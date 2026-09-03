export interface User {
  id: number;
  email: string;
  role: "RECRUITER" | "ADMIN" | "INTERVIEWER" | "CANDIDATE";
  isActive: boolean;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
}

export interface RequirementItem {
  name: string;
  type: "MANDATORY" | "PREFERRED" | "EXPERIENCE" | "EDUCATION" | "CONTEXTUAL";
  weight?: number;
}

export interface JobRequirementData {
  id: string;
  title: string;
  raw_description: string;
  min_experience_years?: number;
  requirements: RequirementItem[];
}

export interface IngestionJobStatus {
  id: string;
  job_type: string;
  status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";
  payload?: any;
  result?: any;
  error?: string;
  created_at?: string;
  updated_at?: string;
}

export interface EvaluationEvidenceItem {
  requirement: string;
  assessment: "Meets" | "Partially Meets" | "Does Not Meet";
  confidence: number;
  evidence_quote?: string;
  reasoning?: string;
  validation_status?: "VERIFIED" | "SUSPECTED_HALLUCINATION" | "UNVERIFIED";
}

export interface CandidateResult {
  candidate_id: number;
  name?: string;
  email?: string;
  phone?: string;
  location?: string;
  gender?: string;
  current_company?: string;
  resume_url?: string;
  current_title?: string;
  total_experience_years?: number;
  final_score: number;
  composite_score?: number;
  retrieval_score?: number;
  match_reasons?: string[];
  eligibility_status: "ELIGIBLE" | "INELIGIBLE";
  retrieval_rank?: number;
  rerank_score?: number;
  evaluations: EvaluationEvidenceItem[];
  social_links?: Record<string, string>;
  engineering_quality_score?: number;
  external_evidence?: string;
  best_matching_section?: string;
}

export interface SearchTelemetry {
  eligibility_latency_sec: number;
  retrieval_ranking_latency_sec: number;
  rerank_latency_sec: number;
  total_search_latency_sec: number;
}

export interface SearchResponse {
  job_id: string;
  eligible_count: number;
  retrieved_count: number;
  telemetry: SearchTelemetry;
  candidates: CandidateResult[];
}

export interface PassiveCandidate {
  name: string;
  email?: string;
  location?: string;
  bio?: string;
  github_url?: string;
  stackoverflow_url?: string;
  reputation?: number;
  public_repos?: number;
  followers?: number;
  primary_language?: string;
  primary_tag?: string;
  source: string;
}

export interface StaleCandidateInfo {
  candidate_id: number;
  name: string;
  last_enriched_at?: string;
  updated_at?: string;
  staleness_score: number;
  has_social_links: boolean;
}

export interface DEIReport {
  job_id: number;
  threshold_score: number;
  total_evaluations: number;
  adverse_impact_detected: boolean;
  adverse_impact_ratio: number;
  disparity_details: {
    gender?: Record<string, { total: number; passed: number; pass_rate: number }>;
    race_ethnicity?: Record<string, { total: number; passed: number; pass_rate: number }>;
  };
}

export interface AIOperationTelemetry {
  operation: string;
  transaction_count: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost_usd: number;
  avg_latency_sec: number;
}

export interface AICostReport {
  total_ai_transactions: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens_consumed: number;
  total_estimated_cost_usd: number;
  operations: AIOperationTelemetry[];
}
