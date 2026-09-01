"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Layers,
  FileText,
  Search,
  Globe,
  RefreshCw,
  BarChart3,
  DollarSign,
  Database,
  Cpu,
  Zap,
  Users
} from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab
}) => {
  const [dbCount, setDbCount] = useState<number | null>(null);

  useEffect(() => {
    const fetchCount = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://talentai-recruitment.onrender.com/api/v1";
        const res = await fetch(`${apiUrl}/candidates/count`);
        const data = await res.json();
        if (data && data.total_amount !== undefined) {
          setDbCount(data.total_amount);
        }
      } catch (err) {}
    };
    fetchCount();
    const interval = setInterval(fetchCount, 5000);
    return () => clearInterval(interval);
  }, []);
  const navItems = [
    { id: "match", label: "Match & Search", icon: Search },
    { id: "ingestion", label: "CV Ingestion", icon: FileText },
    { id: "jobs", label: "Job Requirements", icon: Layers },
    { id: "sourcing", label: "Passive Sourcing", icon: Globe },
    { id: "staleness", label: "Profile Refresh", icon: RefreshCw },
    { id: "dei", label: "DEI & Compliance", icon: BarChart3 },
    { id: "telemetry", label: "AI Telemetry", icon: DollarSign },
  ];

  return (
    <header className="sticky top-0 z-40 w-full bg-[#0A0A0A]/70 backdrop-blur-xl border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Micro System Status Header */}
        <div className="flex items-center justify-between py-1 border-b border-white/5 text-[11px] text-zinc-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-zinc-300 font-medium drop-shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>
              All Systems Operational
            </span>
            <span className="hidden sm:inline-flex items-center gap-1 text-zinc-400">
              <Database className="w-3 h-3 text-zinc-500" />
              Supabase pgvector
            </span>
            <span className="hidden sm:inline-flex items-center gap-1 text-zinc-400">
              <Cpu className="w-3 h-3 text-zinc-500" />
              Gemini 3.6 Flash
            </span>
            <span className="hidden sm:inline-flex items-center gap-1 text-zinc-400">
              <Zap className="w-3 h-3 text-zinc-500" />
              Upstash Redis
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-zinc-500">Cloud Region:</span>
            <span className="font-mono text-zinc-400 text-[10px]">AWS ap-south-1</span>
          </div>
        </div>

        {/* Main Navigation Bar */}
        <div className="flex items-center justify-between h-14 gap-4">
          
          {/* Brand */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-[0_0_15px_rgba(99,102,241,0.4)]">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-white tracking-tight drop-shadow-sm">
                TalentAI
              </span>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-white/5 text-zinc-300 border border-white/10 backdrop-blur-sm">
                Personal Workspace
              </span>
            </div>
          </div>

          {/* Unboxed Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-300 ${
                    isActive
                      ? "text-white bg-white/10 shadow-[0_0_10px_rgba(255,255,255,0.02)] border border-white/5"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Live Indicator & Count */}
          <div className="flex items-center gap-3 shrink-0">
            {dbCount !== null && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.15)]">
                <Users className="w-3.5 h-3.5" />
                {dbCount.toLocaleString()} Candidates
              </span>
            )}
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 shadow-[0_0_12px_rgba(16,185,129,0.1)]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>
              Admin Mode
            </span>
          </div>

        </div>

        {/* Mobile Navigation Row */}
        <div className="md:hidden flex items-center gap-1 overflow-x-auto pb-2.5 pt-1 scrollbar-none border-t border-white/5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap transition-all ${
                  isActive
                    ? "bg-white/10 text-white border border-white/5"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Icon className="w-3 h-3" />
                {item.label}
              </button>
            );
          })}
        </div>

      </div>
    </header>
  );
};
