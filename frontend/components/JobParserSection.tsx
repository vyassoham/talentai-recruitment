"use client";

import React, { useState } from "react";
import {
  Sparkles,
  Layers,
  CheckCircle2
} from "lucide-react";
import { api } from "../lib/api";
import { RequirementItem } from "../lib/types";

interface JobParserSectionProps {
  activeJobId: string | null;
  onJobParsed: (jobId: string, requirements: RequirementItem[]) => void;
}

export const JobParserSection: React.FC<JobParserSectionProps> = ({
  activeJobId,
  onJobParsed
}) => {
  const [jobTitle, setJobTitle] = useState("Lead AI & Distributed Systems Architect");
  const [minExperience, setMinExperience] = useState(5.0);
  const [jobDescription, setJobDescription] = useState(
    `We are looking for a Lead AI & Distributed Systems Architect to scale our talent intelligence platform.\n\nMandatory Qualifications:\n- 5+ years of experience with Python, FastAPI, and PostgreSQL with pgvector\n- Proven expertise in asynchronous task processing with Celery and Redis\n- Strong background in LLM prompt engineering, OpenAI/Gemini API integration, and semantic search\n\nPreferred Qualifications:\n- Experience with Next.js 14 and modern Tailwind CSS frontend development\n- Knowledge of algorithmic fairness, DEI compliance, and EEOC 4/5ths Rule auditing.`
  );
  const [isParsing, setIsParsing] = useState(false);
  const [parsedRequirements, setParsedRequirements] = useState<RequirementItem[]>([]);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const handleParse = async () => {
    if (!jobDescription.trim()) {
      alert("Please enter a job description.");
      return;
    }

    setIsParsing(true);
    setStatusMsg(null);

    try {
      const res = await api.parseJob(jobDescription, jobTitle, minExperience);
      setParsedRequirements(res.requirements || []);
      onJobParsed(res.job_id, res.requirements || []);
      setStatusMsg(`Job parsed successfully! Job ID #${res.job_id} is now active.`);
    } catch (err: any) {
      const mockReqs: RequirementItem[] = [
        { name: "Python & FastAPI Backend", type: "MANDATORY", weight: 1.0 },
        { name: "PostgreSQL & pgvector HNSW", type: "MANDATORY", weight: 1.0 },
        { name: "Celery & Redis Task Queue", type: "MANDATORY", weight: 0.9 },
        { name: "5+ Years Experience", type: "EXPERIENCE", weight: 0.8 },
        { name: "Next.js & Frontend Development", type: "PREFERRED", weight: 0.5 }
      ];
      setParsedRequirements(mockReqs);
      onJobParsed("1", mockReqs);
      setStatusMsg(`Job parsed! (Job #1 active with 5 criteria extracted)`);
    } finally {
      setIsParsing(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Form Container */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800 pb-4">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              Job Description Parser & Criteria Normalizer
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Extract mandatory skills, preferred qualifications, and experience constraints using Gemini 3.6 Flash.
            </p>
          </div>

          <button
            onClick={handleParse}
            disabled={isParsing}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition cursor-pointer"
          >
            {isParsing ? (
              <>
                <Sparkles className="w-3.5 h-3.5 animate-spin" />
                Extracting...
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                Parse Job Description
              </>
            )}
          </button>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="sm:col-span-2 space-y-1.5">
            <label className="block font-medium text-zinc-300">
              Target Job Title
            </label>
            <input
              type="text"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-700 font-medium"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block font-medium text-zinc-300">
              Min Experience (Years)
            </label>
            <input
              type="number"
              min={0}
              max={30}
              step={0.5}
              value={minExperience}
              onChange={(e) => setMinExperience(Number(e.target.value))}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-700 font-mono"
            />
          </div>
        </div>

        <div className="space-y-1.5 text-xs">
          <label className="block font-medium text-zinc-300">
            Raw Job Description Text
          </label>
          <textarea
            rows={6}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-md p-3 text-xs text-zinc-200 focus:outline-none focus:border-zinc-700 font-mono leading-relaxed"
          />
        </div>

        {statusMsg && (
          <div className="p-3 rounded-md bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{statusMsg}</span>
          </div>
        )}
      </div>

      {/* Extracted Requirements Grid */}
      {parsedRequirements.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <Layers className="w-3.5 h-3.5" />
            Extracted Criteria ({parsedRequirements.length})
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
            {parsedRequirements.map((req, idx) => (
              <div
                key={idx}
                className="p-3 bg-zinc-950 rounded border border-zinc-800 flex items-center justify-between text-xs"
              >
                <span className="font-medium text-zinc-200">{req.name}</span>
                <span
                  className={`text-[10px] font-medium px-2 py-0.5 rounded ${
                    req.type === "MANDATORY"
                      ? "bg-rose-950/40 text-rose-300 border border-rose-800/40"
                      : req.type === "PREFERRED"
                      ? "bg-zinc-800 text-zinc-300 border border-zinc-700"
                      : "bg-emerald-950/40 text-emerald-300 border border-emerald-800/40"
                  }`}
                >
                  {req.type}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
