import React from "react";
import { Activity, ShieldCheck, Thermometer, Wind, Zap, Heart } from "lucide-react";
import { VitalBandItem } from "../types";

interface VitalSignsCardProps {
  vitals?: VitalBandItem[];
}

export const VitalSignsCard: React.FC<VitalSignsCardProps> = ({ vitals }) => {
  if (!vitals || vitals.length === 0) return null;

  const getIcon = (metric: string) => {
    switch (metric) {
      case "resting_heart_rate":
        return Heart;
      case "hrv_rmssd":
        return Zap;
      case "respiratory_rate":
        return Wind;
      case "skin_temp_deviation":
        return Thermometer;
      case "spo2_pct":
        return Activity;
      default:
        return Activity;
    }
  };

  return (
    <div className="bg-noop-surface/75 border border-white/10 rounded-2xl p-5 shadow-surface backdrop-blur-xl relative overflow-hidden transition-all duration-300 hover:border-white/20">
      {/* Decorative gradient sheen */}
      <div className="absolute top-0 right-0 w-72 h-32 bg-noop-cyan/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/5">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-noop-cyan/20 to-blue-500/10 border border-noop-cyan/30 flex items-center justify-center text-noop-cyan shadow-glowCyan">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-white flex items-center gap-2">
              Health Monitor & Vitals
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-noop-muted">
                μ ± 1.5σ
              </span>
            </h3>
            <p className="text-[11px] text-noop-subtle">
              Personalized 28-day baseline envelope
            </p>
          </div>
        </div>
      </div>

      {/* Vitals Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {vitals.map((item) => {
          const Icon = getIcon(item.metric);
          const hasData = item.value !== null && item.value !== undefined;
          const isInRange = item.band === "in_range";

          return (
            <div
              key={item.metric}
              className={`p-3.5 rounded-xl border transition-all duration-200 relative overflow-hidden flex flex-col justify-between ${
                !hasData
                  ? "bg-white/[0.02] border-white/5 opacity-60"
                  : isInRange
                  ? "bg-white/[0.03] border-white/10 hover:border-white/20"
                  : "bg-amber-500/[0.06] border-amber-500/30 hover:border-amber-500/40"
              }`}
            >
              {/* Tile top: Icon and Status pill */}
              <div className="flex items-center justify-between mb-2">
                <div
                  className={`w-6 h-6 rounded-lg flex items-center justify-center ${
                    isInRange ? "text-noop-cyan bg-noop-cyan/10" : "text-amber-400 bg-amber-400/10"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>

                {hasData ? (
                  <span
                    className={`inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                      isInRange
                        ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                        : "text-amber-400 bg-amber-500/15 border-amber-500/30 shadow-sm"
                    }`}
                  >
                    <span
                      className={`w-1 h-1 rounded-full ${
                        isInRange ? "bg-emerald-400" : "bg-amber-400 animate-pulse"
                      }`}
                    />
                    {isInRange ? "In range" : "Out of range"}
                  </span>
                ) : (
                  <span className="text-[9px] font-mono text-noop-subtle px-1.5 py-0.5 rounded bg-white/5">
                    No data
                  </span>
                )}
              </div>

              {/* Tile middle: Value and Unit */}
              <div className="my-1">
                <span className="text-[11px] text-noop-muted block truncate font-medium">
                  {item.label}
                </span>
                <div className="flex items-baseline space-x-1.5 mt-0.5">
                  <span className="text-xl md:text-2xl font-bold font-mono tracking-tight text-white">
                    {hasData ? (item.metric === "skin_temp_deviation" && (item.value || 0) > 0 ? `+${item.value}` : item.value) : "—"}
                  </span>
                  <span className="text-xs text-noop-subtle font-mono">{item.unit}</span>
                </div>
              </div>

              {/* Tile bottom: Baseline range */}
              <div className="mt-2 pt-2 border-t border-white/5 text-[10px] font-mono text-noop-subtle flex items-center justify-between">
                <span>Baseline</span>
                <span className="text-noop-muted">
                  {item.baseline_min !== undefined && item.baseline_max !== undefined
                    ? `${item.baseline_min}–${item.baseline_max} ${item.unit}`
                    : "Calibrating"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
