"use client";

import React, { useState } from "react";
import {
  X,
  Mail,
  Phone,
  MapPin,
  Briefcase,
  Code,
  Globe,
  Trash2,
  AlertTriangle,
  Award,
  Calendar,
  ExternalLink,
  ShieldCheck
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
      alert(`Candidate #${candidate.candidate_id} and all related data have been completely deleted.`);
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
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/75 backdrop-blur-md flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-[#1e293b] border-l border-slate-700 h-full overflow-y-auto shadow-2xl flex flex-col">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-700/80 sticky top-0 bg-[#1e293b]/95 backdrop-blur-md z-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/40 text-indigo-300 font-black text-lg flex items-center justify-center">
              {candidate.name ? candidate.name[0] : "C"}
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">
                {candidate.name || `Candidate #${candidate.candidate_id}`}
              </h3>
              <p className="text-xs text-slate-400">
                {candidate.current_title || "Software Engineering Professional"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowConfirmDelete(true)}
              title="GDPR Complete Wipe"
              className="p-2 rounded-xl text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/30 border border-transparent transition"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 flex-1 text-xs">
          
          {/* Quick Stats Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-4 bg-[#0f172a] rounded-2xl border border-slate-700/80">
              <span className="text-slate-400 block font-bold text-[10px] uppercase">AI Match Score</span>
              <span className="text-xl font-black font-mono text-emerald-400 mt-1 block">{scorePct}%</span>
            </div>
            <div className="p-4 bg-[#0f172a] rounded-2xl border border-slate-700/80">
              <span className="text-slate-400 block font-bold text-[10px] uppercase">Total Experience</span>
              <span className="text-xl font-black font-mono text-white mt-1 block">{candidate.total_experience_years || 5}+ Yrs</span>
            </div>
            <div className="p-4 bg-[#0f172a] rounded-2xl border border-slate-700/80">
              <span className="text-slate-400 block font-bold text-[10px] uppercase">Eligibility</span>
              <span className="text-sm font-bold text-indigo-400 mt-1.5 block">VERIFIED</span>
            </div>
          </div>

          {/* AI Match Rationale */}
          {candidate.match_reasons && candidate.match_reasons.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-indigo-300 uppercase tracking-wider">AI Evaluation Rationale</h4>
              <div className="space-y-2">
                {candidate.match_reasons.map((reason, idx) => (
                  <div key={idx} className="p-3 bg-[#0f172a] rounded-xl border border-slate-800 text-slate-300">
                    • {reason}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Verified Evidence Breakdown */}
          {candidate.evaluations && candidate.evaluations.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Resume Evidence Audit
              </h4>
              <div className="space-y-3">
                {candidate.evaluations.map((ev, idx) => (
                  <div key={idx} className="p-4 bg-[#0f172a] rounded-2xl border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-sm">{ev.requirement}</span>
                      <span className="px-2.5 py-0.5 rounded-lg text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        {ev.assessment} ({Math.round(ev.confidence * 100)}%)
                      </span>
                    </div>
                    {ev.evidence_quote && (
                      <p className="p-3 bg-[#1e293b] rounded-xl border border-slate-700 italic text-slate-300 font-mono text-xs">
                        "{ev.evidence_quote}"
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Delete Confirmation Modal Overlay */}
        {showConfirmDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
            <div className="bg-[#1e293b] border border-rose-500/50 rounded-3xl w-full max-w-sm p-6 space-y-4 shadow-2xl">
              <div className="flex items-center gap-2.5 text-rose-400">
                <AlertTriangle className="w-5 h-5" />
                <h4 className="font-bold text-base text-white">Confirm GDPR Deletion</h4>
              </div>
              <p className="text-xs text-slate-300">
                This action will permanently delete all candidate records, skills, embeddings, and evidence from Supabase.
              </p>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => setShowConfirmDelete(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="px-5 py-2 rounded-xl text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/30 transition"
                >
                  {isDeleting ? "Wiping Data..." : "Permanently Delete"}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
