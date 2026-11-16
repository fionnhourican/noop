import React from "react";
import { AlertCircle, CheckCircle2, Clock, Moon, Sparkles, Sun, Zap } from "lucide-react";
import { SleepSession } from "../types";

interface SleepBreakdownProps {
  sleep?: SleepSession;
}

function formatHoursMinutes(totalSeconds?: number): string {
  if (!totalSeconds || totalSeconds <= 0) return "0h 0m";
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

function formatMinutes(minutes?: number): string {
  if (!minutes || minutes <= 0) return "0m";
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (h === 0) return `${m}m`;
  return `${h}h ${m}m`;
}

export const SleepBreakdown: React.FC<SleepBreakdownProps> = ({ sleep }) => {
  if (!sleep) {
    return (
      <div className="glass-card rounded-2xl p-6 flex flex-col items-center justify-center min-h-[340px] text-center relative overflow-hidden">
        <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-3 shadow-inner">
          <Moon className="w-8 h-8 text-noop-subtle animate-pulse" />
        </div>
        <h3 className="text-base font-semibold text-white">No Sleep Session Recorded</h3>
        <p className="text-xs text-noop-subtle mt-1.5 max-w-xs leading-relaxed">
          Sleep stages (Deep, REM, Light, Awake) will automatically sync once your nocturnal rest concludes.
        </p>
      </div>
    );
  }

  const totalSec = sleep.duration_seconds || 1;
  const deepSec = sleep.deep_seconds || 0;
  const remSec = sleep.rem_seconds || 0;
  const lightSec = sleep.light_seconds || 0;
  const awakeSec = sleep.wake_seconds || 0;

  const deepPct = Math.round((deepSec / totalSec) * 100);
  const remPct = Math.round((remSec / totalSec) * 100);
  const lightPct = Math.round((lightSec / totalSec) * 100);
  const awakePct = Math.max(0, 100 - (deepPct + remPct + lightPct));

  const startTimeStr = new Date(sleep.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const endTimeStr = new Date(sleep.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const sleepNeedMin = sleep.sleep_need_minutes || 480;
  const sleptMin = Math.round(totalSec / 60);
  const needPct = Math.min(100, Math.round((sleptMin / sleepNeedMin) * 100));
  const debtMin = sleep.sleep_debt_minutes || 0;

  // Chronological stages for hypnogram
  const hasGranularStages = sleep.stages && sleep.stages.length > 0;

  const getStageColor = (stage: string) => {
    switch (stage.toLowerCase()) {
      case "deep":
        return "bg-noop-indigo";
      case "rem":
        return "bg-noop-cyan";
      case "light":
        return "bg-noop-blue";
      case "wake":
      case "awake":
        return "bg-rose-500";
      default:
        return "bg-white/20";
    }
  };

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden group">
      {/* Corner indigo ambient glow */}
      <div className="absolute -top-10 -right-10 w-36 h-36 rounded-full bg-noop-indigo/15 blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Moon className="w-3.5 h-3.5 text-noop-indigo" />
            Sleep Performance & Architecture
          </span>
          <h2 className="text-sm font-semibold text-white tracking-tight">Sleep Session</h2>
        </div>

        <div className="flex items-center gap-2">
          {sleep.sleep_efficiency !== undefined && sleep.sleep_efficiency !== null && (
            <div className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-noop-indigo/15 border border-noop-indigo/30 text-noop-indigo shadow-inner">
              {Math.round(sleep.sleep_efficiency)}% Efficiency
            </div>
          )}
        </div>
      </div>

      {/* Main Sleep Duration & Need Readout */}
      <div className="my-5">
        <div className="flex items-baseline justify-between mb-1.5">
          <div className="flex items-baseline gap-2.5">
            <span className="text-5xl font-black text-white tracking-tight tabular-nums font-mono drop-shadow-md">
              {formatHoursMinutes(sleep.duration_seconds)}
            </span>
            <span className="text-xs font-semibold text-noop-subtle uppercase tracking-wider">Total Sleep</span>
          </div>

          {/* Sleep Need pill */}
          <div className="text-right">
            <span className="text-[10px] font-mono text-noop-subtle block uppercase tracking-wider">
              Need: {formatMinutes(sleepNeedMin)}
            </span>
            <span className="text-xs font-mono font-bold text-noop-cyan">
              {needPct}% of target
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-noop-muted font-mono mb-3">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <Moon className="w-3.5 h-3.5 text-noop-subtle" /> Bed: {startTimeStr}
            </span>
            <span className="flex items-center gap-1.5">
              <Sun className="w-3.5 h-3.5 text-noop-yellow" /> Wake: {endTimeStr}
            </span>
          </div>

          {/* Sleep Debt status indicator */}
          <div className="flex items-center gap-1.5">
            {debtMin > 0 ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                <AlertCircle className="w-3 h-3" />
                Debt: {formatMinutes(debtMin)}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                <CheckCircle2 className="w-3 h-3" />
                Debt: Balanced
              </span>
            )}
          </div>
        </div>

        {/* Chronological Hypnogram Timeline or Proportional Bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-[10px] font-mono text-noop-subtle mb-1">
            <span>Hypnogram Timeline</span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-noop-indigo" /> Deep
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-noop-cyan" /> REM
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-noop-blue" /> Light
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-rose-500" /> Awake
              </span>
            </div>
          </div>

          <div className="w-full h-4 bg-noop-bg/90 rounded-full p-0.5 border border-white/10 flex overflow-hidden shadow-inner">
            {hasGranularStages ? (
              sleep.stages.map((stg, i) => {
                const widthPct = Math.max(0.5, (stg.duration_seconds / totalSec) * 100);
                return (
                  <div
                    key={i}
                    title={`${stg.stage.toUpperCase()}: ${Math.round(stg.duration_seconds / 60)}m`}
                    style={{ width: `${widthPct}%` }}
                    className={`h-full ${getStageColor(stg.stage)} transition-all first:rounded-l-full last:rounded-r-full`}
                  />
                );
              })
            ) : (
              <>
                <div
                  title={`Deep: ${deepPct}%`}
                  style={{ width: `${deepPct}%` }}
                  className="h-full bg-noop-indigo rounded-l-full transition-all"
                />
                <div
                  title={`REM: ${remPct}%`}
                  style={{ width: `${remPct}%` }}
                  className="h-full bg-noop-cyan transition-all"
                />
                <div
                  title={`Light: ${lightPct}%`}
                  style={{ width: `${lightPct}%` }}
                  className="h-full bg-noop-blue transition-all"
                />
                <div
                  title={`Awake: ${awakePct}%`}
                  style={{ width: `${awakePct}%` }}
                  className="h-full bg-rose-500 rounded-r-full transition-all"
                />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Stage Breakdown Grid */}
      <div className="grid grid-cols-4 gap-2.5 pt-3 border-t border-white/10 text-center">
        <div className="bg-white/5 border border-white/10 rounded-xl p-2.5 shadow-inner">
          <div className="flex items-center justify-center gap-1 text-[10px] text-noop-indigo font-bold uppercase mb-0.5">
            <Sparkles className="w-3 h-3" />
            <span>Deep</span>
          </div>
          <div className="text-xs font-extrabold text-white tabular-nums font-mono">{formatHoursMinutes(deepSec)}</div>
          <div className="text-[10px] text-noop-subtle tabular-nums font-mono">{deepPct}%</div>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-2.5 shadow-inner">
          <div className="flex items-center justify-center gap-1 text-[10px] text-noop-cyan font-bold uppercase mb-0.5">
            <Zap className="w-3 h-3" />
            <span>REM</span>
          </div>
          <div className="text-xs font-extrabold text-white tabular-nums font-mono">{formatHoursMinutes(remSec)}</div>
          <div className="text-[10px] text-noop-subtle tabular-nums font-mono">{remPct}%</div>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-2.5 shadow-inner">
          <div className="flex items-center justify-center gap-1 text-[10px] text-noop-blue font-bold uppercase mb-0.5">
            <Moon className="w-3 h-3" />
            <span>Light</span>
          </div>
          <div className="text-xs font-extrabold text-white tabular-nums font-mono">{formatHoursMinutes(lightSec)}</div>
          <div className="text-[10px] text-noop-subtle tabular-nums font-mono">{lightPct}%</div>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-2.5 shadow-inner">
          <div className="flex items-center justify-center gap-1 text-[10px] text-rose-400 font-bold uppercase mb-0.5">
            <Clock className="w-3 h-3" />
            <span>Awake</span>
          </div>
          <div className="text-xs font-extrabold text-white tabular-nums font-mono">{formatHoursMinutes(awakeSec)}</div>
          <div className="text-[10px] text-noop-subtle tabular-nums font-mono">{awakePct}%</div>
        </div>
      </div>
    </div>
  );
};
