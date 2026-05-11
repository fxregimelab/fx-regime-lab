"use client";

import { AnimatePresence, motion } from "framer-motion";
import React, { useState } from "react";

const MOCK_PAIRS = [
  {
    id: "eurusd",
    symbol: "EUR/USD",
    spot: 1.0924,
    chg: 0.12,
    regime: "BULLISH",
    conf: 84,
    rvol: 6.2,
    trend: [1.08, 1.085, 1.09, 1.088, 1.0924],
  },
  {
    id: "usdjpy",
    symbol: "USD/JPY",
    spot: 151.2,
    chg: -0.45,
    regime: "BEARISH",
    conf: 92,
    rvol: 8.5,
    trend: [153.2, 152.8, 152.0, 151.5, 151.2],
  },
  {
    id: "usdinr",
    symbol: "USD/INR",
    spot: 83.42,
    chg: 0.05,
    regime: "NEUTRAL",
    conf: 45,
    rvol: 2.1,
    trend: [83.3, 83.35, 83.4, 83.45, 83.42],
  },
];

export default function TerminalPage() {
  const [selectedPair, setSelectedPair] = useState(MOCK_PAIRS[0].id);
  const pair = MOCK_PAIRS.find((p) => p.id === selectedPair)!;

  return (
    <div className="flex flex-col gap-6">
      {/* Top Status Bar */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-4 gap-4"
      >
        {[
          {
            label: "System Status",
            value: "OPERATIONAL",
            color: "text-green-400",
          },
          { label: "Data Quality", value: "0.98", color: "text-white" },
          { label: "Market Stress", value: "LOW", color: "text-green-400" },
          { label: "Last Update", value: "Just now", color: "text-white/70" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="p-4 border border-white/10 bg-white/[0.02] rounded-lg"
          >
            <p className="text-[10px] uppercase font-mono tracking-widest text-white/40 mb-2">
              {stat.label}
            </p>
            <p className={`font-mono text-sm ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Pair List */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex flex-col gap-4"
        >
          {MOCK_PAIRS.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedPair(p.id)}
              className={`p-5 rounded-lg border text-left transition-all duration-300 ${
                selectedPair === p.id
                  ? "border-white/40 bg-white/10 shadow-[0_0_30px_rgba(255,255,255,0.05)]"
                  : "border-white/10 bg-white/[0.02] hover:bg-white/[0.04]"
              }`}
            >
              <div className="flex justify-between items-baseline mb-2">
                <span className="font-mono text-lg font-medium">
                  {p.symbol}
                </span>
                <span
                  className={`font-mono text-xs ${p.chg >= 0 ? "text-green-400" : "text-red-400"}`}
                >
                  {p.chg > 0 ? "+" : ""}
                  {p.chg}%
                </span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-3xl font-light tabular-nums">
                  {p.spot.toFixed(p.id === "usdjpy" ? 2 : 4)}
                </span>
                <span
                  className={`text-xs font-mono px-2 py-1 rounded ${
                    p.regime === "BULLISH"
                      ? "bg-green-500/20 text-green-400"
                      : p.regime === "BEARISH"
                        ? "bg-red-500/20 text-red-400"
                        : "bg-white/10 text-white/70"
                  }`}
                >
                  {p.regime}
                </span>
              </div>
            </button>
          ))}
        </motion.div>

        {/* Middle & Right: Detailed View */}
        <motion.div
          key={selectedPair}
          initial={{ opacity: 0, filter: "blur(10px)" }}
          animate={{ opacity: 1, filter: "blur(0px)" }}
          transition={{ duration: 0.3 }}
          className="lg:col-span-2 flex flex-col gap-6"
        >
          {/* Chart Area */}
          <div className="p-6 rounded-lg border border-white/10 bg-white/[0.02] h-64 flex flex-col relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10 text-9xl font-bold font-mono -mt-6 -mr-4 pointer-events-none">
              {pair.symbol.split("/")[0]}
            </div>
            <h3 className="text-sm text-white/50 font-mono tracking-widest uppercase mb-4">
              Spot Trajectory (5D)
            </h3>
            <div className="flex-1 flex items-end justify-between gap-2">
              {pair.trend.map((val, i) => {
                const min = Math.min(...pair.trend);
                const max = Math.max(...pair.trend);
                const height =
                  max === min ? 50 : 20 + ((val - min) / (max - min)) * 80;
                return (
                  <motion.div
                    key={i}
                    initial={{ height: 0 }}
                    animate={{ height: `${height}%` }}
                    transition={{ delay: i * 0.1, type: "spring" }}
                    className="w-full bg-gradient-to-t from-white/5 to-white/20 rounded-t relative group"
                  >
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 font-mono text-[10px] text-white/70 transition-opacity">
                      {val}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Data Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-5 rounded-lg border border-white/10 bg-white/[0.02]">
              <p className="text-[10px] uppercase font-mono tracking-widest text-white/40 mb-3">
                Model Confidence
              </p>
              <div className="flex items-end gap-3 mb-2">
                <span className="text-4xl font-light">{pair.conf}%</span>
              </div>
              <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden mt-4">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pair.conf}%` }}
                  className={`h-full ${pair.conf > 80 ? "bg-green-400" : pair.conf > 50 ? "bg-yellow-400" : "bg-white/40"}`}
                />
              </div>
            </div>

            <div className="p-5 rounded-lg border border-white/10 bg-white/[0.02]">
              <p className="text-[10px] uppercase font-mono tracking-widest text-white/40 mb-3">
                Realized Vol (20D)
              </p>
              <div className="flex items-end gap-3">
                <span className="text-4xl font-light">{pair.rvol}%</span>
                <span className="text-sm font-mono text-white/50 mb-1">
                  annualized
                </span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
