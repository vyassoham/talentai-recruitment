"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Search,
  Sparkles,
  CheckCircle2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  X,
  SlidersHorizontal,
  Bot,
  AlertCircle,
  Copy,
  Check,
} from "lucide-react";
import { CandidateResult, SearchResponse, JobRequirementData } from "../lib/types";
import { api } from "../lib/api";

interface CandidateSearchResultsProps {
  activeJobId: string | null;
  onSelectCandidate: (candidate: CandidateResult) => void;
  onJobChange?: (jobId: string) => void;
}

const SUGGESTED_QUERIES = [
  "Python developer jisko FastAPI aur PostgreSQL aata ho",
  "Senior ML Engineer with PyTorch & pgvector experience",
  "DevOps Engineer who knows Kubernetes & CI/CD",
  "Frontend React developer with Next.js 14 and Tailwind",
  "Mujhe aisa architect chahiye jisko distributed systems aur Redis aata ho",
];

function getPageNumbers(current: number, total: number): (number | string)[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  if (current <= 4) {
    return [1, 2, 3, 4, 5, "...", total];
  }
  if (current >= total - 3) {
    return [1, "...", total - 4, total - 3, total - 2, total - 1, total];
  }
  return [1, "...", current - 1, current, current + 1, "...", total];
}

export const CandidateSearchResults: React.FC<CandidateSearchResultsProps> = ({
  activeJobId,
  onSelectCandidate,
  onJobChange,
}) => {
  const [jobsList, setJobsList] = useState<JobRequirementData[]>([]);

  useEffect(() => {
    let isMounted = true;
    api.getJobs(20)
      .then((res) => {
        if (isMounted && res && res.jobs) {
          setJobsList(res.jobs);
        }
      })
      .catch(() => {});
    return () => { isMounted = false; };
  }, []);
  const [searchQuery, setSearchQuery] = useState(
    "Senior Python backend developer with FastAPI, pgvector, and distributed systems experience",
  );
  const [topK, setTopK] = useState(200);
  const [fastMode, setFastMode] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(
    null,
  );
  const [expandedCandidate, setExpandedCandidate] = useState<number | null>(1);

  // Pagination & Virtualization State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const resultsTableRef = useRef<HTMLDivElement>(null);

  // Multi-Vector Section Highlighting State
  const [activeSectionTabByCand, setActiveSectionTabByCand] = useState<Record<number, number>>({});
  const [copiedSectionKey, setCopiedSectionKey] = useState<string | null>(null);

  // Post-search Filters
  const [filterExp, setFilterExp] = useState<string>("all");
  const [filterGender, setFilterGender] = useState<string>("all");
  const [filterMinScore, setFilterMinScore] = useState<string>("0");

  // Feedback state
  const [feedbackCandidateId, setFeedbackCandidateId] = useState<number | null>(
    null,
  );
  const [feedbackType, setFeedbackType] = useState("SHORTLIST");
  const [feedbackComments, setFeedbackComments] = useState("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  // Reset to page 1 whenever filters or searchResponse changes
  useEffect(() => {
    setCurrentPage(1);
  }, [filterExp, filterGender, filterMinScore, searchResponse]);

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    if (resultsTableRef.current) {
      resultsTableRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const handleSearch = async (e?: React.FormEvent, overrideQuery?: string, isRetry: boolean = false) => {
    if (e) e.preventDefault();

    const queryToUse =
      overrideQuery !== undefined ? overrideQuery : searchQuery;
    if (!queryToUse.trim()) return;

    setIsSearching(true);
    setSearchError(null);
    try {
      const jobId = activeJobId || "1";
      const res = await api.searchCandidates(jobId, topK, queryToUse, fastMode, fastMode ? 0 : 2);
      setSearchResponse(res);
      setSearchError(null);
      if (res.candidates && res.candidates.length > 0) {
        setExpandedCandidate(res.candidates[0].candidate_id);
      }
    } catch (err: any) {
      if (!isRetry) {
        // Transparent auto-retry after 1.5s in case backend was cold-starting
        await new Promise((r) => setTimeout(r, 1500));
        return handleSearch(undefined, queryToUse, true);
      }
      setSearchError(err?.message || "Cloud search engine is warming up. Please tap Retry.");
    } finally {
      setIsSearching(false);
    }
  };

  // Auto-trigger search when activeJobId changes (e.g. after parsing a JD)
  React.useEffect(() => {
    if (activeJobId && activeJobId !== "1") {
      const autoQuery =
        "Find the best candidates matching this job description strictly.";
      setSearchQuery(autoQuery);
      handleSearch(undefined, autoQuery);
    }
  }, [activeJobId]);

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackCandidateId) return;

    setIsSubmittingFeedback(true);
    try {
      await api.submitFeedback(
        feedbackCandidateId,
        activeJobId || "1",
        feedbackType,
        feedbackComments,
      );
      setFeedbackCandidateId(null);
      setFeedbackComments("");
    } catch (err: any) {
      alert("Failed to submit candidate feedback. Please try again.");
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const rawCandidateList = searchResponse ? searchResponse.candidates : [];

  const candidateList = rawCandidateList.filter((cand) => {
    // Experience Filter
    if (filterExp !== "all") {
      const minExp = parseInt(filterExp, 10);
      if ((cand.total_experience_years || 0) < minExp) return false;
    }
    // Gender Filter
    if (filterGender !== "all") {
      if (
        !cand.gender ||
        cand.gender.toLowerCase() !== filterGender.toLowerCase()
      )
        return false;
    }
    // Min Score Filter
    if (filterMinScore !== "0") {
      const rawScore =
        cand.final_score || cand.composite_score || cand.retrieval_score || 0.5;
      const normalized = Math.pow(rawScore, 0.45);
      const scorePct = Math.min(100, Math.round(normalized * 100));
      if (scorePct < parseInt(filterMinScore, 10)) return false;
    }
    return true;
  });

  const totalCandidates = candidateList.length;
  const totalPages = Math.max(1, Math.ceil(totalCandidates / pageSize));
  const validCurrentPage = Math.min(Math.max(1, currentPage), totalPages);
  const startIndex = (validCurrentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalCandidates);
  const paginatedCandidates = candidateList.slice(startIndex, endIndex);

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
              Type any custom criteria in English, Hinglish, or Hindi — Gemini
              AI will extract semantics and match candidates.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="self-start sm:self-auto text-xs font-medium text-zinc-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-all shadow-sm"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-indigo-400" />
            {showAdvanced ? "Hide Controls" : "Filter Controls"}
          </button>
        </div>

        {/* Free-form Prompt Input Form */}
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="relative flex items-center">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g. Mujhe aisa candidate chahiye jisko Python, FastAPI aur Redis aata ho..."
              className="w-full bg-black/20 border border-white/5 backdrop-blur-sm hover:border-zinc-700 focus:border-indigo-500 rounded-lg py-3 pl-4 pr-[130px] text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none transition"
            />

            <div className="absolute right-2 flex items-center gap-2">
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="p-1 rounded text-zinc-500 hover:text-zinc-300 transition"
                >
                  <X className="w-4 h-4" />
                </button>
              )}

              <button
                type="submit"
                disabled={isSearching}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition cursor-pointer shadow-[0_0_10px_rgba(79,70,229,0.15)]"
              >
                {isSearching ? (
                  <>
                    <Sparkles className="w-3.5 h-3.5 animate-spin" />
                    Searching
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5" />
                    Search
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Clickable Inspiration Chips (Clicking fills the input box) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-500">
              <span>Quick Prompt Examples (Click to use):</span>
            </div>
            <div className="flex flex-wrap items-center gap-2.5">
              {SUGGESTED_QUERIES.map((suggestion, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setSearchQuery(suggestion);
                    handleSearch(undefined, suggestion);
                  }}
                  className={`text-xs px-3.5 py-2 rounded-md transition text-left cursor-pointer ${
                    searchQuery === suggestion
                      ? "bg-indigo-950/60 text-indigo-300 border border-indigo-800/60 shadow"
                      : "bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white border border-white/10 transition-all duration-200"
                  }`}
                >
                  ✨ {suggestion}
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
                <div className="flex flex-col text-left">
                  <span className="font-medium text-zinc-200">Search Speed Mode</span>
                  <span className="text-[10px] text-zinc-400">
                    {fastMode ? "⚡ Sub-second Instant Search" : "✨ Deep Gemini LLM Reranking"}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setFastMode(!fastMode)}
                  className={`px-2.5 py-1 rounded text-[11px] font-semibold transition ${
                    fastMode 
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" 
                      : "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40"
                  }`}
                >
                  {fastMode ? "Fast: ON" : "Deep AI: ON"}
                </button>
              </div>

              <div className="flex items-center justify-between p-2.5 bg-transparent rounded border border-white/10 text-zinc-400 gap-2">
                <span>Active Job Context</span>
                {jobsList.length > 0 && onJobChange ? (
                  <div className="relative">
                    <select
                      value={activeJobId || String(jobsList[0].id)}
                      onChange={(e) => onJobChange(e.target.value)}
                      className="bg-black/80 border border-white/20 text-zinc-200 text-xs rounded px-2.5 py-1 pr-6 appearance-none focus:outline-none focus:border-purple-400 cursor-pointer font-medium"
                    >
                      {jobsList.map((j) => (
                        <option key={j.id} value={j.id} className="bg-[#141418] text-zinc-200">
                          {j.title || `Job #${j.id}`} (#{j.id})
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="w-3 h-3 text-zinc-400 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  </div>
                ) : (
                  <span className="font-mono text-zinc-200 font-medium">
                    {jobsList.find(j => String(j.id) === String(activeJobId))?.title || `Job #${activeJobId || "1"}`}
                  </span>
                )}
              </div>
            </div>
          )}
        </form>

        {searchError && (
          <div className="mt-3 flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-amber-200 text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
              <span>{searchError}</span>
            </div>
            <button
              type="button"
              onClick={() => handleSearch(undefined, undefined, false)}
              className="rounded bg-amber-500/20 px-2.5 py-1 text-xs font-medium text-amber-300 hover:bg-amber-500/30 border border-amber-500/40 transition"
            >
              Retry
            </button>
          </div>
        )}
      </div>

      {/* 2. Telemetry Section (4-Column Minimalist KPI Grid) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg p-4 space-y-1">
          <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">
            Eligibility Pass
          </span>
          <span
            className={`text-2xl font-semibold font-mono block transition-colors ${searchResponse ? "text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]" : "text-zinc-600"}`}
          >
            {searchResponse
              ? `${searchResponse.eligible_count} Candidates`
              : "--"}
          </span>
        </div>

        <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg p-4 space-y-1">
          <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">
            Retrieval Time
          </span>
          <span
            className={`text-2xl font-semibold font-mono block transition-colors ${searchResponse ? "text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]" : "text-zinc-600"}`}
          >
            {searchResponse?.telemetry?.retrieval_ranking_latency_sec
              ? `${searchResponse.telemetry.retrieval_ranking_latency_sec}s`
              : "--"}
          </span>
        </div>

        <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg p-4 space-y-1">
          <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">
            AI Rerank Latency
          </span>
          <span
            className={`text-2xl font-semibold font-mono block transition-colors ${searchResponse ? "text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]" : "text-zinc-600"}`}
          >
            {searchResponse?.telemetry?.rerank_latency_sec
              ? `${searchResponse.telemetry.rerank_latency_sec}s`
              : "--"}
          </span>
        </div>

        <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg p-4 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">
              Total Pipeline Time
            </span>
            {searchResponse?.telemetry?.cache_hit && (
              <span className="text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 shadow-[0_0_8px_rgba(16,185,129,0.3)]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                ⚡ {searchResponse.telemetry.cache_tier || "Redis"} Cache Hit
              </span>
            )}
          </div>
          <span
            className={`text-2xl font-semibold font-mono block transition-colors ${searchResponse ? (searchResponse.telemetry.cache_hit ? "text-emerald-300 drop-shadow-[0_0_10px_rgba(16,185,129,0.6)]" : "text-indigo-300 drop-shadow-[0_0_10px_rgba(99,102,241,0.6)]") : "text-zinc-600"}`}
          >
            {searchResponse?.telemetry?.total_search_latency_sec !== undefined
              ? `${searchResponse.telemetry.total_search_latency_sec}s`
              : "--"}
          </span>
        </div>
      </div>

      {/* 3. Candidate List (Clean Table / Rows with Subtle Dividers) */}
      <div
        ref={resultsTableRef}
        className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg overflow-hidden"
      >
        <div className="p-4 sm:p-5 border-b border-white/10 flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white/[0.02]">
          <div>
            <div className="flex items-baseline gap-2">
              <h3 className="text-lg font-bold bg-gradient-to-r from-white via-zinc-200 to-zinc-500 bg-clip-text text-transparent drop-shadow-sm">
                Ranked Candidate Matches ({candidateList.length})
              </h3>
              {candidateList.length > 0 && (
                <span className="text-xs text-zinc-500 font-mono">
                  (Showing {startIndex + 1}–{endIndex})
                </span>
              )}
            </div>
            {searchQuery && (
              <p className="text-[11px] text-zinc-400 mt-0.5 line-clamp-1">
                Matched against:{" "}
                <span className="text-zinc-300 font-mono italic">
                  "{searchQuery}"
                </span>
              </p>
            )}
          </div>

          {/* Quick Filters Toolbar */}
          {rawCandidateList.length > 0 && (
            <div className="flex flex-wrap items-center gap-3 text-xs bg-zinc-900/50 p-2 rounded-md border border-zinc-800">
              <span className="text-zinc-500 font-medium hidden sm:inline-block pl-1">
                Filters:
              </span>

              <select
                value={filterExp}
                onChange={(e) => setFilterExp(e.target.value)}
                className="bg-zinc-950 border border-zinc-700 text-zinc-300 rounded px-2.5 py-1.5 outline-none focus:border-indigo-500 transition-colors cursor-pointer"
              >
                <option value="all">Any Experience</option>
                <option value="3">3+ Years Exp</option>
                <option value="5">5+ Years Exp</option>
                <option value="8">8+ Years Exp</option>
                <option value="12">12+ Years Exp</option>
              </select>

              <select
                value={filterGender}
                onChange={(e) => setFilterGender(e.target.value)}
                className="bg-zinc-950 border border-zinc-700 text-zinc-300 rounded px-2.5 py-1.5 outline-none focus:border-indigo-500 transition-colors cursor-pointer"
              >
                <option value="all">Any Gender</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>

              <select
                value={filterMinScore}
                onChange={(e) => setFilterMinScore(e.target.value)}
                className="bg-zinc-950 border border-zinc-700 text-zinc-300 rounded px-2.5 py-1.5 outline-none focus:border-indigo-500 transition-colors cursor-pointer"
              >
                <option value="0">Any Score</option>
                <option value="60">60%+ Match</option>
                <option value="80">80%+ Match</option>
                <option value="90">90%+ Match</option>
              </select>
            </div>
          )}
        </div>

        <div className="divide-y divide-zinc-800 min-h-[200px]">
          {candidateList.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
              <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-4 text-zinc-500 shadow-inner">
                <Search className="w-7 h-7 opacity-60" />
              </div>
              <h4 className="text-zinc-300 font-medium text-sm mb-1.5">
                No candidates found
              </h4>
              <p className="text-zinc-500 text-xs max-w-sm leading-relaxed">
                {searchResponse
                  ? "Try adjusting your filters or making your prompt less restrictive to find more matches."
                  : "Enter a search prompt or click one of the quick examples above to start discovering talent."}
              </p>
            </div>
          ) : (
            paginatedCandidates.map((cand, index) => {
              const isExpanded = expandedCandidate === cand.candidate_id;

              // Apply a square-root curve to normalize strict mathematical scores to human-expected percentage scales
              const rawScore =
                cand.final_score ||
                cand.composite_score ||
                cand.retrieval_score ||
                0.5;
              const normalized = Math.pow(rawScore, 0.45); // e.g. 0.60 -> ~0.79 (79%)
              const scorePct = Math.min(100, Math.round(normalized * 100));

              return (
                <div
                  key={cand.candidate_id}
                  className="transition-colors hover:bg-white/5 backdrop-blur-md/60"
                  style={{
                    contentVisibility: index >= 3 ? "auto" : "visible",
                    containIntrinsicSize: "auto none auto 140px",
                  }}
                >
                  {/* Main Row */}
                  <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                      {/* Minimalist Rank & Score Badge */}
                      <div className="flex items-center gap-2.5 shrink-0">
                        <span className="w-6 text-center text-xs font-mono font-medium text-zinc-500">
                          #{startIndex + index + 1}
                        </span>
                        <div className="px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-center font-mono shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                          <span className="text-xs font-bold text-emerald-300 drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]">
                            {scorePct}%
                          </span>
                        </div>
                      </div>

                      {/* Profile Summary with AI Copilot Insights */}
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="font-semibold text-sm text-zinc-100">
                            {cand.name}
                          </h4>
                          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                            Eligible
                          </span>
                          {cand.ai_evaluation?.hiring_verdict && (
                            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 flex items-center gap-1 shadow-[0_0_10px_rgba(99,102,241,0.2)]">
                              ✨ {cand.ai_evaluation.hiring_verdict}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-zinc-400">
                          {cand.current_title} • {cand.total_experience_years || 0} Years Exp
                          {cand.location && ` • ${cand.location}`}
                        </p>
                        {cand.ai_evaluation?.reasoning_summary && (
                          <p className="text-xs text-zinc-300/90 italic line-clamp-1 max-w-xl">
                            "{cand.ai_evaluation.reasoning_summary}"
                          </p>
                        )}
                        {(cand.ai_evaluation?.key_strengths || cand.match_reasons || []).length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-0.5">
                            {(cand.ai_evaluation?.key_strengths || cand.match_reasons || []).slice(0, 3).map((st: string, sIdx: number) => (
                              <span key={sIdx} className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-zinc-300 border border-white/10 flex items-center gap-1">
                                <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                                {st}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Multi-Vector Highlight Preview */}
                        {cand.highlighted_section && cand.highlighted_section.content_chunk && (
                          <div className="mt-2.5 p-2 rounded-lg bg-purple-950/20 border border-purple-500/20 flex items-start gap-2 max-w-2xl">
                            <div className="p-1 rounded bg-purple-500/20 text-purple-300 shrink-0 mt-0.5">
                              <Sparkles className="w-3 h-3" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2 mb-0.5">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-300">
                                  Vector Match: {cand.highlighted_section.section_title}
                                </span>
                                {cand.highlighted_section.similarity_score !== undefined && (
                                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-200 border border-purple-500/30">
                                    {Math.round(cand.highlighted_section.similarity_score * 100)}% Match
                                  </span>
                                )}
                              </div>
                              <p className="text-zinc-300 text-[11px] leading-relaxed line-clamp-2 italic font-mono bg-black/25 px-2 py-1 rounded border border-white/5">
                                "{cand.highlighted_section.content_chunk}"
                              </p>
                            </div>
                          </div>
                        )}
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
                        onClick={() =>
                          setFeedbackCandidateId(cand.candidate_id)
                        }
                        className="px-2.5 py-1.5 rounded-md text-xs font-medium text-zinc-300 bg-white/10 hover:bg-white/20 hover:scale-[1.02] transition flex items-center gap-1.5"
                      >
                        <MessageSquare className="w-3 h-3 text-zinc-400" />
                        Decision
                      </button>

                      <button
                        onClick={() =>
                          setExpandedCandidate(
                            isExpanded ? null : cand.candidate_id,
                          )
                        }
                        className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition"
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Details Panel */}
                  {isExpanded && (
                    <div className="px-5 pb-5 pt-1 bg-transparent/50 border-t border-white/10/60 space-y-4 text-xs">
                      {/* Multi-Vector Section Highlighting & Evidence */}
                      {(() => {
                        const sections = (cand.matched_sections && cand.matched_sections.length > 0)
                          ? cand.matched_sections
                          : (cand.highlighted_section ? [cand.highlighted_section] : []);
                        
                        if (sections.length === 0 || !sections[0].content_chunk) return null;

                        const activeTabIdx = activeSectionTabByCand[cand.candidate_id] || 0;
                        const currentSection = sections[Math.min(activeTabIdx, sections.length - 1)];

                        return (
                          <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/30 via-indigo-950/25 to-black/40 border border-purple-500/30 space-y-3 shadow-lg shadow-purple-950/20">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <div className="p-1.5 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                  <Sparkles className="w-4 h-4 text-purple-300" />
                                </div>
                                <div>
                                  <h5 className="text-xs font-bold uppercase tracking-wider text-purple-200 flex items-center gap-1.5">
                                    Multi-Vector Match: Verbatim CV Section Evidence
                                  </h5>
                                  <p className="text-[11px] text-zinc-400">
                                    ColBERT-style chunking identified this exact paragraph as the strongest semantic match for your query.
                                  </p>
                                </div>
                              </div>

                              {currentSection.similarity_score !== undefined && (
                                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/20 border border-purple-500/40 text-purple-200 font-mono text-xs font-bold">
                                  <span>{Math.round(currentSection.similarity_score * 100)}%</span>
                                  <span className="text-[10px] text-purple-300 font-normal">Vector Cosine Match</span>
                                </div>
                              )}
                            </div>

                            {/* Section Selector Tabs if more than 1 section */}
                            {sections.length > 1 && (
                              <div className="flex flex-wrap gap-1.5 pt-1">
                                {sections.map((sec, sIdx) => {
                                  const isActive = sIdx === (activeSectionTabByCand[cand.candidate_id] || 0);
                                  const typeLabel = sec.section_type || "SECTION";
                                  return (
                                    <button
                                      key={sIdx}
                                      onClick={() => setActiveSectionTabByCand(prev => ({ ...prev, [cand.candidate_id]: sIdx }))}
                                      className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition flex items-center gap-1.5 border ${
                                        isActive
                                          ? "bg-purple-600 text-white border-purple-400 shadow-sm shadow-purple-500/30 font-semibold"
                                          : "bg-white/5 text-zinc-300 border-white/10 hover:bg-white/10 hover:text-white"
                                      }`}
                                    >
                                      <span className="uppercase text-[9px] tracking-wide opacity-80">{typeLabel}:</span>
                                      <span className="truncate max-w-[140px]">{sec.section_title}</span>
                                      {sec.similarity_score !== undefined && (
                                        <span className="font-mono text-[10px] opacity-90 font-bold">
                                          {Math.round(sec.similarity_score * 100)}%
                                        </span>
                                      )}
                                    </button>
                                  );
                                })}
                              </div>
                            )}

                            {/* Verbatim Highlighted Section Box */}
                            <div className="p-3.5 rounded-lg bg-black/50 border border-purple-500/30 space-y-2 relative group">
                              <div className="flex items-center justify-between text-[11px] text-zinc-400">
                                <span className="font-semibold text-purple-300 flex items-center gap-1.5">
                                  <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                                  {currentSection.section_title}
                                </span>
                                <button
                                  onClick={() => {
                                    navigator.clipboard.writeText(currentSection.content_chunk);
                                    setCopiedSectionKey(`${cand.candidate_id}-${activeTabIdx}`);
                                    setTimeout(() => setCopiedSectionKey(null), 2000);
                                  }}
                                  className="px-2 py-0.5 rounded bg-white/5 hover:bg-white/15 text-zinc-300 hover:text-white text-[10px] font-medium transition flex items-center gap-1"
                                  title="Copy verbatim section snippet"
                                >
                                  {copiedSectionKey === `${cand.candidate_id}-${activeTabIdx}` ? (
                                    <>
                                      <Check className="w-3 h-3 text-emerald-400" />
                                      <span className="text-emerald-400">Copied!</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="w-3 h-3 text-zinc-400" />
                                      <span>Copy Snippet</span>
                                    </>
                                  )}
                                </button>
                              </div>

                              <blockquote className="border-l-2 border-purple-500 pl-3 py-1 font-mono text-[11.5px] leading-relaxed text-zinc-200 select-all whitespace-pre-wrap">
                                "{currentSection.content_chunk}"
                              </blockquote>
                            </div>
                          </div>
                        );
                      })()}

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
                                  <span className="font-medium text-zinc-200">
                                    {ev.requirement}
                                  </span>
                                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                                    {ev.assessment} (
                                    {Math.round(ev.confidence * 100)}%)
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
            })
          )}
        </div>

        {/* 4. Pagination & DOM Virtualization Footer Bar */}
        {totalCandidates > 0 && (
          <div className="p-4 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4 bg-white/[0.02] text-xs text-zinc-400">
            <div className="flex flex-wrap items-center gap-3">
              <span>
                Showing <span className="text-zinc-200 font-medium font-mono">{startIndex + 1}</span> to{" "}
                <span className="text-zinc-200 font-medium font-mono">{endIndex}</span> of{" "}
                <span className="text-zinc-200 font-medium font-mono">{totalCandidates}</span> candidates
              </span>

              <div className="flex items-center gap-1.5 ml-2">
                <span className="text-zinc-500">Per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-zinc-950 border border-zinc-700 text-zinc-300 rounded px-2 py-1 outline-none focus:border-indigo-500 transition-colors cursor-pointer"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => handlePageChange(Math.max(1, validCurrentPage - 1))}
                  disabled={validCurrentPage === 1}
                  className="p-1.5 rounded-md border border-white/10 bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed text-zinc-300 transition flex items-center gap-1"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                  <span className="hidden sm:inline text-xs">Prev</span>
                </button>

                {getPageNumbers(validCurrentPage, totalPages).map((p, idx) =>
                  typeof p === "number" ? (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handlePageChange(p)}
                      className={`min-w-[28px] h-7 px-2 rounded-md font-medium text-xs transition ${
                        validCurrentPage === p
                          ? "bg-indigo-600 text-white shadow-[0_0_10px_rgba(79,70,229,0.3)]"
                          : "border border-white/10 bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      {p}
                    </button>
                  ) : (
                    <span key={idx} className="px-1 text-zinc-600 select-none font-mono">
                      ...
                    </span>
                  )
                )}

                <button
                  type="button"
                  onClick={() => handlePageChange(Math.min(totalPages, validCurrentPage + 1))}
                  disabled={validCurrentPage === totalPages}
                  className="p-1.5 rounded-md border border-white/10 bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed text-zinc-300 transition flex items-center gap-1"
                  aria-label="Next page"
                >
                  <span className="hidden sm:inline text-xs">Next</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Minimal Feedback Modal */}
      {feedbackCandidateId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-white/5 border border-white/10 backdrop-blur-md rounded-lg w-full max-w-sm p-5 space-y-3 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
              <h3 className="text-lg font-bold bg-gradient-to-r from-white via-zinc-200 to-zinc-500 bg-clip-text text-transparent drop-shadow-sm">
                Recruiter Decision
              </h3>
              <button
                onClick={() => setFeedbackCandidateId(null)}
                className="text-zinc-500 hover:text-zinc-300 text-lg leading-none"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleFeedbackSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Action
                </label>
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
                <label className="block text-xs font-medium text-zinc-400 mb-1">
                  Notes
                </label>
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
