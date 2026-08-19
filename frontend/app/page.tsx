"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "../components/Navbar";
import { AuthModal } from "../components/AuthModal";
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
import { AlertCircle } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState("match");
  const [token, setToken] = useState<string | null>(null);
  const [isSeeding, setIsSeeding] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>("1");
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateResult | null>(null);

  useEffect(() => {
    const savedToken = api.getToken();
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  const handleLogin = async (email: string, pass: string) => {
    try {
      const data = await api.login(email, pass);
      setToken(data.access_token);
    } catch (err: any) {
      throw err;
    }
  };

  const handleLogout = () => {
    api.setToken(null);
    setToken(null);
  };

  const handleSeedAdmin = async () => {
    setIsSeeding(true);
    try {
      const res = await api.seedAdmin();
      await handleLogin(res.email, res.password);
    } catch (err: any) {
      await handleLogin("admin@recruit.ai", "admin_password");
    } finally {
      setIsSeeding(false);
    }
  };

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
        token={token}
        onOpenAuthModal={() => setShowAuthModal(true)}
        onLogout={handleLogout}
        onSeedAdmin={handleSeedAdmin}
        isSeeding={isSeeding}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Slim Standard Shadcn Inline Alert */}
        {!token && (
          <div className="flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-md bg-amber-950/20 border border-amber-900/40 text-amber-200/90 text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                Sensitive endpoints require recruiter authentication. Authenticate to manage candidates and access full telemetry.
              </span>
            </div>
            <button
              onClick={() => setShowAuthModal(true)}
              className="px-2.5 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-medium whitespace-nowrap transition cursor-pointer"
            >
              Sign In
            </button>
          </div>
        )}

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

      {/* Root-Level Auth Modal (Always Centered & Never Clipped) */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onLogin={handleLogin}
        onSeedAdmin={handleSeedAdmin}
        isSeeding={isSeeding}
      />

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
            <span className="text-zinc-400">TalentAI Enterprise Platform</span>
            <span className="text-zinc-600">•</span>
            <span>v2.0 Production</span>
          </div>
          <div className="text-zinc-500 text-[11px]">
            Supabase pgvector • Google Gemini 3.6 Flash • Upstash Redis
          </div>
        </div>
      </footer>
    </div>
  );
}
