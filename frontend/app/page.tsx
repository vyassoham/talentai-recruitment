"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "../components/Navbar";
import { JobParserSection } from "../components/JobParserSection";
import { ResumeUploader } from "../components/ResumeUploader";
import { CandidateSearchResults } from "../components/CandidateSearchResults";
import { CandidateDetailModal } from "../components/CandidateDetailModal";
import { PassiveSourcingTab } from "../components/PassiveSourcingTab";
import { StalenessManagerTab } from "../components/StalenessManagerTab";
import { DEIAnalyticsTab } from "../components/DEIAnalyticsTab";
import { AICostTelemetryTab } from "../components/AICostTelemetryTab";
import { api } from "../lib/api";
import { CandidateResult, RequirementItem } from "../lib/types";

export default function Home() {
  const [activeTab, setActiveTab] = useState("match");
  const [activeJobId, setActiveJobId] = useState<string | null>("1");
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateResult | null>(null);

  // Transparent auto-authentication on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        if (!api.getToken()) {
          await api.login("admin@recruit.ai", "admin_password");
        }
      } catch (err) {
        // Auto-seed if first time
        try {
          await api.seedAdmin();
          await api.login("admin@recruit.ai", "admin_password");
        } catch (_) {}
      }
    };
    initAuth();
  }, []);

  const handleJobParsed = (jobId: string, requirements: RequirementItem[]) => {
    setActiveJobId(jobId);
    setActiveTab("match");
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col antialiased">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Tab Content */}
        {activeTab === "match" && (
          <CandidateSearchResults
            activeJobId={activeJobId}
            onSelectCandidate={(cand) => setSelectedCandidate(cand)}
          />
        )}

        {activeTab === "ingestion" && <ResumeUploader />}

        {activeTab === "jobs" && (
          <JobParserSection
            activeJobId={activeJobId}
            onJobParsed={handleJobParsed}
          />
        )}

        {activeTab === "sourcing" && <PassiveSourcingTab />}

        {activeTab === "staleness" && <StalenessManagerTab />}

        {activeTab === "dei" && <DEIAnalyticsTab activeJobId={activeJobId} />}

        {activeTab === "telemetry" && <AICostTelemetryTab />}

      </main>

      {/* Slideover Drawer */}
      <CandidateDetailModal
        candidate={selectedCandidate}
        onClose={() => setSelectedCandidate(null)}
        onCandidateDeleted={() => setSelectedCandidate(null)}
      />

      {/* Minimal Footer */}
      <footer className="border-t border-zinc-800/80 bg-zinc-950 py-6 mt-12 text-xs text-zinc-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span className="text-zinc-400">TalentAI Workspace</span>
            <span className="text-zinc-600">•</span>
            <span>Personal Edition</span>
          </div>
          <div className="text-zinc-500 text-[11px]">
            Supabase pgvector • Google Gemini 3.6 Flash • Upstash Redis
          </div>
        </div>
      </footer>
    </div>
  );
}
