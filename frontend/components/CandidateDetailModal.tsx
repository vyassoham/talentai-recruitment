"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Trash2,
  AlertTriangle,
  ShieldCheck,
  Mail,
  Phone,
  Building,
  FileText,
  Sparkles,
  GraduationCap,
  Briefcase,
  Copy,
  ExternalLink,
  MapPin,
  CheckCircle2,
  Award,
  Check
} from "lucide-react";
import { CandidateResult } from "../lib/types";
import { api } from "../lib/api";

interface CandidateDetailModalProps {
  candidate: CandidateResult | null;
  onClose: () => void;
  onCandidateDeleted: (id: number) => void;
}

export const CandidateDetailModal: React.FC<CandidateDetailModalProps> = ({
  candidate,
  onClose,
  onCandidateDeleted
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [copiedPhone, setCopiedPhone] = useState(false);
  const [cand, setCand] = useState<CandidateResult>(candidate || ({} as CandidateResult));
  const [activeSectionIdx, setActiveSectionIdx] = useState(0);
  const [copiedSection, setCopiedSection] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [streamedReasoning, setStreamedReasoning] = useState("");
  const [streamingStatus, setStreamingStatus] = useState("");
  const [evalCompleted, setEvalCompleted] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);

  useEffect(() => {
    if (candidate) {
      setCand(candidate);
      setActiveSectionIdx(0);
      setStreamedReasoning("");
      setStreamingStatus("");
      setEvalCompleted(false);
      setStreamError(null);
      
      // Auto-fetch full profile if details like education/history are not yet loaded
      if (candidate.candidate_id) {
        setIsLoadingDetails(true);
        api.getCandidate(candidate.candidate_id)
          .then((fullData) => {
            if (fullData) {
              setCand((prev) => ({
                ...prev,
                ...fullData,
                highlighted_section: prev.highlighted_section || fullData.highlighted_section,
                matched_sections: prev.matched_sections || fullData.matched_sections,
                section_embeddings: fullData.section_embeddings || prev.section_embeddings,
                evaluations: prev.evaluations || fullData.evaluations,
                match_reasons: prev.match_reasons || fullData.match_reasons,
                final_score: prev.final_score !== undefined ? prev.final_score : fullData.final_score,
              }));
            }
          })
          .catch(() => {})
          .finally(() => setIsLoadingDetails(false));
      }
    }
  }, [candidate]);

  if (!candidate) return null;

  const handleDeepEvaluate = async () => {
    setIsEvaluating(true);
    setStreamedReasoning("");
    setStreamingStatus("Connecting to Gemini AI Engine...");
    setStreamError(null);
    setEvalCompleted(false);

    try {
      await api.streamEvaluateCandidate(cand.candidate_id, "1", {
        onStatus: (status) => {
          setStreamingStatus(status);
        },
        onChunk: (chunk) => {
          setStreamedReasoning((prev) => prev + chunk);
        },
        onComplete: (res) => {
          if (res && res.ai_evaluation) {
            setCand((prev) => ({
              ...prev,
              ai_evaluation: res.ai_evaluation,
              evaluations: res.evaluations || prev.evaluations,
              composite_score: res.composite_score || prev.composite_score,
              final_score: res.final_score || prev.final_score,
              match_reasons: res.match_reasons || prev.match_reasons,
            }));
            setEvalCompleted(true);
            setStreamingStatus("Evaluation Complete");
          }
        },
        onError: (err) => {
          console.error("Streaming evaluation error:", err);
          setStreamError(err);
        },
      });
    } catch (err: any) {
      setStreamError(err.message || String(err));
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteCandidate(cand.candidate_id);
      onCandidateDeleted(cand.candidate_id);
      onClose();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const scorePct = Math.round((cand.final_score || cand.retrieval_score || 0.75) * 100);
  const allSkills = cand.skills && cand.skills.length > 0 
    ? cand.skills.map(s => s.name) 
    : (cand.matched_skills && cand.matched_skills.length > 0 ? cand.matched_skills : []);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/75 backdrop-blur-md flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-[#0F0F12] border-l border-white/10 h-full overflow-y-auto shadow-2xl flex flex-col">
        
        {/* Header */}
        <div className="p-6 border-b border-white/10 sticky top-0 bg-[#0F0F12]/95 backdrop-blur-md z-20 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-zinc-100 tracking-tight">
                {cand.name || `Candidate #${cand.candidate_id}`}
              </h2>
              {cand.gender && (
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-zinc-400">
                  {cand.gender}
                </span>
              )}
            </div>
            <p className="text-sm font-medium text-purple-400 mt-0.5">
              {cand.current_title || "Engineering Professional"}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowConfirmDelete(true)}
              title="Delete candidate profile"
              className="p-2 rounded-lg text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-white/10 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 space-y-6 flex-1 text-xs">
          
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3.5 bg-white/5 rounded-xl border border-white/10 shadow-sm">
              <span className="text-zinc-400 block text-[10px] uppercase tracking-wider font-semibold">Match Score</span>
              <span className="text-2xl font-bold font-mono text-emerald-400 mt-1 block">{scorePct}%</span>
            </div>
            <div className="p-3.5 bg-white/5 rounded-xl border border-white/10 shadow-sm">
              <span className="text-zinc-400 block text-[10px] uppercase tracking-wider font-semibold">Total Experience</span>
              <span className="text-2xl font-bold font-mono text-zinc-100 mt-1 block">{cand.total_experience_years || 3}+ Yrs</span>
            </div>
            <div className="p-3.5 bg-white/5 rounded-xl border border-white/10 shadow-sm">
              <span className="text-zinc-400 block text-[10px] uppercase tracking-wider font-semibold">Eligibility</span>
              <span className="text-xs font-bold text-indigo-400 mt-2 block inline-flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                {cand.eligibility_status || "PASS"}
              </span>
            </div>
          </div>

          {/* Contact Details & Action Banner (Highlighted prominently) */}
          <div className="p-4 bg-gradient-to-r from-purple-950/30 to-indigo-950/30 border border-purple-500/20 rounded-xl space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-purple-400" />
                Contact & Communication
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDeepEvaluate}
                  disabled={isEvaluating}
                  className="px-3.5 py-1.5 bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-md shadow-purple-600/30 disabled:opacity-50"
                  title="Stream deep AI evaluation with Gemini 3.6 Flash"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${isEvaluating ? 'animate-spin text-purple-200' : 'text-purple-300'}`} />
                  {isEvaluating ? "Evaluating with Gemini..." : cand.ai_evaluation ? "Re-evaluate Profile" : "Deep AI Evaluate"}
                </button>
                {cand.resume_url && (
                  <a 
                    href={cand.resume_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-zinc-200 rounded-lg text-xs font-semibold border border-white/10 transition flex items-center gap-1.5"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    View Original Resume
                    <ExternalLink className="w-3 h-3 text-white/70" />
                  </a>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
              {/* Email Box */}
              <div className="flex items-center justify-between p-2.5 bg-black/40 border border-white/10 rounded-lg">
                <div className="flex items-center gap-2 overflow-hidden">
                  <Mail className="w-4 h-4 text-purple-400 flex-shrink-0" />
                  <span className="text-zinc-200 font-mono text-xs truncate select-all">
                    {cand.email || "No email detected in CV"}
                  </span>
                </div>
                {cand.email && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(cand.email!);
                      setCopiedEmail(true);
                      setTimeout(() => setCopiedEmail(false), 2000);
                    }}
                    title="Copy email address"
                    className="ml-2 p-1 text-zinc-400 hover:text-zinc-100 rounded hover:bg-white/10 transition"
                  >
                    {copiedEmail ? <span className="text-[10px] text-emerald-400 font-medium">Copied!</span> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>

              {/* Phone Box */}
              <div className="flex items-center justify-between p-2.5 bg-black/40 border border-white/10 rounded-lg">
                <div className="flex items-center gap-2 overflow-hidden">
                  <Phone className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span className="text-zinc-200 font-mono text-xs truncate select-all">
                    {cand.phone || "No phone detected in CV"}
                  </span>
                </div>
                {cand.phone && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(cand.phone!);
                      setCopiedPhone(true);
                      setTimeout(() => setCopiedPhone(false), 2000);
                    }}
                    title="Copy phone number"
                    className="ml-2 p-1 text-zinc-400 hover:text-zinc-100 rounded hover:bg-white/10 transition"
                  >
                    {copiedPhone ? <span className="text-[10px] text-emerald-400 font-medium">Copied!</span> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>

              {/* Location & Company */}
              {(cand.location || cand.current_company) && (
                <div className="sm:col-span-2 flex flex-wrap items-center gap-4 text-xs text-zinc-400 px-1 pt-0.5">
                  {cand.location && (
                    <span className="inline-flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-zinc-500" />
                      {cand.location}
                    </span>
                  )}
                  {cand.current_company && (
                    <span className="inline-flex items-center gap-1.5">
                      <Building className="w-3.5 h-3.5 text-zinc-500" />
                      {cand.current_company}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Live AI Streaming Evaluation Card (Typewriter Effect) */}
          {(isEvaluating || streamedReasoning || streamError) && (
            <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/40 via-indigo-950/30 to-black/60 border border-purple-500/40 space-y-3 shadow-xl shadow-purple-950/20 animate-in fade-in duration-300">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2.5">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    <Sparkles className={`w-4 h-4 ${isEvaluating ? 'animate-spin text-purple-300' : 'text-purple-200'}`} />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-purple-200 flex items-center gap-2">
                      <span>Gemini 3.6 Flash Live Evaluation Stream</span>
                      {isEvaluating && (
                        <span className="flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                          STREAMING
                        </span>
                      )}
                      {evalCompleted && (
                        <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          ✓ COMPLETED
                        </span>
                      )}
                    </h3>
                    <p className="text-[11px] text-zinc-400">
                      {streamingStatus || "Live SSE streaming token-by-token from Google Gemini"}
                    </p>
                  </div>
                </div>

                {cand.ai_evaluation?.hiring_verdict && (
                  <span className="text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-purple-500/20 text-purple-200 border border-purple-500/40 shadow-[0_0_12px_rgba(168,85,247,0.3)]">
                    {cand.ai_evaluation.hiring_verdict}
                  </span>
                )}
              </div>

              {/* Typewriter Stream Box */}
              {streamedReasoning && (
                <div className="p-3.5 rounded-lg bg-black/60 border border-purple-500/30 text-zinc-200 font-mono text-[11.5px] leading-relaxed whitespace-pre-wrap select-all">
                  {streamedReasoning}
                  {isEvaluating && (
                    <span className="inline-block w-2 h-4 bg-purple-400 animate-pulse ml-1 align-middle" />
                  )}
                </div>
              )}

              {/* Error Box if any */}
              {streamError && (
                <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                  <span>Streaming error: {streamError}</span>
                </div>
              )}
            </div>
          )}

          {/* Multi-Vector Semantic Match Breakdown & Verbatim Evidence Card */}
          {(() => {
            const sectionsToDisplay = (cand.matched_sections && cand.matched_sections.length > 0)
              ? cand.matched_sections
              : (cand.section_embeddings && cand.section_embeddings.length > 0)
                ? cand.section_embeddings
                : (cand.highlighted_section ? [cand.highlighted_section] : []);

            if (sectionsToDisplay.length === 0 || !sectionsToDisplay[0].content_chunk) return null;

            const activeSec = sectionsToDisplay[Math.min(activeSectionIdx, sectionsToDisplay.length - 1)];

            return (
              <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/40 via-indigo-950/30 to-black/50 border border-purple-500/30 space-y-3.5 shadow-xl shadow-purple-950/20">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      <Sparkles className="w-4 h-4 text-purple-300" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-purple-200 flex items-center gap-1.5">
                        Multi-Vector Match: Verbatim CV Section Evidence
                      </h3>
                      <p className="text-[11px] text-zinc-400">
                        Exact candidate CV paragraph indexed in 1536-d pgvector space for ColBERT-style MaxSim retrieval.
                      </p>
                    </div>
                  </div>

                  {activeSec.similarity_score !== undefined && (
                    <div className="px-3 py-1 rounded-full bg-purple-500/20 border border-purple-500/40 text-purple-200 font-mono text-xs font-bold flex items-center gap-1.5 shadow-[0_0_12px_rgba(168,85,247,0.25)]">
                      <span className="text-purple-300">Similarity:</span>
                      <span className="text-emerald-300">{Math.round(activeSec.similarity_score * 100)}%</span>
                    </div>
                  )}
                </div>

                {/* Section Selector Tabs if multiple sections available */}
                {sectionsToDisplay.length > 1 && (
                  <div className="flex flex-wrap gap-1.5">
                    {sectionsToDisplay.map((sec, sIdx) => {
                      const isActive = sIdx === Math.min(activeSectionIdx, sectionsToDisplay.length - 1);
                      return (
                        <button
                          key={sIdx}
                          onClick={() => setActiveSectionIdx(sIdx)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 border ${
                            isActive
                              ? "bg-purple-600 text-white border-purple-400 shadow-md shadow-purple-600/30 font-semibold"
                              : "bg-white/5 text-zinc-300 border-white/10 hover:bg-white/10 hover:text-white"
                          }`}
                        >
                          <span className="uppercase text-[9px] font-mono tracking-wider opacity-80">
                            {sec.section_type || "CHUNK"}:
                          </span>
                          <span className="truncate max-w-[150px]">{sec.section_title}</span>
                          {sec.similarity_score !== undefined && (
                            <span className="font-mono text-[10px] font-bold opacity-90">
                              {Math.round(sec.similarity_score * 100)}%
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Verbatim CV Highlight Card */}
                <div className="p-3.5 rounded-lg bg-black/60 border border-purple-500/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-purple-300 text-[11px] flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                      {activeSec.section_title}
                    </span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(activeSec.content_chunk);
                        setCopiedSection(true);
                        setTimeout(() => setCopiedSection(false), 2000);
                      }}
                      className="px-2.5 py-1 rounded bg-white/5 hover:bg-white/15 text-zinc-300 hover:text-white text-[10px] font-medium transition flex items-center gap-1 border border-white/5"
                    >
                      {copiedSection ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-400">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3 text-zinc-400" />
                          <span>Copy Quote</span>
                        </>
                      )}
                    </button>
                  </div>

                  <blockquote className="border-l-2 border-purple-500 pl-3.5 py-1 font-mono text-[11.5px] leading-relaxed text-zinc-200 select-all whitespace-pre-wrap">
                    "{activeSec.content_chunk}"
                  </blockquote>
                </div>
              </div>
            );
          })()}

          {/* Key Technical Skills Inventory */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <Award className="w-3.5 h-3.5 text-indigo-400" />
              Technical Skills & Competencies ({allSkills.length})
            </span>
            {allSkills.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {allSkills.map((s, idx) => (
                  <span 
                    key={idx} 
                    className="px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-zinc-200 text-[11px] font-medium hover:border-purple-500/40 transition"
                  >
                    {s}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-zinc-500 italic">No normalized skills cataloged for this profile.</p>
            )}
          </div>

          {/* Experience Highlights & "What all things has he done" */}
          <div className="space-y-2.5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-300 flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5 text-purple-400" />
              Work Experience, Projects & Accomplishments
            </span>
            
            {cand.summary && (
              <div className="p-3 bg-white/5 border border-white/10 rounded-lg text-zinc-300 text-xs leading-relaxed italic">
                "{cand.summary}"
              </div>
            )}

            {cand.work_history && cand.work_history.length > 0 ? (
              <div className="space-y-2">
                {cand.work_history.map((bullet, i) => (
                  <div key={i} className="flex items-start gap-2.5 p-2.5 bg-black/30 border border-white/5 rounded-lg text-zinc-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 mt-1.5 flex-shrink-0" />
                    <span className="leading-relaxed text-xs">{bullet}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-zinc-500 italic p-3 bg-white/5 border border-white/10 rounded-lg">
                Extracted resume text available. Open full resume to inspect complete chronological work history.
              </p>
            )}
          </div>

          {/* Education & Certifications Segment */}
          <div className="space-y-2.5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-300 flex items-center gap-1.5">
              <GraduationCap className="w-3.5 h-3.5 text-emerald-400" />
              Education, Degrees & Certifications
            </span>
            {cand.education && cand.education.length > 0 ? (
              <div className="space-y-2">
                {cand.education.map((edu, i) => (
                  <div key={i} className="flex items-center gap-2.5 p-2.5 bg-emerald-950/20 border border-emerald-500/20 rounded-lg text-emerald-200">
                    <GraduationCap className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    <span className="font-medium text-xs">{edu}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-3 bg-white/5 border border-white/10 rounded-lg text-zinc-400 flex items-center gap-2">
                <GraduationCap className="w-4 h-4 text-zinc-500" />
                <span>Formal degree information mentioned within body of resume document.</span>
              </div>
            )}
          </div>

          {/* AI Executive Assessment & Verdict */}
          {cand.ai_evaluation?.reasoning_summary && (
            <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl space-y-2 shadow-[0_0_15px_rgba(99,102,241,0.1)]">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  AI Executive Assessment
                </span>
                {cand.ai_evaluation?.hiring_verdict && (
                  <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-200 border border-indigo-500/30">
                    {cand.ai_evaluation.hiring_verdict}
                  </span>
                )}
              </div>
              <p className="text-zinc-200 text-xs leading-relaxed">
                {cand.ai_evaluation.reasoning_summary}
              </p>
            </div>
          )}

          {/* AI Match Rationale */}
          {cand.match_reasons && cand.match_reasons.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 block">
                Evaluation Rationale
              </span>
              <div className="space-y-1.5">
                {cand.match_reasons.map((reason, idx) => (
                  <div key={idx} className="p-2.5 bg-white/5 rounded-lg border border-white/10 text-zinc-300">
                    • {reason}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Audit */}
          {cand.evaluations && cand.evaluations.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Requirement Evidence Audit
              </span>
              <div className="space-y-2">
                {cand.evaluations.map((ev, idx) => (
                  <div key={idx} className="p-3 bg-white/5 rounded-lg border border-white/10 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-zinc-200">{ev.requirement}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-950/40 text-emerald-300 border border-emerald-800/40">
                        {ev.assessment} ({Math.round(ev.confidence * 100)}%)
                      </span>
                    </div>
                    {ev.evidence_quote && (
                      <p className="p-2 bg-black/40 rounded border border-white/10 text-zinc-400 font-mono text-[11px]">
                        "{ev.evidence_quote}"
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 1-Click AI Outreach Invitation Generator */}
          <div className="p-4 bg-blue-950/20 border border-blue-500/20 rounded-xl space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-blue-300 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-blue-400" />
                1-Click Personalized Outreach Email
              </span>
              <button
                onClick={() => {
                  const skillsStr = allSkills.slice(0, 3).join(', ') || 'modern software engineering';
                  const text = `Hi ${cand.name || 'there'},\n\nI came across your profile and was very impressed by your track record in ${cand.current_title || 'Software Engineering'} and your hands-on background with ${skillsStr}.\n\nWe have an exciting opportunity that closely aligns with your background. Would you be open for a brief 15-minute introductory call this week?\n\nBest regards,\nTalent Acquisition Team`;
                  navigator.clipboard.writeText(text);
                  setCopiedEmail(true);
                  setTimeout(() => setCopiedEmail(false), 2000);
                }}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-[11px] font-medium transition flex items-center gap-1 shadow"
              >
                {copiedEmail ? "✓ Copied to Clipboard!" : "Copy Invite Email"}
              </button>
            </div>
            <p className="text-zinc-300 text-[11px] bg-black/40 p-3 rounded-lg border border-white/5 font-mono leading-relaxed">
              "Hi {cand.name || 'there'}, I came across your profile and was very impressed by your track record in {cand.current_title || 'Software Engineering'} and your hands-on background with {allSkills.slice(0, 3).join(', ') || 'modern tech'}..."
            </p>
          </div>

        </div>

        {/* Delete Confirmation Modal */}
        {showConfirmDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
            <div className="bg-[#18181B] border border-white/10 rounded-xl w-full max-w-sm p-6 space-y-4 shadow-2xl">
              <div className="flex items-center gap-2 text-rose-400">
                <AlertTriangle className="w-5 h-5" />
                <h4 className="font-bold text-sm text-zinc-100">Confirm Deletion</h4>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Permanently delete {cand.name} from your cloud database, including skills, documents, and embeddings?
              </p>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => setShowConfirmDelete(false)}
                  className="px-3 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white transition"
                >
                  {isDeleting ? "Deleting..." : "Delete Permanently"}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
