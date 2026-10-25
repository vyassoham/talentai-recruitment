"use client";

import React, { useState, useEffect } from "react";
import { RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import { DEIReport } from "../lib/types";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

interface DEIAnalyticsTabProps {
  activeJobId: string | null;
}

export const DEIAnalyticsTab: React.FC<DEIAnalyticsTabProps> = ({
  activeJobId
}) => {
  const [report, setReport] = useState<DEIReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchDEI = async () => {
    setIsLoading(true);
    try {
      const jobId = activeJobId || "1";
      const data = await api.getDEIAnalytics(jobId, 0.7);
      setReport(data);
    } catch (err) {
      setReport(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDEI();
  }, [activeJobId]);

  const rawDei = report?.dei_analytics || [];

  // Group by gender for Pie Chart (Total Applicants)
  const genderTotals = rawDei.reduce((acc, curr) => {
    const g = curr.gender || "Unknown";
    acc[g] = (acc[g] || 0) + curr.total_applicants;
    return acc;
  }, {} as Record<string, number>);

  const pieData = Object.keys(genderTotals).map((key) => ({
    name: key,
    value: genderTotals[key],
  }));

  // Bar Chart (Pass Rates by Gender/Race)
  const barData = rawDei.map((d) => ({
    name: `${d.gender || "Unknown"}`,
    "Total Applied": d.total_applicants,
    "Passed AI": d.passed_ai,
    "Pass Rate (%)": d.pass_rate_percentage,
  }));

  return (
    <div className="space-y-6">
      <div className="bg-[#121212] border border-zinc-800 shadow-[0_0_15px_rgba(0,0,0,0.5)] rounded-lg p-6 space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800 pb-4">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              DEI Bias Audit & Analytics Dashboard
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Visualize applicant demographics and AI pass rates to ensure fair evaluation.
            </p>
          </div>

          <button
            onClick={fetchDEI}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh Data
          </button>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Pie Chart */}
          <div className="bg-zinc-900/50 p-4 rounded-md border border-zinc-800/50 flex flex-col">
            <h3 className="text-sm font-semibold mb-4 text-center text-zinc-300">Applicant Gender Distribution</h3>
            {pieData.length > 0 ? (
              <div className="h-64 flex-1">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', color: '#fff' }}
                      itemStyle={{ color: '#fff' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-64 justify-center items-center text-zinc-600 text-sm">No Demographic Data Available</div>
            )}
          </div>

          {/* Bar Chart */}
          <div className="bg-zinc-900/50 p-4 rounded-md border border-zinc-800/50 flex flex-col">
            <h3 className="text-sm font-semibold mb-4 text-center text-zinc-300">AI Evaluation Pass Rates</h3>
            {barData.length > 0 ? (
              <div className="h-64 flex-1">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={barData}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis dataKey="name" stroke="#a1a1aa" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#a1a1aa" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', color: '#fff' }}
                      cursor={{fill: '#27272a', opacity: 0.4}}
                    />
                    <Legend wrapperStyle={{ paddingTop: '20px', fontSize: '12px' }} />
                    <Bar dataKey="Total Applied" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Passed AI" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-64 justify-center items-center text-zinc-600 text-sm">No Evaluation Data Available</div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
