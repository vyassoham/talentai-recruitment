"use client";

import React, { useState, useEffect } from "react";
import { Wifi, Lock, ShieldAlert, KeyRound, CheckCircle2 } from "lucide-react";

interface NetworkGuardProps {
  children: React.ReactNode;
}

// Strictly authorized Home WiFi Network Subnet
const AUTHORIZED_HOME_IP_PREFIXES = ["49.43.176.", "49.43.", "127.0.0.1", "localhost", "::1"];
const EMERGENCY_OWNER_PASSKEY = "2026"; // Emergency owner unlock passkey

export const NetworkGuard: React.FC<NetworkGuardProps> = ({ children }) => {
  const [isChecking, setIsChecking] = useState(true);
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [clientIp, setClientIp] = useState<string | null>(null);
  const [showPasskeyInput, setShowPasskeyInput] = useState(false);
  const [passkey, setPasskey] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const verifyNetwork = async () => {
      // 1. Check if device has stored authorized passkey
      if (typeof window !== "undefined") {
        const savedAuth = localStorage.getItem("talentai_home_authorized");
        if (savedAuth === "true") {
          setIsAuthorized(true);
          setIsChecking(false);
          return;
        }
      }

      // 2. Fetch current client public IP
      try {
        const res = await fetch("https://api.ipify.org?format=json", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          const ip = data.ip;
          setClientIp(ip);

          // Check if IP belongs to authorized home WiFi ISP subnet
          const matchesHomeNetwork = AUTHORIZED_HOME_IP_PREFIXES.some((prefix) =>
            ip.startsWith(prefix)
          );

          if (matchesHomeNetwork) {
            setIsAuthorized(true);
            if (typeof window !== "undefined") {
              localStorage.setItem("talentai_home_authorized", "true");
            }
          } else {
            setIsAuthorized(false);
          }
        } else {
          setIsAuthorized(false);
        }
      } catch (err) {
        setIsAuthorized(false);
      } finally {
        setIsChecking(false);
      }
    };

    verifyNetwork();
  }, []);

  const handlePasskeySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (passkey === EMERGENCY_OWNER_PASSKEY) {
      setIsAuthorized(true);
      if (typeof window !== "undefined") {
        localStorage.setItem("talentai_home_authorized", "true");
      }
      setErrorMsg(null);
    } else {
      setErrorMsg("Incorrect owner passkey. Access denied.");
    }
  };

  // While verifying network
  if (isChecking) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center text-zinc-400 text-xs gap-3 font-mono">
        <Wifi className="w-5 h-5 animate-pulse text-indigo-400" />
        <span>Authenticating Home WiFi Network Security Token...</span>
      </div>
    );
  }

  // If connected to Home WiFi or passkey authorized
  if (isAuthorized) {
    return <>{children}</>;
  }

  // Locked Screen for unauthorized visitors outside Home WiFi
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center p-4 antialiased">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-md p-8 shadow-2xl space-y-6 text-center">
        
        <div className="w-12 h-12 rounded-full bg-rose-950/50 border border-rose-900/50 text-rose-400 flex items-center justify-center mx-auto">
          <Lock className="w-6 h-6" />
        </div>

        <div className="space-y-2">
          <h2 className="text-base font-semibold text-zinc-100">
            Private Home Network Restricted
          </h2>
          <p className="text-xs text-zinc-400 leading-relaxed max-w-sm mx-auto">
            This workspace is strictly locked to devices connected to the owner's <strong className="text-zinc-200">Home WiFi Network</strong>.
          </p>
        </div>

        <div className="p-3.5 bg-zinc-950 rounded-lg border border-zinc-800 text-[11px] text-zinc-400 font-mono text-left space-y-1.5">
          <div className="flex justify-between">
            <span>Your Network IP:</span>
            <span className="text-zinc-200">{clientIp || "Unknown External"}</span>
          </div>
          <div className="flex justify-between">
            <span>Authorized Network:</span>
            <span className="text-zinc-400">49.43.176.x (Home WiFi)</span>
          </div>
          <div className="flex justify-between border-t border-zinc-900 pt-1">
            <span>Access Firewall:</span>
            <span className="text-rose-400 font-semibold">BLOCKED 🔒</span>
          </div>
        </div>

        {/* Emergency Passkey Form */}
        {!showPasskeyInput ? (
          <button
            type="button"
            onClick={() => setShowPasskeyInput(true)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition underline underline-offset-4"
          >
            I am the owner (Unlock with Passkey)
          </button>
        ) : (
          <form onSubmit={handlePasskeySubmit} className="space-y-3 pt-1">
            <div>
              <input
                type="password"
                value={passkey}
                onChange={(e) => setPasskey(e.target.value)}
                placeholder="Enter 4-digit Passkey"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 text-center font-mono focus:outline-none focus:border-zinc-700"
              />
            </div>

            {errorMsg && (
              <p className="text-[11px] text-rose-400">{errorMsg}</p>
            )}

            <button
              type="submit"
              className="w-full py-2 px-3 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition cursor-pointer"
            >
              Verify & Unlock Device
            </button>
          </form>
        )}

      </div>
    </div>
  );
};
