import {
  SearchResponse,
  IngestionJobStatus,
  CandidateResult,
  DEIReport,
  AICostReport,
  PassiveCandidate,
  StaleCandidateInfo,
  RequirementItem
} from "./types";

/**
 * Resolves the backend API base URL.
 * Priority:
 * 1. Explicitly configured NEXT_PUBLIC_API_URL environment variable.
 * 2. Client-side browser hostname detection: if running on localhost or 127.0.0.1,
 *    default to local backend (http://localhost:8000/api/v1) to prevent 50s Render cold-start lag.
 * 3. Default production fallback (https://talentai-recruitment.onrender.com/api/v1).
 */
export function getApiBaseUrl(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) {
    const envUrl = process.env.NEXT_PUBLIC_API_URL.trim();
    if (envUrl) {
      return envUrl.replace(/\/+$/, "");
    }
  }

  if (typeof window !== "undefined" && window.location) {
    const hostname = window.location.hostname;
    if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "0.0.0.0") {
      return "http://127.0.0.1:8000/api/v1";
    }
  }

  return "https://talentai-recruitment.onrender.com/api/v1";
}

export const BASE_URL = getApiBaseUrl();

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private isRefreshingToken: boolean = false;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl ? baseUrl.replace(/\/+$/, "") : getApiBaseUrl();
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("talentai_jwt_token");
      // Silently wake up the Render backend in the background so cold start is eliminated
      const healthUrl = this.baseUrl.replace(/\/api\/v1\/?$/, "") + "/health";
      fetch(healthUrl, { method: "GET", mode: "cors" }).catch(() => {});

      // Auto-authenticate immediately if no token
      if (!this.token) {
        this.login("admin@recruit.ai", "admin_password").catch(() => {});
      }
    }
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  setBaseUrl(url: string) {
    this.baseUrl = url.replace(/\/+$/, "");
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== "undefined") {
      if (token) {
        localStorage.setItem("talentai_jwt_token", token);
      } else {
        localStorage.removeItem("talentai_jwt_token");
      }
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== "undefined") {
      this.token = localStorage.getItem("talentai_jwt_token");
    }
    return this.token;
  }

  private async request<T>(path: string, options: RequestInit = {}, retryCount: number = 0): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    // Add API key for protected endpoints
    if (!headers["X-API-Key"]) {
      headers["X-API-Key"] = "dev-secret-api-key";
    }

    const cleanBase = this.baseUrl.replace(/\/+$/, "");
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    const url = `${cleanBase}${cleanPath}`;

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
      });
    } catch (networkErr: any) {
      // Auto-retry up to 2 times with backoff on Render cold start or network hiccups
      if (retryCount < 2) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        return this.request<T>(path, options, retryCount + 1);
      }
      throw new Error(`Network connection error: ${networkErr.message || "Failed to reach server"}.`);
    }

    if (!response.ok) {
      // Automatic silent re-authentication on 401
      if (response.status === 401 && path !== "/auth/token" && !this.isRefreshingToken) {
        this.isRefreshingToken = true;
        this.setToken(null);
        try {
          const authData = await this.login("admin@recruit.ai", "admin_password");
          this.isRefreshingToken = false;
          if (authData?.access_token) {
            headers["Authorization"] = `Bearer ${authData.access_token}`;
            return this.request<T>(path, { ...options, headers }, retryCount + 1);
          }
        } catch (reAuthErr) {
          this.isRefreshingToken = false;
        }
      }

      // Auto-retry on Render 502/503/504 cold-start gateway errors
      if ([502, 503, 504].includes(response.status) && retryCount < 2) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        return this.request<T>(path, options, retryCount + 1);
      }

      let errorMessage = `API Error ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch (_) {}
      throw new Error(errorMessage);
    }

    return response.json();
  }

  // ==================== Authentication ====================

  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const data = await this.request<{ access_token: string; token_type: string }>("/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });

    this.setToken(data.access_token);
    return data;
  }

  async seedAdmin(): Promise<{ message: string; email: string; password: string }> {
    return this.request("/auth/seed-admin", { method: "POST" });
  }

  // ==================== Job Parsing ====================

  async parseJob(
    jobDescription: string,
    jobTitle?: string,
    minExperienceYears?: number
  ): Promise<{ status: string; job_id: string; requirements?: RequirementItem[] }> {
    return this.request("/jobs/parse", {
      method: "POST",
      body: JSON.stringify({
        job_description: jobDescription,
        title: jobTitle,
        min_experience_years: minExperienceYears
      }),
    });
  }

  async getJobStatus(jobId: string): Promise<IngestionJobStatus> {
    return this.request(`/jobs/${jobId}/status`);
  }

  // ==================== Resume Ingestion ====================

  async uploadCV(file: File): Promise<{ status: string; job_id: string; document_id?: number }> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request("/candidates/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getUploadJobStatus(jobId: string): Promise<{
    status: string;
    candidate_id?: number;
    candidate_name?: string;
    error_message?: string;
  }> {
    return this.request(`/candidates/upload/${jobId}/status`);
  }

  async getCandidate(candidateId: number | string): Promise<CandidateResult> {
    return this.request(`/candidates/${candidateId}`);
  }

  async deleteCandidate(candidateId: number): Promise<{ message: string }> {
    return this.request(`/candidates/${candidateId}`, { method: "DELETE" });
  }

  // ==================== Candidate Search & Feedback ====================

  async searchCandidates(
    jobId: string, 
    topK: number = 200, 
    query?: string,
    fastMode?: boolean,
    rerankTopN?: number
  ): Promise<SearchResponse> {
    return this.request("/candidates/search", {
      method: "POST",
      body: JSON.stringify({ 
        job_id: jobId, 
        top_k: topK, 
        query: query || undefined,
        fast_mode: fastMode !== undefined ? fastMode : true,
        rerank_top_n: rerankTopN !== undefined ? rerankTopN : undefined
      }),
    });
  }

  async evaluateCandidate(candidateId: number, jobId: string = "1") {
    return this.request(`/candidates/${candidateId}/evaluate`, {
      method: "POST",
      body: JSON.stringify({ job_id: jobId }),
    });
  }

  async submitFeedback(candidateId: number, jobId: string, feedbackType: string, comments: string) {
    return this.request(`/candidates/${candidateId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, feedback_type: feedbackType, comments }),
    });
  }

  // ==================== Sourcing & Staleness ====================

  async searchGitHubSourcing(
    language: string,
    location?: string,
    minRepos: number = 5,
    maxResults: number = 20
  ): Promise<PassiveCandidate[]> {
    return this.request("/sourcing/github", {
      method: "POST",
      body: JSON.stringify({ language, location, min_repos: minRepos, max_results: maxResults }),
    });
  }

  async searchStackOverflowSourcing(
    tags: string[],
    minReputation: number = 1000,
    maxResults: number = 20
  ): Promise<PassiveCandidate[]> {
    return this.request("/sourcing/stackoverflow", {
      method: "POST",
      body: JSON.stringify({ tags, min_reputation: minReputation, max_results: maxResults }),
    });
  }

  async ingestDiscoveredCandidates(candidates: PassiveCandidate[]): Promise<{ created: number; skipped_duplicates: number }> {
    return this.request("/sourcing/ingest-discovered", {
      method: "POST",
      body: JSON.stringify({ candidates }),
    });
  }

  async getStaleCandidates(thresholdDays: number = 90, limit: number = 50): Promise<StaleCandidateInfo[]> {
    return this.request(`/sourcing/stale-profiles?threshold_days=${thresholdDays}&limit=${limit}`);
  }

  async triggerStalenessRefresh(thresholdDays: number = 90, limit: number = 20): Promise<{ stale_found: number; enqueued: number }> {
    return this.request(`/sourcing/refresh-stale?threshold_days=${thresholdDays}&limit=${limit}`, { method: "POST" });
  }

  // ==================== Analytics & Telemetry ====================

  async getDEIAnalytics(jobId?: string | number, thresholdScore: number = 0.7): Promise<DEIReport> {
    const query = jobId ? `?job_id=${jobId}&threshold_score=${thresholdScore}` : `?threshold_score=${thresholdScore}`;
    return this.request(`/analytics/dei${query}`);
  }

  async getAICostAnalytics(): Promise<AICostReport> {
    return this.request("/analytics/ai-costs");
  }

  async getCandidatesCount(): Promise<{ total_amount: number }> {
    return this.request("/candidates/count");
  }
}

export const api = new ApiClient();

