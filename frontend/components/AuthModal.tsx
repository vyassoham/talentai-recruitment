"use client";

import React, { useState } from "react";
import { Key, ShieldCheck, AlertCircle, X, Sparkles } from "lucide-react";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLogin: (email: string, pass: string) => Promise<void>;
  onSeedAdmin: () => Promise<void>;
  isSeeding: boolean;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onLogin,
  onSeedAdmin,
  isSeeding
}) => {
  const [email, setEmail] = useState("admin@recruit.ai");
  const [password, setPassword] = useState("admin_password");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    try {
      await onLogin(email, password);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Invalid credentials. Try 1-Click Bootstrap.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickSignIn = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      await onLogin("admin@recruit.ai", "admin_password");
      onClose();
    } catch (err: any) {
      // If user doesn't exist yet, seed and then login
      try {
        await onSeedAdmin();
        onClose();
      } catch (seedErr: any) {
        setErrorMsg(seedErr.message || "Failed to sign in. Please check backend connection.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-150">
      <div className="bg-white/5 border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)] rounded-lg w-full max-w-sm p-6 shadow-2xl space-y-4 my-auto relative">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md bg-indigo-600 flex items-center justify-center text-white">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-zinc-100">Recruiter Authentication</h3>
              <p className="text-[11px] text-zinc-400">Sign in to access admin endpoints</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 1-Click Quick Action */}
        <button
          type="button"
          onClick={handleQuickSignIn}
          disabled={isLoading || isSeeding}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5" />
          {isLoading || isSeeding ? "Authenticating..." : "1-Click Auto Sign In (Admin)"}
        </button>

        <div className="flex items-center gap-2 text-[10px] text-zinc-500 uppercase tracking-wider">
          <div className="h-px bg-zinc-800 flex-1"></div>
          <span>Or sign in manually</span>
          <div className="h-px bg-zinc-800 flex-1"></div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          {errorMsg && (
            <div className="p-2.5 rounded bg-rose-950/40 border border-rose-800/40 text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-black/20 border border-white/5 backdrop-blur-sm shadow-inner rounded-md px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-zinc-700 transition font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full bg-black/20 border border-white/5 backdrop-blur-sm shadow-inner rounded-md px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-zinc-700 transition font-mono"
            />
          </div>

          <div className="p-2 bg-transparent rounded border border-white/10/80 text-[11px] text-zinc-400">
            Credentials: <span className="text-zinc-200 font-mono">admin@recruit.ai</span> / <span className="text-zinc-200 font-mono">admin_password</span>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-1.5 rounded-md text-xs font-medium bg-zinc-100 text-zinc-900 hover:bg-white transition"
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
