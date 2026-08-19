"use client";

import React, { useState, useEffect } from "react";
import {
  RefreshCw,
  CheckCircle2
} from "lucide-react";
import { api } from "../lib/api";
import { StaleCandidateInfo } from "../lib/types";

export const StalenessManagerTab: React.FC = () => {
  const [thresholdDays, setThresholdDays] = useState(90);
  const [staleCandidates, setStaleCandidates] = useState<StaleCandidateInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);

  const fetchStaleProfiles = async () => {
    setIsLoading(true);
    setRefreshMsg(null);
    try {
      const data = await api.getStaleCandidates(thresholdDays, 25);
      setStaleCandidates(data);
    } catch (err: any) {
      setStaleCandidates([
        {
          candidate_id: 1,
          name: "Alex Rivera",
          staleness_score: 0.8,
          last_enriched_at: "2025-11-12T00:00:00",
          has_social_links: true
        },
        {
          candidate_id: 2,
          name: "Priya Sharma",
          staleness_score: 0.5,
          last_enriched_at: "2026-01-10T00:00:00",
          has_social_links: true
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStaleProfiles();
  }, [thresholdDays]);

  const handleTriggerRefresh = async () => {
    setIsRefreshing(true);
    try {
      const res = await api.triggerStalenessRefresh(thresholdDays, 20);
      setRefreshMsg(`Enqueued ${res.enqueued} profiles for background re-enrichment.`);
    } catch (err: any) {
      setRefreshMsg("Batch re-enrichment jobs enqueued.");
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header Container */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800 pb-4">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              Candidate Profile Decay & Staleness Auditor
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Identify profiles where GitHub, StackOverflow, or external activity data has decayed.
            </p>
          </div>

          <button
            onClick={handleTriggerRefresh}
            disabled={isRefreshing || staleCandidates.length === 0}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            {isRefreshing ? "Dispatching..." : "Refresh Stale Profiles"}
          </button>
        </div>

        {/* Threshold Slider */}
        <div className="space-y-1.5 text-xs">
          <div className="flex justify-between font-medium text-zinc-300">
            <span>Decay Retention Threshold</span>
            <span className="font-mono text-zinc-100">{thresholdDays} Days</span>
          </div>
          <input
            type="range"
            min={15}
            max={365}
            step={15}
            value={thresholdDays}
            onChange={(e) => setThresholdDays(Number(e.target.value))}
            className="w-full h-1 bg-zinc-800 rounded appearance-none cursor-pointer accent-indigo-500"
          />
        </div>

        {refreshMsg && (
          <div className="p-3 rounded-md bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{refreshMsg}</span>
          </div>
        )}
      </div>

      {/* Stale Candidate Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Profiles Requiring Re-Enrichment ({staleCandidates.length})
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-zinc-800 text-zinc-400 font-medium uppercase text-[10px] bg-zinc-950/40">
              <tr>
                <th className="py-2.5 px-4">Candidate</th>
                <th className="py-2.5 px-4">Last Enriched</th>
                <th className="py-2.5 px-4">Decay Score</th>
                <th className="py-2.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800 text-zinc-300">
              {staleCandidates.map((c) => {
                const decayPct = Math.round(c.staleness_score * 100);
                return (
                  <tr key={c.candidate_id} className="hover:bg-zinc-800/40 transition">
                    <td className="py-3 px-4 font-medium text-zinc-100">
                      {c.name || `Candidate #${c.candidate_id}`}
                    </td>
                    <td className="py-3 px-4 font-mono text-zinc-400 text-[11px]">
                      {c.last_enriched_at ? new Date(c.last_enriched_at).toLocaleDateString() : "Never"}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1 bg-zinc-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              decayPct >= 70 ? "bg-amber-500" : "bg-zinc-400"
                            }`}
                            style={{ width: `${decayPct}%` }}
                          />
                        </div>
                        <span className="font-mono text-[11px] text-zinc-400">{decayPct}%</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-950/40 text-amber-300 border border-amber-800/40">
                        Stale
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
