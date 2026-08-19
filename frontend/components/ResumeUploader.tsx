"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Shield,
  Trash2,
  Clock,
  Sparkles,
  ShieldCheck,
  Zap,
  ArrowRight
} from "lucide-react";
import { api } from "../lib/api";

interface UploadedFileState {
  id: string;
  file: File;
  jobId: string | null;
  status: "UPLOADING" | "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
  candidateId?: number;
  candidateName?: string;
  error?: string;
}

export const ResumeUploader: React.FC = () => {
  const [files, setFiles] = useState<UploadedFileState[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (newFiles: FileList | File[]) => {
    const fileList = Array.from(newFiles);
    
    for (const file of fileList) {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (ext !== "pdf" && ext !== "docx") {
        alert(`Unsupported file format .${ext}. Only PDF and DOCX files are permitted.`);
        continue;
      }

      if (file.size > 10 * 1024 * 1024) {
        alert(`File ${file.name} exceeds the 10MB size limit.`);
        continue;
      }

      const tempId = Math.random().toString(36).substring(7);
      const newEntry: UploadedFileState = {
        id: tempId,
        file,
        jobId: null,
        status: "UPLOADING",
      };

      setFiles((prev) => [newEntry, ...prev]);

      try {
        const res = await api.uploadCV(file);
        setFiles((prev) =>
          prev.map((f) =>
            f.id === tempId
              ? { ...f, jobId: res.job_id, status: res.status as any }
              : f
          )
        );
        pollJobStatus(tempId, res.job_id);
      } catch (err: any) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === tempId
              ? { ...f, status: "FAILED", error: err.message || "Upload failed" }
              : f
          )
        );
      }
    }
  };

  const pollJobStatus = async (tempId: string, jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await api.getUploadJobStatus(jobId);
        if (res.status === "COMPLETED" || res.status === "FAILED") {
          clearInterval(interval);
          setFiles((prev) =>
            prev.map((f) =>
              f.id === tempId
                ? {
                    ...f,
                    status: res.status as any,
                    candidateId: res.candidate_id,
                    candidateName: res.candidate_name,
                    error: res.error_message,
                  }
                : f
            )
          );
        } else {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === tempId ? { ...f, status: res.status as any } : f
            )
          );
        }
      } catch (err) {
        clearInterval(interval);
      }
    }, 2000);
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <div className="space-y-6">
      
      {/* Header Info */}
      <div className="bg-[#1e293b]/90 border border-slate-700/80 rounded-3xl p-6 sm:p-8 shadow-xl backdrop-blur-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-700/60 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 font-bold text-xs border border-emerald-500/30 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                ClamAV Antivirus Shield Active
              </span>
              <span className="text-xs text-slate-400">PDF & DOCX Multi-Upload</span>
            </div>
            <h2 className="text-2xl font-black text-white tracking-tight">
              CV & Resume Ingestion Pipeline
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Asynchronous resume extraction with PDF text extraction, SHA-256 deduplication, Gemini 3.6 entity parsing, and 1536-d vector embedding generation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 font-medium">Max 10MB / file</span>
          </div>
        </div>

        {/* Drag and Drop Zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files) {
              handleFiles(e.dataTransfer.files);
            }
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`mt-6 rounded-3xl border-2 border-dashed p-10 text-center cursor-pointer transition-all duration-200 ${
            isDragging
              ? "border-indigo-500 bg-indigo-500/10 scale-[1.01]"
              : "border-slate-700 hover:border-indigo-500/80 bg-[#0f172a]/60 hover:bg-[#0f172a]"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files);
            }}
            multiple
            accept=".pdf,.docx"
            className="hidden"
          />

          <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto mb-4 border border-indigo-500/30 shadow-lg shadow-indigo-500/20">
            <UploadCloud className="w-8 h-8" />
          </div>

          <h3 className="text-base font-bold text-white mb-1">
            Drag & Drop CV Files or Browse Device
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Upload candidate resumes in PDF or DOCX format for automated background parsing and semantic indexing.
          </p>
        </div>
      </div>

      {/* Uploaded Files Tracker */}
      {files.length > 0 && (
        <div className="bg-[#1e293b]/90 border border-slate-700/80 rounded-3xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Active Ingestion Tasks ({files.length})
          </h3>

          <div className="space-y-3">
            {files.map((item) => (
              <div
                key={item.id}
                className="p-4 bg-[#0f172a] rounded-2xl border border-slate-700/70 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center shrink-0 border border-slate-700">
                    <FileText className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white">
                      {item.file.name}
                    </h4>
                    <p className="text-[11px] text-slate-400">
                      {(item.file.size / (1024 * 1024)).toFixed(2)} MB
                      {item.candidateName && (
                        <span className="ml-2 font-bold text-emerald-400">
                          • Candidate: {item.candidateName}
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {item.status === "COMPLETED" && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      <CheckCircle2 className="w-4 h-4" />
                      Indexed & Saved
                    </span>
                  )}
                  {item.status === "FAILED" && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                      <AlertCircle className="w-4 h-4" />
                      {item.error || "Failed"}
                    </span>
                  )}
                  {(item.status === "UPLOADING" ||
                    item.status === "QUEUED" ||
                    item.status === "PROCESSING") && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      {item.status}...
                    </span>
                  )}

                  <button
                    onClick={() => removeFile(item.id)}
                    className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
