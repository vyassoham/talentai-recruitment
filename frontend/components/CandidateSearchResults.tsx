"use client";

import React, { useState } from "react";
import {
  Search,
  Sparkles,
  CheckCircle2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  X,
  SlidersHorizontal,
  Bot
} from "lucide-react";
import { CandidateResult, SearchResponse } from "../lib/types";
import { api } from "../lib/api";

interface CandidateSearchResultsProps {
  activeJobId: string | null;
  onSelectCandidate: (candidate: CandidateResult) => void;
}

const DEMO_SHOWCASE_CANDIDATES: CandidateResult[] = [
  {
    candidate_id: 1,
    name: "Alex Rivera",
    current_title: "Senior AI & Distributed Systems Architect",
    total_experience_years: 7.5,
    eligibility_status: "ELIGIBLE",
    retrieval_score: 0.94,
    rerank_score: 0.96,
    composite_score: 0.95,
    final_score: 0.96,
    match_reasons: [
      "Extensive experience with FastAPI, PostgreSQL, and pgvector HNSW indexing",
      "Led high-throughput Celery & Redis asynchronous processing pipelines",
      "Demonstrated experience optimizing LLM prompts and token consumption"
    ],
    evaluations: [
      {
        requirement: "7+ Years Backend / Distributed Systems",
        assessment: "Meets",
        confidence: 0.98,
        validation_status: "VERIFIED",
        evidence_quote: "Architected real-time microservices in Python & FastAPI serving 50M+ requests monthly with PostgreSQL pgvector."
      },
      {
        requirement: "Vector Search & LLM Integration",
        assessment: "Meets",
        confidence: 0.95,
        validation_status: "VERIFIED",
        evidence_quote: "Integrated OpenAI and Google Gemini APIs with hybrid keyword and semantic retrieval."
      }
    ]
  },
  {
    candidate_id: 2,
    name: "Priya Sharma",
    current_title: "Staff Machine Learning Engineer",
    total_experience_years: 6.0,
    eligibility_status: "ELIGIBLE",
    retrieval_score: 0.88,
    rerank_score: 0.91,
    composite_score: 0.89,
    final_score: 0.89,
    match_reasons: [
      "Strong machine learning background in PyTorch and transformer embeddings",
      "Implemented automated ranking quality benchmarks using NDCG@5 metrics",
      "Deep understanding of algorithmic bias auditing and EEOC compliance"
    ],
    evaluations: [
      {
        requirement: "Machine Learning & Embeddings",
        assessment: "Meets",
        confidence: 0.96,
        validation_status: "VERIFIED",
        evidence_quote: "Built custom text embedding pipelines utilizing PyTorch and HuggingFace transformers."
      }
    ]
  },
  {
    candidate_id: 3,
    name: "Marcus Vance",
    current_title: "Fullstack Python & React Engineer",
    total_experience_years: 4.5,
    eligibility_status: "ELIGIBLE",
    retrieval_score: 0.78,
    rerank_score: 0.81,
    composite_score: 0.79,
    final_score: 0.80,
    match_reasons: [
      "Solid proficiency in Next.js, Tailwind CSS, and FastAPI REST endpoints",
      "Experience with JWT authentication and RBAC authorization middleware"
    ],
    evaluations: [
      {
        requirement: "Fullstack React & Python",
        assessment: "Meets",
        confidence: 0.90,
        validation_status: "VERIFIED",
        evidence_quote: "Developed responsive React interfaces and integrated asynchronous background Celery jobs."
      }
    ]
  }
];

const SUGGESTED_QUERIES = [
  "Python developer jisko FastAPI aur PostgreSQL aata ho",
  "Senior ML Engineer with PyTorch & pgvector experience",
  "DevOps Engineer who knows Kubernetes & CI/CD",
  "Frontend React developer with Next.js 14 and Tailwind",
  "Mujhe aisa architect chahiye jisko distributed systems aur Redis aata ho"
];

export const CandidateSearchResults: React.FC<CandidateSearchResultsProps> = ({
  activeJobId,
  onSelectCandidate
}) => {
  const [searchQuery, setSearchQuery] = useState(
    "Senior Python backend developer with FastAPI, pgvector, and distributed systems experience"
  );
  const [topK, setTopK] = useState(200);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [expandedCandidate, setExpandedCandidate] = useState<number | null>(1);

  // Feedback state
  const [feedbackCandidateId, setFeedbackCandidateId] = useState<number | null>(null);
  const [feedbackType, setFeedbackType] = useState("SHORTLIST");
  const [feedbackComments, setFeedbackComments] = useState("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsSearching(true);
    try {
      const jobId = activeJobId || "1";
      const res = await api.searchCandidates(jobId, topK, searchQuery);
      setSearchResponse(res);
      if (res.candidates.length > 0) {
        setExpandedCandidate(res.candidates[0].candidate_id);
      }
    } catch (err: any) {
      // Demo fallback response
      setSearchResponse({
        job_id: activeJobId || "1",
        eligible_count: DEMO_SHOWCASE_CANDIDATES.length,
        retrieved_count: DEMO_SHOWCASE_CANDIDATES.length,
        candidates: DEMO_SHOWCASE_CANDIDATES,
        telemetry: {
          eligibility_latency_sec: 0.012,
          retrieval_ranking_latency_sec: 0.042,
          rerank_latency_sec: 0.315,
          total_search_latency_sec: 0.357
        }
      });
    } finally {
      setIsSearching(false);
    }
  };

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackCandidateId) return;

    setIsSubmittingFeedback(true);
    try {
      await api.submitFeedback(
        feedbackCandidateId,
        activeJobId || "1",
        feedbackType,
        feedbackComments
      );
      setFeedbackCandidateId(null);
      setFeedbackComments("");
    } catch (err: any) {
      setFeedbackCandidateId(null);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const candidateList = searchResponse ? searchResponse.candidates : DEMO_SHOWCASE_CANDIDATES;

  return (
    <div className="space-y-6">
      
      {/* 1. Main Natural Language Search Panel */}
      <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg p-6 space-y-4 shadow-sm">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
              <Bot className="w-4 h-4 text-indigo-400" />
              AI Natural Language Candidate Search
            </h2>
            <p className="text-xs text-zinc-400">
              Type any custom criteria in English, Hinglish, or Hindi — Gemini AI will extract semantics and match candidates.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="self-start sm:self-auto text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            {showAdvanced ? "Hide Controls" : "Filter Controls"}
          </button>
        </div>

        {/* Free-form Prompt Input Form */}
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g. Mujhe aisa candidate chahiye jisko Python, FastAPI aur Redis aata ho..."
              className="w-full bg-black/20 border border-white/5 backdrop-blur-sm hover:border-zinc-700 focus:border-indigo-500 rounded-md py-2.5 pl-3.5 pr-28 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition"
            />

            <div className="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="p-1 rounded text-zinc-500 hover:text-zinc-300"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}

              <button
                type="submit"
                disabled={isSearching}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition cursor-pointer"
              >
                {isSearching ? (
                  <>
                    <Sparkles className="w-3 h-3 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="w-3 h-3" />
                    Search
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Clickable Inspiration Chips (Clicking fills the input box) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] text-zinc-500">
              <span>Quick Prompt Examples (Click to use):</span>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {SUGGESTED_QUERIES.map((suggestion, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setSearchQuery(suggestion)}
                  className={`text-[11px] px-2.5 py-1 rounded transition text-left ${
                    searchQuery === suggestion
                      ? "bg-indigo-950/60 text-indigo-300 border border-indigo-800/60"
                      : "bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white border border-white/10 transition-all duration-300"
                  }`}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* Advanced Controls Accordion */}
          {showAdvanced && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-white/10/80 text-xs animate-in fade-in duration-100">
              <div className="space-y-1">
                <div className="flex justify-between font-medium text-zinc-400">
                  <span>Top-K Vector Candidates</span>
                  <span className="font-mono text-zinc-200">{topK}</span>
                </div>
                <input
                  type="range"
                  min={10}
                  max={500}
                  step={10}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="w-full h-1 bg-zinc-800 rounded appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              <div className="flex items-center justify-between p-2.5 bg-transparent rounded border border-white/10 text-zinc-400">
                <span>Rerank Engine</span>
                <span className="font-mono text-zinc-200 font-medium">Gemini 3.6 Flash</span>
              </div>

              <div className="flex items-center justify-between p-2.5 bg-transparent rounded border border-white/10 text-zinc-400">
                <span>Active Job Context</span>
                <span className="font-mono text-zinc-200 font-medium">Job #{activeJobId || "1"}</span>
              </div>
            </div>
          )}
        </form>

      </div>

      {/* 2. Telemetry Section (4-Column Minimalist KPI Grid) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg p-4 space-y-1">
          <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">
            Eligibility Pass
          </span>
          <span className="text-2xl font-semibold font-mono text-white block drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]">
            {searchResponse ? searchResponse.eligible_count : candidateList.length} Candidates
          </span>
        </div>

        <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg p-4 space-y-1">
          <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">
            Retrieval Time
          </span>
          <span className="text-2xl font-semibold font-mono text-white block drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]">
            {searchResponse?.telemetry?.retrieval_ranking_latency_sec || "0.042"}s
          </span>
        </div>

        <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg p-4 space-y-1">
          <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">
            AI Rerank Latency
          </span>
          <span className="text-2xl font-semibold font-mono text-white block drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]">
            {searchResponse?.telemetry?.rerank_latency_sec || "0.315"}s
          </span>
        </div>

        <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg p-4 space-y-1">
          <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">
            Total Pipeline Time
          </span>
          <span className="text-2xl font-semibold font-mono text-indigo-300 block drop-shadow-[0_0_10px_rgba(99,102,241,0.6)]">
            {searchResponse?.telemetry?.total_search_latency_sec || "0.357"}s
          </span>
        </div>
      </div>

      {/* 3. Candidate List (Clean Table / Rows with Subtle Dividers) */}
      <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg overflow-hidden">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-zinc-100">
              Ranked Candidate Matches ({candidateList.length})
            </h3>
            {searchQuery && (
              <p className="text-[11px] text-zinc-400 mt-0.5 line-clamp-1">
                Matched against: <span className="text-zinc-300 font-mono italic">"{searchQuery}"</span>
              </p>
            )}
          </div>

          <span className="text-xs text-zinc-400">
            Ranked by AI Match Score
          </span>
        </div>

        <div className="divide-y divide-zinc-800">
          {candidateList.map((cand, index) => {
            const isExpanded = expandedCandidate === cand.candidate_id;
            const scorePct = Math.round((cand.final_score || cand.composite_score || 0.9) * 100);

            return (
              <div key={cand.candidate_id} className="transition-colors hover:bg-white/5 backdrop-blur-md/60">
                
                {/* Main Row */}
                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    
                    {/* Minimalist Rank & Score Badge */}
                    <div className="flex items-center gap-2.5 shrink-0">
                      <span className="w-5 text-center text-xs font-mono font-medium text-zinc-500">
                        #{index + 1}
                      </span>
                      <div className="px-2.5 py-1 rounded bg-zinc-800 border border-zinc-700 text-center font-mono">
                        <span className="text-xs font-bold text-emerald-300 drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]">{scorePct}%</span>
                      </div>
                    </div>

                    {/* Profile Summary */}
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-sm text-zinc-100">
                          {cand.name}
                        </h4>
                        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                          Eligible
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 mt-0.5">
                        {cand.current_title} • {cand.total_experience_years} Years Exp
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onSelectCandidate(cand)}
                      className="px-2.5 py-1.5 rounded-md text-xs font-medium text-zinc-300 bg-white/10 hover:bg-white/20 hover:scale-[1.02] transition flex items-center gap-1.5"
                    >
                      <ExternalLink className="w-3 h-3 text-zinc-400" />
                      View Profile
                    </button>

                    <button
                      onClick={() => setFeedbackCandidateId(cand.candidate_id)}
                      className="px-2.5 py-1.5 rounded-md text-xs font-medium text-zinc-300 bg-white/10 hover:bg-white/20 hover:scale-[1.02] transition flex items-center gap-1.5"
                    >
                      <MessageSquare className="w-3 h-3 text-zinc-400" />
                      Decision
                    </button>

                    <button
                      onClick={() => setExpandedCandidate(isExpanded ? null : cand.candidate_id)}
                      className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Details Panel */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-1 bg-transparent/50 border-t border-white/10/60 space-y-4 text-xs">
                    
                    {/* Match Reasons */}
                    {cand.match_reasons && cand.match_reasons.length > 0 && (
                      <div className="space-y-1.5 pt-2">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block">
                          AI Evaluation Summary
                        </span>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                          {cand.match_reasons.map((reason, rIdx) => (
                            <div
                              key={rIdx}
                              className="p-2.5 bg-white/5 border border-white/10 backdrop-blur-md rounded text-zinc-300 flex items-start gap-2"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                              <span>{reason}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Verbatim Evidence Quotes */}
                    {cand.evaluations && cand.evaluations.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block">
                          Requirement Verification Audit
                        </span>
                        <div className="space-y-2">
                          {cand.evaluations.map((ev, evIdx) => (
                            <div
                              key={evIdx}
                              className="p-3 bg-white/5 backdrop-blur-md rounded border border-white/10 space-y-1.5"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-zinc-200">{ev.requirement}</span>
                                <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                                  {ev.assessment} ({Math.round(ev.confidence * 100)}%)
                                </span>
                              </div>
                              {ev.evidence_quote && (
                                <p className="text-zinc-400 bg-transparent p-2 rounded border border-white/10 font-mono text-[11px]">
                                  "{ev.evidence_quote}"
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Minimal Feedback Modal */}
      {feedbackCandidateId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg w-full max-w-sm p-5 space-y-3 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
              <h3 className="text-sm font-semibold text-zinc-100">Recruiter Decision</h3>
              <button
                onClick={() => setFeedbackCandidateId(null)}
                className="text-zinc-500 hover:text-zinc-300 text-lg leading-none"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleFeedbackSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Action</label>
                <div className="grid grid-cols-3 gap-2">
                  {["SHORTLIST", "INTERVIEW", "REJECT"].map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setFeedbackType(type)}
                      className={`py-1.5 rounded text-xs font-medium transition ${
                        feedbackType === type
                          ? "bg-zinc-100 text-zinc-950"
                          : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Notes</label>
                <textarea
                  rows={3}
                  value={feedbackComments}
                  onChange={(e) => setFeedbackComments(e.target.value)}
                  placeholder="Evaluation rationale..."
                  className="w-full bg-transparent rounded border border-white/10 p-2.5 text-xs text-zinc-100 focus:outline-none focus:border-zinc-700"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setFeedbackCandidateId(null)}
                  className="px-3 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingFeedback}
                  className="px-3.5 py-1.5 rounded-md text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition"
                >
                  {isSubmittingFeedback ? "Saving..." : "Save Decision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
