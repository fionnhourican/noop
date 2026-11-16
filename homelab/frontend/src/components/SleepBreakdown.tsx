import React from "react";
import { Clock, Moon, Sparkles, Sun, Zap } from "lucide-react";
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

export const SleepBreakdown: React.FC<SleepBreakdownProps> = ({ sleep }) => {
  if (!sleep) {
    return (
      <div className="bg-noop-card border border-noop-border rounded-2xl p-6 flex flex-col items-center justify-center min-h-[320px] text-center">
        <Moon className="w-10 h-10 text-noop-subtle mb-3 animate-pulse" />
        <h3 className="text-base font-semibold text-white">No Sleep Session Recorded</h3>
        <p className="text-xs text-noop-subtle mt-1 max-w-xs">
          Sleep sessions and stages will automatically sync once your nocturnal rest concludes.
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

  return (
    <div className="bg-noop-card border border-noop-border hover:border-noop-border/80 transition-all rounded-2xl p-6 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Moon className="w-3.5 h-3.5 text-noop-indigo" />
            Sleep Performance
          </span>
          <h2 className="text-sm font-semibold text-white">Sleep Architecture</h2>
        </div>

        {sleep.sleep_efficiency !== undefined && sleep.sleep_efficiency !== null && (
          <div className="px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-noop-indigo/10 border border-noop-indigo/30 text-noop-indigo">
            {Math.round(sleep.sleep_efficiency)}% Efficiency
          </div>
        )}
      </div>

      {/* Main Sleep Duration Readout */}
      <div className="my-5">
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-4xl font-extrabold text-white tracking-tight">
            {formatHoursMinutes(sleep.duration_seconds)}
          </span>
          <span className="text-xs text-noop-subtle">total sleep</span>
        </div>

        <div className="flex items-center gap-4 text-xs text-noop-muted">
          <span className="flex items-center gap-1">
            <Moon className="w-3.5 h-3.5 text-noop-subtle" /> Bed: {startTimeStr}
          </span>
          <span className="flex items-center gap-1">
            <Sun className="w-3.5 h-3.5 text-noop-yellow" /> Wake: {endTimeStr}
          </span>
        </div>

        {/* Segmented Stages Progress Bar */}
        <div className="w-full h-3.5 bg-noop-bg rounded-full p-0.5 border border-noop-border/80 flex overflow-hidden mt-4">
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
        </div>
      </div>

      {/* Stage Breakdown Grid */}
      <div className="grid grid-cols-4 gap-2 pt-3 border-t border-noop-border/60 text-center">
        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-2">
          <div className="flex items-center justify-center gap-1 text-[10px] text-noop-indigo font-semibold uppercase mb-0.5">
            <Sparkles className="w-3 h-3" />
            <span>Deep</span>
          </div>
          <div className="text-xs font-bold text-white">{formatHoursMinutes(deepSec)}</div>
          <div className="text-[10px] text-noop-subtle">{deepPct}%</div>
        </div>

        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-2">
          <div className="flex items-center justify-center gap-1 text-[10px] text-noop-cyan font-semibold uppercase mb-0.5">
            <Zap className="w-3 h-3" />
            <span>REM</span>
          </div>
          <div className="text-xs font-bold text-white">{formatHoursMinutes(remSec)}</div>
          <div className="text-[10px] text-noop-subtle">{remPct}%</div>
        </div>

        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-2">
          <div className="flex items-center justify-center gap-1 text-[10px] text-noop-blue font-semibold uppercase mb-0.5">
            <Moon className="w-3 h-3" />
            <span>Light</span>
          </div>
          <div className="text-xs font-bold text-white">{formatHoursMinutes(lightSec)}</div>
          <div className="text-[10px] text-noop-subtle">{lightPct}%</div>
        </div>

        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-2">
          <div className="flex items-center justify-center gap-1 text-[10px] text-rose-400 font-semibold uppercase mb-0.5">
            <Clock className="w-3 h-3" />
            <span>Awake</span>
          </div>
          <div className="text-xs font-bold text-white">{formatHoursMinutes(awakeSec)}</div>
          <div className="text-[10px] text-noop-subtle">{awakePct}%</div>
        </div>
      </div>
    </div>
  );
};
