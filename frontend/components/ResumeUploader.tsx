"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Trash2,
  ShieldCheck
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
      
      {/* Upload Container */}
      <div className="bg-white/5 border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)] rounded-lg p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-zinc-100">
                Resume & CV Ingestion Pipeline
              </h2>
              <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                ClamAV Active
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">
              Automated PDF text extraction, SHA-256 deduplication, stream compression, and vector embedding.
            </p>
          </div>

          <span className="text-xs text-zinc-500">Max 10MB per file • PDF, DOCX</span>
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
          className={`rounded-lg border border-dashed p-8 text-center cursor-pointer transition-colors ${
            isDragging
              ? "border-indigo-500 bg-zinc-800/50"
              : "border-zinc-700 hover:border-zinc-600 bg-transparent/40 hover:bg-transparent"
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

          <div className="w-10 h-10 rounded-md bg-zinc-800 text-zinc-400 flex items-center justify-center mx-auto mb-3 border border-zinc-700">
            <UploadCloud className="w-5 h-5" />
          </div>

          <h3 className="text-sm font-medium text-zinc-200 mb-0.5">
            Click to upload or drag and drop
          </h3>
          <p className="text-xs text-zinc-500 max-w-sm mx-auto">
            Select single or batch PDF/DOCX resumes for background parsing
          </p>
        </div>
      </div>

      {/* Uploaded Files Table */}
      {files.length > 0 && (
        <div className="bg-white/5 border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)] rounded-lg overflow-hidden">
          <div className="p-4 border-b border-white/10">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Active Ingestion Tasks ({files.length})
            </h3>
          </div>

          <div className="divide-y divide-zinc-800">
            {files.map((item) => (
              <div
                key={item.id}
                className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-zinc-400 shrink-0" />
                  <div>
                    <span className="font-medium text-zinc-200 block">{item.file.name}</span>
                    <span className="text-[11px] text-zinc-500 font-mono">
                      {(item.file.size / (1024 * 1024)).toFixed(2)} MB
                      {item.candidateName && (
                        <span className="text-zinc-400 ml-2">• Candidate: {item.candidateName}</span>
                      )}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {item.status === "COMPLETED" && (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-950/40 text-emerald-300 border border-emerald-800/40">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Indexed
                    </span>
                  )}
                  {item.status === "FAILED" && (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-rose-950/40 text-rose-300 border border-rose-800/40">
                      <AlertCircle className="w-3.5 h-3.5" />
                      {item.error || "Failed"}
                    </span>
                  )}
                  {(item.status === "UPLOADING" ||
                    item.status === "QUEUED" ||
                    item.status === "PROCESSING") && (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      {item.status}...
                    </span>
                  )}

                  <button
                    onClick={() => removeFile(item.id)}
                    className="p-1 rounded text-zinc-500 hover:text-zinc-300 transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
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
