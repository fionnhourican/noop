import React from "react";
import { Award, Flame, Heart, Zap } from "lucide-react";
import { StrainMetric } from "../types";

interface StrainMeterProps {
  strain?: StrainMetric;
}

export const StrainMeter: React.FC<StrainMeterProps> = ({ strain }) => {
  if (!strain) {
    return (
      <div className="bg-noop-card border border-noop-border rounded-2xl p-6 flex flex-col items-center justify-center min-h-[320px] text-center">
        <Flame className="w-10 h-10 text-noop-subtle mb-3 animate-pulse" />
        <h3 className="text-base font-semibold text-white">No Strain Logged Yet</h3>
        <p className="text-xs text-noop-subtle mt-1 max-w-xs">
          Physical cardiovascular load accumulated today will appear here on a 0 - 21.0 scale.
        </p>
      </div>
    );
  }

  const score = strain.strain_score;
  const maxScale = 21.0;
  const progressPercent = Math.min(100, Math.max(0, (score / maxScale) * 100));

  // Category labels based on WHOOP 0-21 strain levels
  const levelText =
    score < 10 ? "Light" : score < 14 ? "Moderate" : score < 18 ? "Strenuous" : "All Out";

  const colorClass =
    score < 10
      ? "text-noop-blue"
      : score < 14
      ? "text-noop-yellow"
      : score < 18
      ? "text-amber-500"
      : "text-noop-red";

  return (
    <div className="bg-noop-card border border-noop-border hover:border-noop-border/80 transition-all rounded-2xl p-6 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle">
            Day Strain
          </span>
          <h2 className="text-sm font-semibold text-white">Cardiovascular Load</h2>
        </div>
        <div className="px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-noop-bg border border-noop-border text-noop-cyan flex items-center gap-1">
          <Zap className="w-3 h-3" />
          <span>{levelText}</span>
        </div>
      </div>

      {/* Main Strain Score Display */}
      <div className="my-6">
        <div className="flex items-baseline gap-2 mb-3">
          <span className={`text-5xl font-extrabold tracking-tight ${colorClass}`}>
            {score.toFixed(1)}
          </span>
          <span className="text-sm font-medium text-noop-subtle">/ 21.0</span>
        </div>

        {/* Progress bar with smooth WHOOP gradient */}
        <div className="w-full h-3.5 bg-noop-bg rounded-full p-0.5 border border-noop-border/80 overflow-hidden relative">
          <div
            className="h-full rounded-full bg-gradient-to-r from-noop-blue via-noop-yellow to-noop-red transition-all duration-1000 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="flex justify-between text-[10px] text-noop-subtle mt-1.5 px-0.5">
          <span>0 (Rest)</span>
          <span>10 (Moderate)</span>
          <span>14 (Strenuous)</span>
          <span>21 (Max)</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-2.5 pt-3 border-t border-noop-border/60">
        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-2.5 text-center">
          <div className="flex items-center justify-center gap-1 text-noop-subtle text-[11px] mb-1">
            <Heart className="w-3 h-3 text-noop-cyan" />
            <span>Avg HR</span>
          </div>
          <div className="text-base font-bold text-white">
            {strain.average_hr ? Math.round(strain.average_hr) : "--"}{" "}
            <span className="text-[10px] font-normal text-noop-subtle">bpm</span>
          </div>
        </div>

        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-2.5 text-center">
          <div className="flex items-center justify-center gap-1 text-noop-subtle text-[11px] mb-1">
            <Flame className="w-3 h-3 text-noop-red" />
            <span>Max HR</span>
          </div>
          <div className="text-base font-bold text-white">
            {strain.max_hr || "--"}{" "}
            <span className="text-[10px] font-normal text-noop-subtle">bpm</span>
          </div>
        </div>

        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-2.5 text-center">
          <div className="flex items-center justify-center gap-1 text-noop-subtle text-[11px] mb-1">
            <Award className="w-3 h-3 text-noop-yellow" />
            <span>Energy</span>
          </div>
          <div className="text-base font-bold text-white">
            {strain.kilojoules ? Math.round(strain.kilojoules) : "--"}{" "}
            <span className="text-[10px] font-normal text-noop-subtle">kJ</span>
          </div>
        </div>
      </div>

      <div className="text-[10px] text-noop-subtle mt-3 text-right">
        Banister TRIMP v{strain.algorithm_version}
      </div>
    </div>
  );
};
