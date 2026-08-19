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

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("talentai_jwt_token");
    }
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

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
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

  async deleteCandidate(candidateId: number): Promise<{ message: string }> {
    return this.request(`/candidates/${candidateId}`, { method: "DELETE" });
  }

  // ==================== Candidate Search & Feedback ====================

  async searchCandidates(jobId: string, topK: number = 200, query?: string): Promise<SearchResponse> {
    return this.request("/candidates/search", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, top_k: topK, query: query || undefined }),
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
}

export const api = new ApiClient();
