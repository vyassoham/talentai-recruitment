"use client";

import React, { useState, useEffect } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  RefreshCw
} from "lucide-react";
import { api } from "../lib/api";
import { DEIReport } from "../lib/types";

interface DEIAnalyticsTabProps {
  activeJobId: string | null;
}

export const DEIAnalyticsTab: React.FC<DEIAnalyticsTabProps> = ({
  activeJobId
}) => {
  const [report, setReport] = useState<DEIReport | null>(null);
  const [thresholdScore, setThresholdScore] = useState(0.7);
  const [isLoading, setIsLoading] = useState(false);

  const fetchDEI = async () => {
    setIsLoading(true);
    try {
      const jobId = activeJobId || "1";
      const data = await api.getDEIAnalytics(jobId, thresholdScore);
      setReport(data);
    } catch (err) { setReport(null); } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDEI();
  }, [activeJobId, thresholdScore]);

  return (
    <div className="space-y-6">
      
      {/* Header Container */}
      <div className="bg-white/5 border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)] rounded-lg p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              DEI Bias Audit & EEOC Adverse Impact Monitor
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Audits AI candidate selection rates across demographic cohorts to enforce the EEOC 4/5ths Rule (80% ratio).
            </p>
          </div>

          <button
            onClick={fetchDEI}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Recalculate
          </button>
        </div>

        {/* Minimal 3 KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-4 bg-transparent rounded border border-white/10 space-y-1">
            <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">EEOC Status</span>
            <div className="flex items-center gap-1.5 pt-0.5">
              {report && !report.adverse_impact_detected ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="font-semibold text-emerald-400 text-sm">Compliant</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span className="font-semibold text-amber-400 text-sm">Disparity Flagged</span>
                </>
              )}
            </div>
          </div>

          <div className="p-4 bg-transparent rounded border border-white/10 space-y-1">
            <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">Adverse Impact Ratio</span>
            <span className="text-lg font-semibold font-mono text-zinc-100 block">
              {report && report.adverse_impact_ratio ? `${(report.adverse_impact_ratio * 100).toFixed(1)}%` : "N/A"}
            </span>
            <span className="text-[10px] text-zinc-500 block">80.0% Minimum Legal Standard</span>
          </div>

          <div className="p-4 bg-transparent rounded border border-white/10 space-y-1">
            <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider block">Demographic Sample</span>
            <span className="text-lg font-semibold font-mono text-zinc-100 block">
              {report ? report.total_evaluations : 0} Candidates
            </span>
            <span className="text-[10px] text-zinc-500 block">Voluntary EEO Disclosures</span>
          </div>
        </div>
      </div>

      {/* Cohort Breakdown */}
      {report && report.disparity_details && (
        <div className="bg-white/5 border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)] rounded-lg p-6 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Demographic Pass-Through Breakdown
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            
            {/* Gender */}
            <div className="bg-transparent p-4 rounded border border-white/10 space-y-2.5">
              <span className="font-medium text-zinc-200 block text-xs">Gender Representation</span>
              <div className="space-y-2">
                {Object.entries(report.disparity_details.gender || {}).map(([cohort, stats]: any) => (
                  <div key={cohort} className="flex items-center justify-between border-b border-zinc-900 pb-1.5">
                    <span className="capitalize text-zinc-400">{cohort}</span>
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-zinc-500 text-[11px]">{stats.passed}/{stats.total} Passed</span>
                      <span className="font-mono font-medium text-zinc-200">{(stats.pass_rate * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Race / Ethnicity */}
            <div className="bg-transparent p-4 rounded border border-white/10 space-y-2.5">
              <span className="font-medium text-zinc-200 block text-xs">Race & Ethnicity Representation</span>
              <div className="space-y-2">
                {Object.entries(report.disparity_details.race_ethnicity || {}).map(([cohort, stats]: any) => (
                  <div key={cohort} className="flex items-center justify-between border-b border-zinc-900 pb-1.5">
                    <span className="capitalize text-zinc-400">{cohort}</span>
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-zinc-500 text-[11px]">{stats.passed}/{stats.total} Passed</span>
                      <span className="font-mono font-medium text-zinc-200">{(stats.pass_rate * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};

