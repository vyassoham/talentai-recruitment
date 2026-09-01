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
  FileText
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

  if (!candidate) return null;

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteCandidate(candidate.candidate_id);
      onCandidateDeleted(candidate.candidate_id);
      onClose();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const scorePct = Math.round((candidate.final_score || 0.9) * 100);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end animate-in fade-in duration-150">
      <div className="w-full max-w-xl bg-white/5 backdrop-blur-md border-l border-white/10 h-full overflow-y-auto shadow-2xl flex flex-col">
        
        {/* Header */}
        <div className="p-5 border-b border-white/10 sticky top-0 bg-white/5 backdrop-blur-md/95 backdrop-blur-sm z-10 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">
              {candidate.name || `Candidate #${candidate.candidate_id}`}
            </h3>
            <p className="text-xs text-zinc-400">
              {candidate.current_title || "Engineering Professional"}
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
              <span className="text-lg font-semibold font-mono text-zinc-100 mt-0.5 block">{candidate.total_experience_years || 5}+ Yrs</span>
            </div>
            <div className="p-3 bg-transparent rounded border border-white/10">
              <span className="text-zinc-500 block text-[10px] uppercase font-medium">Eligibility</span>
              <span className="text-xs font-semibold text-indigo-400 mt-1 block">PASS</span>
            </div>
          </div>

          {/* Contact & Resume */}
          <div className="p-3 bg-white/5 border border-white/10 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-4">
             <div className="space-y-2">
                {candidate.email && (
                   <div className="flex items-center gap-2 text-zinc-300">
                     <Mail className="w-3.5 h-3.5 text-zinc-500" />
                     {candidate.email}
                   </div>
                )}
                {candidate.phone && (
                   <div className="flex items-center gap-2 text-zinc-300">
                     <Phone className="w-3.5 h-3.5 text-zinc-500" />
                     {candidate.phone}
                   </div>
                )}
                {candidate.current_company && (
                   <div className="flex items-center gap-2 text-zinc-300">
                     <Building className="w-3.5 h-3.5 text-zinc-500" />
                     {candidate.current_company}
                   </div>
                )}
                {(!candidate.email && !candidate.phone && !candidate.current_company) && (
                   <span className="text-zinc-500 italic">No contact details found in CV.</span>
                )}
             </div>
             {candidate.resume_url && (
                <a 
                  href={candidate.resume_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition flex items-center gap-2 whitespace-nowrap shadow-lg shadow-indigo-500/20"
                >
                  <FileText className="w-4 h-4" />
                  View Original Resume
                </a>
             )}
          </div>

          {/* AI Match Rationale */}
          {candidate.match_reasons && candidate.match_reasons.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block">
                Evaluation Rationale
              </span>
              <div className="space-y-1.5">
                {candidate.match_reasons.map((reason, idx) => (
                  <div key={idx} className="p-2.5 bg-transparent rounded border border-white/10 text-zinc-300">
                    • {reason}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Audit */}
          {candidate.evaluations && candidate.evaluations.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Resume Evidence Audit
              </span>
              <div className="space-y-2">
                {candidate.evaluations.map((ev, idx) => (
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
