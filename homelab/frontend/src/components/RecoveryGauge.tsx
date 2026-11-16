import React from "react";
import { Activity, Heart, Moon, Sparkles, Thermometer, TrendingUp } from "lucide-react";
import { RecoveryMetric } from "../types";

interface RecoveryGaugeProps {
  recovery?: RecoveryMetric;
}

export const RecoveryGauge: React.FC<RecoveryGaugeProps> = ({ recovery }) => {
  if (!recovery) {
    return (
      <div className="glass-card rounded-2xl p-6 flex flex-col items-center justify-center min-h-[340px] text-center relative overflow-hidden">
        <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-3 shadow-inner">
          <Activity className="w-8 h-8 text-noop-subtle animate-pulse" />
        </div>
        <h3 className="text-base font-semibold text-white">No Recovery Data Yet</h3>
        <p className="text-xs text-noop-subtle mt-1.5 max-w-xs leading-relaxed">
          Wear your WHOOP strap through the night to compute your baseline recovery and HRV readiness score.
        </p>
      </div>
    );
  }

  const score = Math.round(recovery.recovery_score);
  const isGreen = score >= 67;
  const isYellow = score >= 34 && score < 67;

  const colorClass = isGreen ? "text-noop-green" : isYellow ? "text-noop-yellow" : "text-noop-red";
  const bgClass = isGreen ? "bg-noop-green/10" : isYellow ? "bg-noop-yellow/10" : "bg-noop-red/10";
  const borderClass = isGreen ? "border-noop-green/40" : isYellow ? "border-noop-yellow/40" : "border-noop-red/40";
  const strokeColor = isGreen ? "#00E676" : isYellow ? "#FFD600" : "#FF1744";
  const glowColor = isGreen ? "rgba(0, 230, 118, 0.4)" : isYellow ? "rgba(255, 214, 0, 0.4)" : "rgba(255, 23, 68, 0.4)";

  // SVG Gauge calculations
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden group">
      {/* Dynamic ambient corner glow */}
      <div
        className="absolute -top-10 -left-10 w-36 h-36 rounded-full blur-3xl pointer-events-none opacity-40 transition-all duration-700"
        style={{ backgroundColor: strokeColor }}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-noop-green" />
            Recovery
          </span>
          <h2 className="text-sm font-semibold text-white tracking-tight">Daily Readiness</h2>
        </div>
        <div
          className={`px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase border shadow-sm ${bgClass} ${colorClass} ${borderClass}`}
        >
          {isGreen ? "Optimal" : isYellow ? "Adequate" : "Low"}
        </div>
      </div>

      {/* Liquid Metallic Concentric Gauge */}
      <div className="flex items-center justify-center my-6 relative">
        <svg className="w-48 h-48 -rotate-90 overflow-visible" viewBox="0 0 160 160">
          <defs>
            <filter id="recoveryGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor={glowColor} floodOpacity="0.8" />
            </filter>
            <linearGradient id="recoveryGradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor={strokeColor} stopOpacity="1" />
              <stop offset="100%" stopColor={isGreen ? "#00F0FF" : strokeColor} stopOpacity="0.85" />
            </linearGradient>
          </defs>

          {/* Outer Glass Track */}
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="transparent"
            stroke="rgba(255, 255, 255, 0.05)"
            strokeWidth="12"
          />

          {/* Animated Liquid Metallic Progress Arc */}
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="transparent"
            stroke="url(#recoveryGradient)"
            strokeWidth="12"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            filter="url(#recoveryGlow)"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center Score Readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={`text-5xl font-black tracking-tight tabular-nums font-mono drop-shadow-md ${colorClass}`}
          >
            {score}%
          </span>
          <span className="text-[11px] font-semibold text-noop-subtle uppercase tracking-wider mt-1">
            {recovery.date}
          </span>
        </div>
      </div>

      {/* Biometric Baseline Pillars */}
      <div className="grid grid-cols-2 gap-3 pt-3 border-t border-white/10">
        {/* HRV RMSSD */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-3 shadow-inner">
          <div className="flex items-center gap-1.5 text-noop-subtle text-xs mb-1">
            <Activity className="w-3.5 h-3.5 text-noop-cyan" />
            <span className="font-medium">HRV (RMSSD)</span>
          </div>
          <div className="text-lg font-extrabold text-white tabular-nums font-mono">
            {recovery.hrv_rmssd.toFixed(1)}{" "}
            <span className="text-xs font-normal text-noop-subtle font-sans">ms</span>
          </div>
        </div>

        {/* Resting Heart Rate */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-3 shadow-inner">
          <div className="flex items-center gap-1.5 text-noop-subtle text-xs mb-1">
            <Heart className="w-3.5 h-3.5 text-noop-red" />
            <span className="font-medium">Resting HR</span>
          </div>
          <div className="text-lg font-extrabold text-white tabular-nums font-mono">
            {Math.round(recovery.resting_heart_rate)}{" "}
            <span className="text-xs font-normal text-noop-subtle font-sans">bpm</span>
          </div>
        </div>

        {/* Sleep Performance */}
        {recovery.sleep_performance !== undefined && recovery.sleep_performance !== null && (
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 shadow-inner">
            <div className="flex items-center gap-1.5 text-noop-subtle text-xs mb-1">
              <Moon className="w-3.5 h-3.5 text-noop-indigo" />
              <span className="font-medium">Sleep Need Met</span>
            </div>
            <div className="text-lg font-extrabold text-white tabular-nums font-mono">
              {Math.round(recovery.sleep_performance)}%
            </div>
          </div>
        )}

        {/* Skin Temp */}
        {recovery.skin_temp_deviation !== undefined && recovery.skin_temp_deviation !== null && (
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 shadow-inner">
            <div className="flex items-center gap-1.5 text-noop-subtle text-xs mb-1">
              <Thermometer className="w-3.5 h-3.5 text-noop-yellow" />
              <span className="font-medium">Skin Temp</span>
            </div>
            <div className="text-lg font-extrabold text-white tabular-nums font-mono">
              {recovery.skin_temp_deviation >= 0 ? "+" : ""}
              {recovery.skin_temp_deviation.toFixed(1)}°
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
