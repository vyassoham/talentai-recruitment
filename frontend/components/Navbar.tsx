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
      <div className="w-full px-3 sm:px-5 lg:px-8">
        
        {/* Micro System Status Header */}
        <div className="flex items-center justify-between py-1 border-b border-white/5 text-[11px] text-zinc-500">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-zinc-300 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>
              All Systems Operational
            </span>
            <span className="hidden lg:inline-flex items-center gap-1 text-zinc-400">
              <Database className="w-3 h-3 text-zinc-500" />
              Supabase pgvector
            </span>
            <span className="hidden lg:inline-flex items-center gap-1 text-zinc-400">
              <Cpu className="w-3 h-3 text-zinc-500" />
              Gemini 3.6 Flash
            </span>
            <span className="hidden lg:inline-flex items-center gap-1 text-zinc-400">
              <Zap className="w-3 h-3 text-zinc-500" />
              Upstash Redis
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-zinc-500 hidden sm:inline">Cloud Region:</span>
            <span className="font-mono text-zinc-400 text-[10px]">AWS ap-south-1</span>
          </div>
        </div>

        {/* Main Navigation Bar */}
        <div className="flex items-center justify-between h-13 gap-2 py-2">
          
          {/* Brand */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-[0_0_15px_rgba(99,102,241,0.4)]">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-sm text-white tracking-tight">
                TalentAI
              </span>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-white/5 text-zinc-300 border border-white/10 hidden sm:inline">
                Workspace
              </span>
            </div>
          </div>

          {/* Navigation Links — scrollable on small desktops */}
          <nav className="flex items-center gap-0.5 overflow-x-auto scrollbar-none flex-1 mx-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[11px] font-medium transition-all duration-200 whitespace-nowrap shrink-0 ${
                    isActive
                      ? "text-white bg-white/10 border border-white/10"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Live Indicator & Count */}
          <div className="flex items-center gap-2 shrink-0">
            {dbCount !== null && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 whitespace-nowrap">
                <Users className="w-3.5 h-3.5" />
                {dbCount.toLocaleString()}
              </span>
            )}
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 whitespace-nowrap">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Admin
            </span>
          </div>

        </div>

      </div>
    </header>
  );
};
