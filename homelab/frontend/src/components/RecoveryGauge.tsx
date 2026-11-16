import React from "react";
import { Activity, Heart, Moon, Thermometer } from "lucide-react";
import { RecoveryMetric } from "../types";

interface RecoveryGaugeProps {
  recovery?: RecoveryMetric;
}

export const RecoveryGauge: React.FC<RecoveryGaugeProps> = ({ recovery }) => {
  if (!recovery) {
    return (
      <div className="bg-noop-card border border-noop-border rounded-2xl p-6 flex flex-col items-center justify-center min-h-[320px] text-center">
        <Activity className="w-10 h-10 text-noop-subtle mb-3 animate-pulse" />
        <h3 className="text-base font-semibold text-white">No Recovery Data Yet</h3>
        <p className="text-xs text-noop-subtle mt-1 max-w-xs">
          Wear your WHOOP 4.0 through the night to compute your baseline recovery score.
        </p>
      </div>
    );
  }

  const score = Math.round(recovery.recovery_score);
  const isGreen = score >= 67;
  const isYellow = score >= 34 && score < 67;

  const colorClass = isGreen ? "text-noop-green" : isYellow ? "text-noop-yellow" : "text-noop-red";
  const bgClass = isGreen ? "bg-noop-green/10" : isYellow ? "bg-noop-yellow/10" : "bg-noop-red/10";
  const borderClass = isGreen ? "border-noop-green/30" : isYellow ? "border-noop-yellow/30" : "border-noop-red/30";
  const strokeColor = isGreen ? "#00E676" : isYellow ? "#FFD600" : "#FF1744";

  // SVG Gauge calculations
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="bg-noop-card border border-noop-border hover:border-noop-border/80 transition-all rounded-2xl p-6 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle">
            Recovery
          </span>
          <h2 className="text-sm font-semibold text-white">Daily Readiness</h2>
        </div>
        <div className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${bgClass} ${colorClass} ${borderClass}`}>
          {isGreen ? "Optimal" : isYellow ? "Adequate" : "Low"}
        </div>
      </div>

      {/* Circular Gauge */}
      <div className="flex items-center justify-center my-6 relative">
        <svg className="w-44 h-44 -rotate-90" viewBox="0 0 160 160">
          {/* Background Track */}
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="transparent"
            stroke="#1a1e2b"
            strokeWidth="12"
          />
          {/* Animated Progress Arc */}
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="transparent"
            stroke={strokeColor}
            strokeWidth="12"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center Score Readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-extrabold tracking-tight ${colorClass}`}>
            {score}%
          </span>
          <span className="text-[11px] font-medium text-noop-subtle uppercase tracking-wider mt-0.5">
            {recovery.date}
          </span>
        </div>
      </div>

      {/* Biometric Baseline Pillars */}
      <div className="grid grid-cols-2 gap-3 pt-3 border-t border-noop-border/60">
        {/* HRV */}
        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-3">
          <div className="flex items-center gap-1.5 text-noop-subtle text-xs mb-1">
            <Activity className="w-3.5 h-3.5 text-noop-cyan" />
            <span>HRV (RMSSD)</span>
          </div>
          <div className="text-lg font-bold text-white">
            {recovery.hrv_rmssd.toFixed(1)}{" "}
            <span className="text-xs font-normal text-noop-subtle">ms</span>
          </div>
        </div>

        {/* Resting HR */}
        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-3">
          <div className="flex items-center gap-1.5 text-noop-subtle text-xs mb-1">
            <Heart className="w-3.5 h-3.5 text-noop-red" />
            <span>Resting HR</span>
          </div>
          <div className="text-lg font-bold text-white">
            {Math.round(recovery.resting_heart_rate)}{" "}
            <span className="text-xs font-normal text-noop-subtle">bpm</span>
          </div>
        </div>

        {/* Sleep Performance */}
        {recovery.sleep_performance !== undefined && recovery.sleep_performance !== null && (
          <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-3">
            <div className="flex items-center gap-1.5 text-noop-subtle text-xs mb-1">
              <Moon className="w-3.5 h-3.5 text-noop-indigo" />
              <span>Sleep Need Met</span>
            </div>
            <div className="text-lg font-bold text-white">
              {Math.round(recovery.sleep_performance)}%
            </div>
          </div>
        )}

        {/* Skin Temp */}
        {recovery.skin_temp_deviation !== undefined && recovery.skin_temp_deviation !== null && (
          <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-3">
            <div className="flex items-center gap-1.5 text-noop-subtle text-xs mb-1">
              <Thermometer className="w-3.5 h-3.5 text-noop-yellow" />
              <span>Skin Temp</span>
            </div>
            <div className="text-lg font-bold text-white">
              {recovery.skin_temp_deviation >= 0 ? "+" : ""}
              {recovery.skin_temp_deviation.toFixed(1)}°
            </div>
          </div>
        )}
      </div>

      <div className="text-[10px] text-noop-subtle mt-3 text-right">
        Ported NOOP Algorithm v{recovery.algorithm_version}
      </div>
    </div>
  );
};
