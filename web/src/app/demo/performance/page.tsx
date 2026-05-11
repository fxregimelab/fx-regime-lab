"use client";

import { motion } from "framer-motion";
import React from "react";

export default function PerformancePage() {
  const containerVars = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } },
  };

  const itemVars = {
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      variants={containerVars}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-8"
    >
      <motion.div variants={itemVars} className="border-b border-white/10 pb-6">
        <h1 className="text-3xl font-light tracking-tight mb-2">
          Track Record
        </h1>
        <p className="text-sm font-mono text-white/50">
          Validated outcomes measured against next-day spot (T+5).
        </p>
      </motion.div>

      <motion.div
        variants={itemVars}
        className="grid grid-cols-1 md:grid-cols-4 gap-4"
      >
        {[
          { label: "Cumulative Return", value: "+14.2%", highlight: true },
          { label: "Win Rate (T+5)", value: "68.4%" },
          { label: "Brier Score", value: "0.142" },
          { label: "Sharpe Ratio", value: "1.84" },
        ].map((stat) => (
          <div
            key={stat.label}
            className={`p-6 rounded-lg border ${stat.highlight ? "border-white/30 bg-white/5" : "border-white/10 bg-white/[0.02]"}`}
          >
            <p className="text-[10px] uppercase font-mono tracking-widest text-white/40 mb-3">
              {stat.label}
            </p>
            <p
              className={`text-3xl font-light ${stat.highlight ? "text-green-400" : "text-white"}`}
            >
              {stat.value}
            </p>
          </div>
        ))}
      </motion.div>

      <motion.div variants={itemVars} className="mt-8">
        <h3 className="text-sm font-mono tracking-widest text-white/50 uppercase mb-4">
          Recent Ledger Entries
        </h3>
        <div className="border border-white/10 rounded-lg overflow-hidden bg-white/[0.02]">
          <table className="w-full text-left font-mono text-sm">
            <thead className="bg-white/[0.03] border-b border-white/10 text-[10px] text-white/40 uppercase tracking-widest">
              <tr>
                <th className="px-6 py-4 font-normal">Date</th>
                <th className="px-6 py-4 font-normal">Pair</th>
                <th className="px-6 py-4 font-normal">Call</th>
                <th className="px-6 py-4 font-normal">Outcome</th>
                <th className="px-6 py-4 font-normal text-right">
                  Return (bps)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {[
                {
                  date: "2026-05-11",
                  pair: "EUR/USD",
                  call: "BULLISH",
                  outcome: "PENDING",
                  ret: "-",
                },
                {
                  date: "2026-05-10",
                  pair: "USD/JPY",
                  call: "BEARISH",
                  outcome: "CORRECT",
                  ret: "+42",
                },
                {
                  date: "2026-05-09",
                  pair: "EUR/USD",
                  call: "BEARISH",
                  outcome: "INCORRECT",
                  ret: "-18",
                },
                {
                  date: "2026-05-08",
                  pair: "USD/INR",
                  call: "NEUTRAL",
                  outcome: "CORRECT",
                  ret: "+5",
                },
                {
                  date: "2026-05-07",
                  pair: "USD/JPY",
                  call: "BULLISH",
                  outcome: "CORRECT",
                  ret: "+68",
                },
              ].map((row, i) => (
                <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-6 py-4 text-white/60">{row.date}</td>
                  <td className="px-6 py-4 text-white">{row.pair}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 rounded text-[10px] ${
                        row.call === "BULLISH"
                          ? "bg-green-500/10 text-green-400"
                          : row.call === "BEARISH"
                            ? "bg-red-500/10 text-red-400"
                            : "bg-white/5 text-white/60"
                      }`}
                    >
                      {row.call}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`text-[10px] tracking-wider ${
                        row.outcome === "CORRECT"
                          ? "text-green-400"
                          : row.outcome === "INCORRECT"
                            ? "text-red-400"
                            : "text-white/40"
                      }`}
                    >
                      {row.outcome}
                    </span>
                  </td>
                  <td
                    className={`px-6 py-4 text-right ${row.ret.startsWith("+") ? "text-green-400" : row.ret.startsWith("-") ? "text-red-400" : "text-white/40"}`}
                  >
                    {row.ret}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  );
}
