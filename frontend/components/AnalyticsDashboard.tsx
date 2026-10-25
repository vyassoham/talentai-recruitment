"use client";

import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { DEIReport, AICostReport } from "../lib/types";
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

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8"];

export default function AnalyticsDashboard() {
  const [deiData, setDeiData] = useState<DEIReport | null>(null);
  const [aiCostData, setAiCostData] = useState<AICostReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [dei, costs] = await Promise.all([
          api.getDEIAnalytics(),
          api.getAICostAnalytics(),
        ]);
        setDeiData(dei);
        setAiCostData(costs);
      } catch (err) {
        console.error("Failed to fetch analytics:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64 text-slate-400">
        Loading Analytics...
      </div>
    );
  }

  // Process DEI Data for Charts
  const rawDei = deiData?.dei_analytics || [];
  
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

  // Bar Chart (Pass Rates by Gender)
  const barData = rawDei.map((d) => ({
    name: d.gender || "Unknown",
    "Total Applied": d.total_applicants,
    "Passed AI": d.passed_ai,
    "Pass Rate (%)": d.pass_rate_percentage,
  }));

  return (
    <div className="space-y-8 p-6 bg-slate-900 text-slate-200 rounded-lg shadow-xl border border-slate-700">
      
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">DEI & Telemetry Dashboard</h2>
        <p className="text-slate-400">
          Monitor Diversity, Equity, and Inclusion (DEI) metrics and AI pipeline performance.
        </p>
      </div>

      {/* Grid for Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Pie Chart: Gender Distribution */}
        <div className="bg-slate-800 p-4 rounded-md border border-slate-700">
          <h3 className="text-lg font-semibold mb-4 text-center">Applicant Gender Distribution</h3>
          {pieData.length > 0 ? (
            <div className="h-64">
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
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', color: '#fff' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-64 justify-center items-center text-slate-500">No Data Available</div>
          )}
        </div>

        {/* Bar Chart: AI Pass Rates */}
        <div className="bg-slate-800 p-4 rounded-md border border-slate-700">
          <h3 className="text-lg font-semibold mb-4 text-center">AI Evaluation Pass Rates</h3>
          {barData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={barData}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', color: '#fff' }}
                  />
                  <Legend />
                  <Bar dataKey="Total Applied" fill="#3b82f6" />
                  <Bar dataKey="Passed AI" fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-64 justify-center items-center text-slate-500">No Data Available</div>
          )}
        </div>
      </div>

      {/* Telemetry / AI Costs Table */}
      <div className="bg-slate-800 p-6 rounded-md border border-slate-700 mt-8">
        <h3 className="text-lg font-semibold mb-4 border-b border-slate-700 pb-2">
          AI Telemetry & Token Usage
        </h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-900 p-3 rounded-md text-center">
            <div className="text-sm text-slate-400">Total API Calls</div>
            <div className="text-xl font-bold text-blue-400">{aiCostData?.total_ai_transactions || 0}</div>
          </div>
          <div className="bg-slate-900 p-3 rounded-md text-center">
            <div className="text-sm text-slate-400">Total Tokens</div>
            <div className="text-xl font-bold text-yellow-400">{aiCostData?.total_tokens_consumed || 0}</div>
          </div>
          <div className="bg-slate-900 p-3 rounded-md text-center">
            <div className="text-sm text-slate-400">Est. USD Cost</div>
            <div className="text-xl font-bold text-emerald-400">${(aiCostData?.total_estimated_cost_usd || 0).toFixed(4)}</div>
          </div>
        </div>

        {aiCostData?.operations && aiCostData.operations.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-left text-slate-300">
              <thead className="text-xs text-slate-400 uppercase bg-slate-900">
                <tr>
                  <th className="px-4 py-3">Operation</th>
                  <th className="px-4 py-3">Calls</th>
                  <th className="px-4 py-3">Avg Latency (s)</th>
                  <th className="px-4 py-3">Cost (USD)</th>
                </tr>
              </thead>
              <tbody>
                {aiCostData.operations.map((op, idx) => (
                  <tr key={idx} className="border-b border-slate-700 hover:bg-slate-700/50">
                    <td className="px-4 py-3 font-medium text-white">{op.operation}</td>
                    <td className="px-4 py-3">{op.transaction_count}</td>
                    <td className="px-4 py-3">{op.avg_latency_sec.toFixed(2)}s</td>
                    <td className="px-4 py-3">${op.estimated_cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
