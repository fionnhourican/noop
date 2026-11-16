import React from "react";
import { Award, Flame, Heart, TrendingUp, Zap } from "lucide-react";
import { StrainMetric } from "../types";

interface StrainMeterProps {
  strain?: StrainMetric;
}

export const StrainMeter: React.FC<StrainMeterProps> = ({ strain }) => {
  if (!strain) {
    return (
      <div className="glass-card rounded-2xl p-6 flex flex-col items-center justify-center min-h-[340px] text-center relative overflow-hidden">
        <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-3 shadow-inner">
          <Flame className="w-8 h-8 text-noop-subtle animate-pulse" />
        </div>
        <h3 className="text-base font-semibold text-white">No Strain Logged Yet</h3>
        <p className="text-xs text-noop-subtle mt-1.5 max-w-xs leading-relaxed">
          Cardiovascular physical load accumulated today will automatically calculate on a 0.0–21.0 scale via Banister TRIMP.
        </p>
      </div>
    );
  }

  const score = strain.strain_score;
  const maxScale = 21.0;
  const progressPercent = Math.min(100, Math.max(0, (score / maxScale) * 100));

  // Category labels based on WHOOP 0-21 strain zones
  const getZone = () => {
    if (score < 6) return { text: "Rest / Light", color: "text-noop-blue", glow: "rgba(59, 130, 246, 0.4)" };
    if (score < 10) return { text: "Active", color: "text-noop-cyan", glow: "rgba(0, 240, 255, 0.4)" };
    if (score < 14) return { text: "Moderate", color: "text-noop-yellow", glow: "rgba(255, 214, 0, 0.4)" };
    if (score < 18) return { text: "Building", color: "text-amber-500", glow: "rgba(245, 158, 11, 0.4)" };
    return { text: "All-Out", color: "text-noop-red", glow: "rgba(255, 23, 68, 0.4)" };
  };

  const zone = getZone();

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden group">
      {/* Corner flame glow */}
      <div
        className="absolute -top-10 -right-10 w-36 h-36 rounded-full blur-3xl pointer-events-none opacity-30 transition-all duration-700"
        style={{ backgroundColor: zone.glow }}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Flame className="w-3.5 h-3.5 text-amber-500" />
            Day Strain
          </span>
          <h2 className="text-sm font-semibold text-white tracking-tight">Cardiovascular Load</h2>
        </div>
        <div className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-white/5 border border-white/10 text-white flex items-center gap-1.5 shadow-inner">
          <Zap className={`w-3.5 h-3.5 ${zone.color}`} />
          <span className={zone.color}>{zone.text}</span>
        </div>
      </div>

      {/* Main Strain Score Display */}
      <div className="my-6">
        <div className="flex items-baseline gap-2.5 mb-3.5">
          <span className={`text-5xl font-black tracking-tight tabular-nums font-mono drop-shadow-md ${zone.color}`}>
            {score.toFixed(1)}
          </span>
          <span className="text-xs font-semibold text-noop-subtle uppercase tracking-wider">
            / 21.0 MAX
          </span>
        </div>

        {/* Fluid Gradient Progress Track with Glowing Thumb */}
        <div className="w-full h-4 bg-noop-bg/90 rounded-full p-0.5 border border-white/10 overflow-hidden relative shadow-inner">
          <div
            className="h-full rounded-full bg-gradient-to-r from-noop-blue via-noop-cyan via-noop-yellow via-amber-500 to-noop-red transition-all duration-1000 ease-out relative"
            style={{ width: `${Math.max(4, progressPercent)}%` }}
          >
            {/* Specular highlight */}
            <div className="absolute inset-0 bg-gradient-to-b from-white/25 to-transparent rounded-full" />
          </div>
        </div>

        {/* Zone Markers */}
        <div className="flex justify-between text-[10px] font-mono text-noop-subtle mt-2 px-1">
          <span>0 (Rest)</span>
          <span>10 (Active)</span>
          <span>14 (Building)</span>
          <span>21 (Max)</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-2.5 pt-3 border-t border-white/10">
        <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center shadow-inner">
          <div className="flex items-center justify-center gap-1 text-noop-subtle text-[11px] mb-1">
            <Heart className="w-3 h-3 text-noop-cyan" />
            <span className="font-medium">Avg HR</span>
          </div>
          <div className="text-base font-extrabold text-white tabular-nums font-mono">
            {strain.average_hr ? Math.round(strain.average_hr) : "--"}{" "}
            <span className="text-[10px] font-normal text-noop-subtle font-sans">bpm</span>
          </div>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center shadow-inner">
          <div className="flex items-center justify-center gap-1 text-noop-subtle text-[11px] mb-1">
            <Flame className="w-3 h-3 text-noop-red" />
            <span className="font-medium">Max HR</span>
          </div>
          <div className="text-base font-extrabold text-white tabular-nums font-mono">
            {strain.max_hr || "--"}{" "}
            <span className="text-[10px] font-normal text-noop-subtle font-sans">bpm</span>
          </div>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center shadow-inner">
          <div className="flex items-center justify-center gap-1 text-noop-subtle text-[11px] mb-1">
            <Award className="w-3 h-3 text-noop-yellow" />
            <span className="font-medium">Energy</span>
          </div>
          <div className="text-base font-extrabold text-white tabular-nums font-mono">
            {strain.kilojoules ? Math.round(strain.kilojoules) : "--"}{" "}
            <span className="text-[10px] font-normal text-noop-subtle font-sans">kJ</span>
          </div>
        </div>
      </div>

      <div className="text-[10px] text-noop-subtle/80 mt-3 text-right font-mono">
        Banister TRIMP Algorithm
      </div>
    </div>
  );
};
