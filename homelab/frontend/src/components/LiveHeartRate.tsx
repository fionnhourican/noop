import React from "react";
import { Activity, Battery, BatteryCharging, Heart, Radio } from "lucide-react";

interface LiveHeartRateProps {
  bpm: number | null;
  history: { time: string; bpm: number }[];
  liveState: "connected" | "connecting" | "disconnected";
  batteryLevel?: number | null;
  isCharging?: boolean | null;
  lastTimestamp?: string | null;
}

export const LiveHeartRate: React.FC<LiveHeartRateProps> = ({
  bpm,
  history,
  liveState,
  batteryLevel,
  isCharging,
  lastTimestamp,
}) => {
  const currentBpm = bpm || (history.length > 0 ? history[history.length - 1].bpm : null);

  // SVG Sparkline calculation
  const sparklinePoints = React.useMemo(() => {
    if (history.length < 2) return "";
    const minBpm = Math.min(...history.map((h) => h.bpm)) - 5;
    const maxBpm = Math.max(...history.map((h) => h.bpm)) + 5;
    const range = Math.max(1, maxBpm - minBpm);

    const width = 280;
    const height = 64;

    return history
      .map((h, i) => {
        const x = (i / (history.length - 1)) * width;
        const y = height - ((h.bpm - minBpm) / range) * height;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [history]);

  // Pulse animation duration based on current BPM (e.g. 60 bpm = 1.0s, 120 bpm = 0.5s)
  const pulseDuration = currentBpm ? `${(60 / currentBpm).toFixed(2)}s` : "1.2s";

  return (
    <div className="bg-noop-card border border-noop-border hover:border-noop-border/80 transition-all rounded-2xl p-6 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-noop-cyan" />
            Live Stream
          </span>
          <h2 className="text-sm font-semibold text-white">Real-Time Heart Rate</h2>
        </div>

        {batteryLevel !== undefined && batteryLevel !== null && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-noop-bg border border-noop-border text-xs text-noop-muted">
            {isCharging ? (
              <BatteryCharging className="w-3.5 h-3.5 text-noop-green" />
            ) : (
              <Battery className="w-3.5 h-3.5 text-noop-cyan" />
            )}
            <span>{Math.round(batteryLevel)}%</span>
          </div>
        )}
      </div>

      {/* Main Pulse & BPM Display */}
      <div className="flex items-center justify-between my-4">
        <div className="flex items-baseline gap-2">
          {currentBpm ? (
            <>
              <span className="text-5xl font-black text-white tracking-tight">
                {currentBpm}
              </span>
              <span className="text-sm font-semibold text-noop-subtle uppercase tracking-wider">
                bpm
              </span>
            </>
          ) : (
            <div className="text-3xl font-bold text-noop-subtle">
              {liveState === "connected" ? "Streaming..." : "Standby"}
            </div>
          )}
        </div>

        {/* Pulsing Heart Animation */}
        <div className="relative flex items-center justify-center w-16 h-16">
          {currentBpm && liveState === "connected" && (
            <div
              className="absolute inset-0 rounded-full bg-noop-red/20 animate-ping opacity-60"
              style={{ animationDuration: pulseDuration }}
            />
          )}
          <div
            className={`w-12 h-12 rounded-full flex items-center justify-center border shadow-lg ${
              currentBpm && liveState === "connected"
                ? "bg-noop-red/10 border-noop-red/40 text-noop-red shadow-noop-red/20"
                : "bg-noop-bg border-noop-border text-noop-subtle"
            }`}
            style={{
              animation: currentBpm && liveState === "connected" ? `heartbeat ${pulseDuration} ease-in-out infinite` : "none",
            }}
          >
            <Heart className="w-6 h-6 fill-current" />
          </div>
        </div>
      </div>

      {/* Real-time Sparkline Trend */}
      <div className="pt-2 border-t border-noop-border/60">
        <div className="flex items-center justify-between text-[11px] text-noop-subtle mb-1.5">
          <span>Real-time Window (30s)</span>
          {lastTimestamp && (
            <span>{new Date(lastTimestamp).toLocaleTimeString()}</span>
          )}
        </div>

        <div className="w-full h-16 bg-noop-bg/80 border border-noop-border/40 rounded-xl p-1 flex items-center justify-center overflow-hidden">
          {sparklinePoints ? (
            <svg className="w-full h-full overflow-visible" viewBox="0 0 280 64" preserveAspectRatio="none">
              <polyline
                fill="none"
                stroke="#00F0FF"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={sparklinePoints}
              />
            </svg>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-noop-subtle">
              <Activity className="w-3.5 h-3.5 animate-pulse" />
              <span>Awaiting sensor frames...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
