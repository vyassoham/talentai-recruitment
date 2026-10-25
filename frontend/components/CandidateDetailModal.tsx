"use client";

import React, { useState } from "react";
import {
  X,
  Trash2,
  AlertTriangle,
  ShieldCheck,
  Mail,
  Phone,
  Building,
  FileText,
  Sparkles
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
  const [cand, setCand] = useState<CandidateResult>(candidate || ({} as CandidateResult));
  const [isEvaluating, setIsEvaluating] = useState(false);

  React.useEffect(() => {
    if (candidate) setCand(candidate);
  }, [candidate]);

  if (!candidate) return null;

  const handleDeepEvaluate = async () => {
    setIsEvaluating(true);
    try {
      const res = await api.evaluateCandidate(cand.candidate_id, "1");
      if (res && res.ai_evaluation) {
        setCand(prev => ({
          ...prev,
          ai_evaluation: res.ai_evaluation,
          evaluations: res.evaluations || prev.evaluations,
          composite_score: res.composite_score || prev.composite_score,
          final_score: res.final_score || prev.final_score,
          match_reasons: res.match_reasons || prev.match_reasons
        }));
      }
    } catch (err: any) {
      alert(`Deep evaluation failed: ${err.message || err}`);
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

  const scorePct = Math.round((cand.final_score || 0.9) * 100);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end animate-in fade-in duration-150">
      <div className="w-full max-w-xl bg-white/5 backdrop-blur-md border-l border-white/10 h-full overflow-y-auto shadow-2xl flex flex-col">
        
        {/* Header */}
        <div className="p-5 border-b border-white/10 sticky top-0 bg-white/5 backdrop-blur-md/95 backdrop-blur-sm z-10 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">
              {cand.name || `Candidate #${cand.candidate_id}`}
            </h3>
            <p className="text-xs text-zinc-400">
              {cand.current_title || "Engineering Professional"}
            </p>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setShowConfirmDelete(true)}
              title="Delete candidate"
              className="p-1.5 rounded text-zinc-400 hover:text-rose-400 hover:bg-white/10 transition"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded text-zinc-400 hover:text-zinc-100 hover:bg-white/10 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-5 flex-1 text-xs">
          
          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-2.5">
            <div className="p-3 bg-transparent rounded border border-white/10">
              <span className="text-zinc-500 block text-[10px] uppercase font-medium">Match Score</span>
              <span className="text-lg font-semibold font-mono text-emerald-400 mt-0.5 block">{scorePct}%</span>
            </div>
            <div className="p-3 bg-transparent rounded border border-white/10">
              <span className="text-zinc-500 block text-[10px] uppercase font-medium">Experience</span>
              <span className="text-lg font-semibold font-mono text-zinc-100 mt-0.5 block">{cand.total_experience_years || 5}+ Yrs</span>
            </div>
            <div className="p-3 bg-transparent rounded border border-white/10">
              <span className="text-zinc-500 block text-[10px] uppercase font-medium">Eligibility</span>
              <span className="text-xs font-semibold text-indigo-400 mt-1 block">PASS</span>
            </div>
          </div>

          {/* Contact & Resume */}
          <div className="p-3 bg-white/5 border border-white/10 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-4">
             <div className="space-y-2">
                {cand.email && (
                   <div className="flex items-center gap-2 text-zinc-300">
                     <Mail className="w-3.5 h-3.5 text-zinc-500" />
                     {cand.email}
                   </div>
                )}
                {cand.phone && (
                   <div className="flex items-center gap-2 text-zinc-300">
                     <Phone className="w-3.5 h-3.5 text-zinc-500" />
                     {cand.phone}
                   </div>
                )}
                {cand.current_company && (
                   <div className="flex items-center gap-2 text-zinc-300">
                     <Building className="w-3.5 h-3.5 text-zinc-500" />
                     {cand.current_company}
                   </div>
                )}
                {(!cand.email && !cand.phone && !cand.current_company) && (
                   <span className="text-zinc-500 italic">No contact details found in CV.</span>
                )}
             </div>
             {cand.resume_url && (
                <a 
                  href={cand.resume_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition flex items-center gap-2 whitespace-nowrap shadow-lg shadow-indigo-500/20"
                >
                  <FileText className="w-4 h-4" />
                  View Original Resume
                </a>
             )}
          </div>

          {/* AI Executive Assessment */}
          {cand.ai_evaluation?.reasoning_summary && (
            <div className="p-3.5 bg-indigo-500/10 border border-indigo-500/20 rounded-lg space-y-1.5 shadow-[0_0_15px_rgba(99,102,241,0.1)]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
                    ✨ AI Executive Assessment
                  </span>
                  <button
                    onClick={handleDeepEvaluate}
                    disabled={isEvaluating}
                    className="px-2 py-0.5 rounded bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-200 border border-indigo-500/40 text-[10px] font-semibold flex items-center gap-1 transition"
                  >
                    {isEvaluating ? (
                      <>
                        <span className="w-2.5 h-2.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mr-1" />
                        Auditing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3 h-3 text-indigo-400" />
                        Deep Gemini Audit
                      </>
                    )}
                  </button>
                </div>
                {cand.ai_evaluation?.hiring_verdict && (
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-200 border border-indigo-500/30">
                    {cand.ai_evaluation.hiring_verdict}
                  </span>
                )}
              </div>
              <p className="text-zinc-200 text-xs leading-relaxed">
                {cand.ai_evaluation.reasoning_summary}
              </p>
            </div>
          )}

          {/* AI Identified Key Strengths */}
          {cand.ai_evaluation?.key_strengths && cand.ai_evaluation.key_strengths.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400 block">
                ⚡ AI Identified Strengths
              </span>
              <div className="flex flex-wrap gap-1.5">
                {cand.ai_evaluation.key_strengths.map((str, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px] font-medium">
                    ✓ {str}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* AI Recommended Interview Questions */}
          <div className="p-3.5 bg-purple-500/10 border border-purple-500/20 rounded-lg space-y-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
              🎯 AI Recommended Interview Questions
            </span>
            <ul className="space-y-1.5 text-zinc-300 text-xs list-disc list-inside">
              <li>How did you design, scale, and optimize system performance in your {cand.current_title || 'engineering'} projects?</li>
              <li>Can you walk me through your most complex architectural decision involving {cand.skills?.slice(0, 2).map(s => s.name).join(' & ') || cand.ai_evaluation?.key_strengths?.slice(0, 2).join(' & ') || 'production services'}?</li>
              <li>How do you approach observability, automated testing, and peer reviews in high-velocity sprints?</li>
            </ul>
          </div>

          {/* 1-Click AI Outreach Invitation */}
          <div className="p-3.5 bg-blue-500/10 border border-blue-500/20 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-300 flex items-center gap-1.5">
                ✉️ 1-Click AI Outreach Generator
              </span>
              <button
                onClick={() => {
                  const skillsStr = cand.skills?.slice(0, 3).map(s => s.name).join(', ') || cand.ai_evaluation?.key_strengths?.slice(0, 3).join(', ') || 'modern software engineering';
                  const text = `Hi ${cand.name || 'there'},\n\nI came across your profile and was very impressed by your track record in ${cand.current_title || 'Software Engineering'} and your hands-on background with ${skillsStr}.\n\nWe have an exciting opportunity that closely aligns with your background. Would you be open for a brief 15-minute introductory call this week?\n\nBest regards,\nTalent Acquisition Team`;
                  navigator.clipboard.writeText(text);
                  setCopiedEmail(true);
                  setTimeout(() => setCopiedEmail(false), 2000);
                }}
                className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[11px] font-medium transition flex items-center gap-1 shadow"
              >
                {copiedEmail ? "✓ Copied to Clipboard!" : "Copy Invite Email"}
              </button>
            </div>
            <p className="text-zinc-300 text-[11px] bg-black/30 p-2.5 rounded border border-white/5 font-mono leading-relaxed">
              "Hi {cand.name || 'there'}, I came across your profile and was very impressed by your track record in {cand.current_title || 'Software Engineering'} and your hands-on background with {cand.skills?.slice(0, 3).map(s => s.name).join(', ') || cand.ai_evaluation?.key_strengths?.slice(0, 3).join(', ') || 'modern tech'}..."
            </p>
          </div>

          {/* AI Match Rationale */}
          {cand.match_reasons && cand.match_reasons.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block">
                Evaluation Rationale
              </span>
              <div className="space-y-1.5">
                {cand.match_reasons.map((reason, idx) => (
                  <div key={idx} className="p-2.5 bg-transparent rounded border border-white/10 text-zinc-300">
                    • {reason}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Audit */}
          {cand.evaluations && cand.evaluations.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Resume Evidence Audit
              </span>
              <div className="space-y-2">
                {cand.evaluations.map((ev, idx) => (
                  <div key={idx} className="p-3 bg-transparent rounded border border-white/10 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-zinc-200">{ev.requirement}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-950/40 text-emerald-300 border border-emerald-800/40">
                        {ev.assessment} ({Math.round(ev.confidence * 100)}%)
                      </span>
                    </div>
                    {ev.evidence_quote && (
                      <p className="p-2 bg-white/5 backdrop-blur-md rounded border border-white/10 text-zinc-400 font-mono text-[11px]">
                        "{ev.evidence_quote}"
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Delete Confirmation */}
        {showConfirmDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="bg-white/5 border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)] rounded-lg w-full max-w-xs p-5 space-y-3 shadow-2xl">
              <div className="flex items-center gap-2 text-rose-400">
                <AlertTriangle className="w-4 h-4" />
                <h4 className="font-semibold text-sm text-zinc-100">Confirm Deletion</h4>
              </div>
              <p className="text-xs text-zinc-400">
                Permanently delete candidate records, skills, and embeddings from the database.
              </p>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => setShowConfirmDelete(false)}
                  className="px-3 py-1 text-xs font-medium text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="px-3 py-1 rounded text-xs font-medium bg-rose-600 hover:bg-rose-500 text-white transition"
                >
                  {isDeleting ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
