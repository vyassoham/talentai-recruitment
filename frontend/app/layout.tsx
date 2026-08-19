import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TalentAI Enterprise — Next-Gen AI Recruitment Platform",
  description: "Enterprise candidate matching, deterministic eligibility, deep AI reranking, and DEI compliance platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
