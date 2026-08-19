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
import { ShieldAlert, Sparkles, CheckCircle2 } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState("match");
  const [token, setToken] = useState<string | null>(null);
  const [isSeeding, setIsSeeding] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>("1");
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateResult | null>(null);

  // Initialize token from storage
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
      alert("Successfully authenticated! JWT Bearer active.");
    } catch (err: any) {
      alert(`Login failed: ${err.message}`);
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
      alert(`Admin account active: ${res.email} / ${res.password}. Logging you in...`);
      await handleLogin(res.email, res.password);
    } catch (err: any) {
      alert(`Admin account already ready: admin@recruit.ai / admin_password`);
    } finally {
      setIsSeeding(false);
    }
  };

  const handleJobParsed = (jobId: string, requirements: RequirementItem[]) => {
    setActiveJobId(jobId);
    setActiveTab("match");
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation Bar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        token={token}
        onLogin={handleLogin}
        onLogout={handleLogout}
        onSeedAdmin={handleSeedAdmin}
        isSeeding={isSeeding}
      />

      {/* Main Workspace Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        
        {/* Banner if Unauthenticated */}
        {!token && (
          <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border border-amber-500/30 text-amber-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
                <ShieldAlert className="w-4 h-4" />
              </div>
              <div>
                <span className="font-bold text-amber-100 block">Recruiter Authentication Available</span>
                <span className="text-[11px] text-amber-300/80">Log in or 1-click bootstrap to manage protected candidate files and rate limits.</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleSeedAdmin}
                disabled={isSeeding}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold transition text-xs shadow-md active:scale-95"
              >
                {isSeeding ? "Bootstrapping..." : "1-Click Bootstrap Admin"}
              </button>
            </div>
          </div>
        )}

        {/* Tab 1: Match & Search */}
        {activeTab === "match" && (
          <div className="space-y-6">
            <CandidateSearchResults
              activeJobId={activeJobId}
              onSelectCandidate={(cand) => setSelectedCandidate(cand)}
            />
          </div>
        )}

        {/* Tab 2: CV Ingestion */}
        {activeTab === "ingestion" && (
          <div className="space-y-6">
            <ResumeUploader />
          </div>
        )}

        {/* Tab 3: Job Requirements */}
        {activeTab === "jobs" && (
          <div className="space-y-6">
            <JobParserSection
              activeJobId={activeJobId}
              onJobParsed={handleJobParsed}
            />
          </div>
        )}

        {/* Tab 4: Passive Sourcing */}
        {activeTab === "sourcing" && (
          <div className="space-y-6">
            <PassiveSourcingTab />
          </div>
        )}

        {/* Tab 5: Profile Staleness */}
        {activeTab === "staleness" && (
          <div className="space-y-6">
            <StalenessManagerTab />
          </div>
        )}

        {/* Tab 6: DEI & Compliance */}
        {activeTab === "dei" && (
          <div className="space-y-6">
            <DEIAnalyticsTab activeJobId={activeJobId} />
          </div>
        )}

        {/* Tab 7: AI Cost & Telemetry */}
        {activeTab === "telemetry" && (
          <div className="space-y-6">
            <AICostTelemetryTab />
          </div>
        )}

      </main>

      {/* Candidate Profile Slide-Over Drawer */}
      <CandidateDetailModal
        candidate={selectedCandidate}
        onClose={() => setSelectedCandidate(null)}
        onCandidateDeleted={() => setSelectedCandidate(null)}
      />

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-[#0f172a]/80 py-8 mt-16 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>TalentAI Enterprise Platform • v2.0 Production</span>
          </div>
          <div className="text-slate-400 text-[11px]">
            Powered by Supabase pgvector, Google Gemini 3.6 Flash & Upstash Redis
          </div>
        </div>
      </footer>
    </div>
  );
}
