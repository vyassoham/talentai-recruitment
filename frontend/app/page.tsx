"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "../components/Navbar";
import { NetworkGuard } from "../components/NetworkGuard";
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
  const [activeTab, setActiveTab] = useState("jobs");
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
    <NetworkGuard>
      <div className="min-h-screen bg-[#0A0A0A] text-zinc-100 flex flex-col antialiased relative overflow-hidden">
        {/* Ambient Background Gradients */}
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-purple-600/10 rounded-full blur-[120px] pointer-events-none opacity-50" />
        <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-emerald-600/10 rounded-full blur-[100px] pointer-events-none opacity-40" />

        {/* Top Navigation */}
        <Navbar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />

        {/* Main Container */}
        <main className="flex-1 w-full px-3 sm:px-5 lg:px-8 py-6 space-y-6 relative z-10" style={{maxWidth: '100%'}}>
          
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
        <footer className="border-t border-white/10 bg-[#0A0A0A]/80 backdrop-blur-md py-4 mt-12 text-xs text-zinc-500 relative z-10">
          <div className="w-full px-3 sm:px-5 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span className="text-zinc-400">TalentAI Workspace</span>
              <span className="text-zinc-600">•</span>
              <span>Home WiFi Protected</span>
            </div>
            <div className="text-zinc-500 text-[11px]">
              Supabase pgvector • Google Gemini 3.6 Flash • Upstash Redis
            </div>
          </div>
        </footer>
      </div>
    </NetworkGuard>
  );
}
