"use client";

import React from "react";
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
  Zap
} from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab
}) => {
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
    <header className="sticky top-0 z-40 w-full bg-zinc-950/90 backdrop-blur-md border-b border-zinc-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Micro System Status Header */}
        <div className="flex items-center justify-between py-1 border-b border-zinc-800/60 text-[11px] text-zinc-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-zinc-400 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              All Systems Operational
            </span>
            <span className="hidden sm:inline-flex items-center gap-1 text-zinc-500">
              <Database className="w-3 h-3 text-zinc-400" />
              Supabase pgvector
            </span>
            <span className="hidden sm:inline-flex items-center gap-1 text-zinc-500">
              <Cpu className="w-3 h-3 text-zinc-400" />
              Gemini 3.6 Flash
            </span>
            <span className="hidden sm:inline-flex items-center gap-1 text-zinc-500">
              <Zap className="w-3 h-3 text-zinc-400" />
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
            <div className="w-7 h-7 rounded-md bg-indigo-600 flex items-center justify-center text-white">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-zinc-100 tracking-tight">
                TalentAI
              </span>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
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
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "text-zinc-100 bg-zinc-800"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Live Indicator */}
          <div className="flex items-center gap-2 shrink-0">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-zinc-900 text-zinc-300 border border-zinc-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Admin Mode Active
            </span>
          </div>

        </div>

        {/* Mobile Navigation Row */}
        <div className="md:hidden flex items-center gap-1 overflow-x-auto pb-2.5 pt-1 scrollbar-none border-t border-zinc-800/40">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap transition ${
                  isActive
                    ? "bg-zinc-800 text-zinc-100"
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
