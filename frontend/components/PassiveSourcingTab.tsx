"use client";

import React, { useState } from "react";
import {
  Globe,
  Search,
  CheckCircle2,
  ExternalLink,
  Code,
  Sparkles
} from "lucide-react";
import { api } from "../lib/api";
import { PassiveCandidate } from "../lib/types";

export const PassiveSourcingTab: React.FC = () => {
  const [platform, setPlatform] = useState<"github" | "stackoverflow">("github");
  const [language, setLanguage] = useState("python");
  const [location, setLocation] = useState("mumbai");
  const [minRepos, setMinRepos] = useState(5);
  const [tags, setTags] = useState("fastapi, pgvector, postgresql");

  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<PassiveCandidate[]>([]);
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);

  const handleSearch = async () => {
    setIsLoading(true);
    setIngestMsg(null);
    try {
      if (platform === "github") {
        const data = await api.searchGitHubSourcing(language, location, minRepos, 10);
        setResults(data);
      } else {
        const tagList = tags.split(",").map((t) => t.trim());
        const data = await api.searchStackOverflowSourcing(tagList, 500, 10);
        setResults(data);
      }
    } catch (err: any) { setResults([]); alert('Sourcing failed or endpoint not implemented on backend.'); } finally {
      setIsLoading(false);
    }
  };

  const handleIngest = async () => {
    if (results.length === 0) return;
    setIsIngesting(true);
    try {
      const res = await api.ingestDiscoveredCandidates(results);
      setIngestMsg(`Ingested ${res.created} candidate profiles into Supabase. (${res.skipped_duplicates} duplicates skipped)`);
    } catch (err: any) { setResults([]); alert('Sourcing failed or endpoint not implemented on backend.'); } finally {
      setIsIngesting(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Sourcing Form Container */}
      <div className="bg-white/5 border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)] rounded-lg p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              Passive Talent Sourcing & Web Discovery
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Scan engineering platforms to discover, evaluate, and auto-ingest candidate profiles.
            </p>
          </div>

          {/* Platform Toggle */}
          <div className="flex items-center gap-1 bg-transparent p-1 rounded-md border border-white/10">
            <button
              onClick={() => setPlatform("github")}
              className={`px-3 py-1 rounded text-xs font-medium transition ${
                platform === "github"
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              GitHub Developers
            </button>
            <button
              onClick={() => setPlatform("stackoverflow")}
              className={`px-3 py-1 rounded text-xs font-medium transition ${
                platform === "stackoverflow"
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              StackOverflow Experts
            </button>
          </div>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          {platform === "github" ? (
            <>
              <div className="space-y-1.5">
                <label className="block font-medium text-zinc-300">
                  Primary Language
                </label>
                <input
                  type="text"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full bg-black/20 border border-white/5 backdrop-blur-sm shadow-inner rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-700"
                />
              </div>

              <div className="space-y-1.5">
                <label className="block font-medium text-zinc-300">
                  Location / City
                </label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="w-full bg-black/20 border border-white/5 backdrop-blur-sm shadow-inner rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-700"
                />
              </div>

              <div className="space-y-1.5">
                <label className="block font-medium text-zinc-300">
                  Min Repositories
                </label>
                <input
                  type="number"
                  min={1}
                  value={minRepos}
                  onChange={(e) => setMinRepos(Number(e.target.value))}
                  className="w-full bg-black/20 border border-white/5 backdrop-blur-sm shadow-inner rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-700 font-mono"
                />
              </div>
            </>
          ) : (
            <div className="sm:col-span-3 space-y-1.5">
              <label className="block font-medium text-zinc-300">
                Technology Tags (Comma Separated)
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="w-full bg-black/20 border border-white/5 backdrop-blur-sm shadow-inner rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-700"
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-zinc-500">GitHub PAT Authenticated • 5,000 req/hr</span>
          <button
            onClick={handleSearch}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition cursor-pointer"
          >
            {isLoading ? (
              <>
                <Sparkles className="w-3.5 h-3.5 animate-spin" />
                Scanning API...
              </>
            ) : (
              <>
                <Search className="w-3.5 h-3.5" />
                Discover Candidates
              </>
            )}
          </button>
        </div>

        {ingestMsg && (
          <div className="p-3 rounded-md bg-black/20 border border-white/5 backdrop-blur-sm shadow-inner text-zinc-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{ingestMsg}</span>
          </div>
        )}
      </div>

      {/* Discovered Candidates Grid */}
      {results.length > 0 && (
        <div className="bg-white/5 border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)] rounded-lg p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Discovered Profiles ({results.length})
            </h3>

            <button
              onClick={handleIngest}
              disabled={isIngesting}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              {isIngesting ? "Ingesting..." : "Ingest All to Database"}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {results.map((c, idx) => (
              <div
                key={idx}
                className="p-4 bg-transparent rounded border border-white/10 space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-zinc-100 block text-sm">{c.name}</span>
                    {c.location && <span className="text-zinc-500 text-[11px]">{c.location}</span>}
                  </div>

                  {c.github_url && (
                    <a
                      href={c.github_url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1 rounded text-zinc-400 hover:text-zinc-100 transition"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>

                {c.bio && (
                  <p className="text-zinc-400 line-clamp-2 italic text-[11px]">
                    "{c.bio}"
                  </p>
                )}

                <div className="flex items-center gap-3 pt-2 border-t border-zinc-900 text-[11px] text-zinc-400">
                  {c.public_repos !== undefined && (
                    <span>{c.public_repos} Repos</span>
                  )}
                  {c.followers !== undefined && (
                    <span>{c.followers} Followers</span>
                  )}
                  <span className="text-zinc-300 font-medium">
                    {c.primary_language || "Developer"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};

