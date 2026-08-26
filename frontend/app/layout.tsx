import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

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
    <html lang="en" className={`${inter.variable} font-sans`}>
      <body className="min-h-screen bg-[#0A0A0A] text-white antialiased selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
