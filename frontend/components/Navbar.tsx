"use client";

import React, { useState } from "react";
import {
  Sparkles,
  ShieldCheck,
  Key,
  LogOut,
  Layers,
  FileText,
  Search,
  Globe,
  RefreshCw,
  BarChart3,
  DollarSign,
  CheckCircle2,
  Database,
  Cpu,
  Zap
} from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  token: string | null;
  onLogin: (email: string, pass: string) => void;
  onLogout: () => void;
  onSeedAdmin: () => void;
  isSeeding: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  token,
  onLogin,
  onLogout,
  onSeedAdmin,
  isSeeding
}) => {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [email, setEmail] = useState("admin@recruit.ai");
  const [password, setPassword] = useState("admin_password");

  const navItems = [
    { id: "match", label: "Match & Search", icon: Search },
    { id: "ingestion", label: "CV Ingestion", icon: FileText },
    { id: "jobs", label: "Job Requirements", icon: Layers },
    { id: "sourcing", label: "Passive Sourcing", icon: Globe },
    { id: "staleness", label: "Profile Refresh", icon: RefreshCw },
    { id: "dei", label: "DEI & Compliance", icon: BarChart3 },
    { id: "telemetry", label: "AI Cost & Telemetry", icon: DollarSign },
  ];

  return (
    <header className="sticky top-0 z-40 w-full bg-[#0f172a]/95 backdrop-blur-md border-b border-slate-800 shadow-2xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Top Status Bar */}
        <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60 text-[11px] text-slate-400">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Live Production Stack
            </span>
            <span className="hidden sm:inline-flex items-center gap-1 text-slate-400">
              <Database className="w-3 h-3 text-emerald-400" />
              Supabase pgvector
            </span>
            <span className="hidden sm:inline-flex items-center gap-1 text-slate-400">
              <Cpu className="w-3 h-3 text-indigo-400" />
              Gemini 3.6 Flash
            </span>
            <span className="hidden sm:inline-flex items-center gap-1 text-slate-400">
              <Zap className="w-3 h-3 text-amber-400" />
              Upstash Redis
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400">Environment:</span>
            <span className="font-semibold text-slate-200 uppercase text-[10px] bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
              Production (Cloud)
            </span>
          </div>
        </div>

        {/* Main Nav Bar */}
        <div className="flex items-center justify-between h-16 gap-4">
          
          {/* Brand Logo */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-lg text-white tracking-tight">
                  TalentAI
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                  Enterprise
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5">Autonomous Talent Intelligence</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                    isActive
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "text-slate-400 hover:text-white hover:bg-slate-800"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Auth Actions */}
          <div className="flex items-center gap-2.5 shrink-0">
            {token ? (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700">
                  <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">
                    A
                  </div>
                  <div className="text-left">
                    <span className="block text-xs font-bold text-slate-200 leading-tight">Admin Recruiter</span>
                    <span className="block text-[10px] text-emerald-400 leading-tight">JWT Bearer Active</span>
                  </div>
                </div>
                <button
                  onClick={onLogout}
                  title="Sign out"
                  className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition border border-transparent hover:border-slate-700"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowAuthModal(true)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 transition active:scale-95"
                >
                  <Key className="w-3.5 h-3.5" />
                  Recruiter Sign In
                </button>
                <button
                  onClick={onSeedAdmin}
                  disabled={isSeeding}
                  className="text-xs font-semibold px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                >
                  {isSeeding ? "Seeding..." : "Bootstrap"}
                </button>
              </div>
            )}
          </div>

        </div>

        {/* Mobile Navigation Row */}
        <div className="lg:hidden flex items-center gap-1 overflow-x-auto pb-3 pt-1 scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                  isActive
                    ? "bg-indigo-600 text-white"
                    : "text-slate-400 hover:text-white bg-slate-900 border border-slate-800"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {item.label}
              </button>
            );
          })}
        </div>

      </div>

      {/* Auth Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200">
          <div className="bg-[#1e293b] border border-slate-700 rounded-3xl w-full max-w-md p-7 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-700/60 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                  <Key className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Recruiter Sign In</h3>
                  <p className="text-xs text-slate-400">Authenticated access for TalentAI</p>
                </div>
              </div>
              <button
                onClick={() => setShowAuthModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ×
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                onLogin(email, password);
                setShowAuthModal(false);
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full bg-[#0f172a] border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full bg-[#0f172a] border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                />
              </div>

              <div className="p-3 bg-indigo-950/40 border border-indigo-800/40 rounded-xl text-[11px] text-indigo-300 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>Pre-seeded demo credentials: <strong>admin@recruit.ai</strong> / <strong>admin_password</strong></span>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAuthModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-6 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition"
                >
                  Sign In & Authorize
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
};
