import React from "react";
import { Activity, Battery, BatteryCharging, Heart, Radio, Zap } from "lucide-react";

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

  // Compute stats in current window
  const minBpm = React.useMemo(() => {
    if (history.length === 0) return null;
    return Math.min(...history.map((h) => h.bpm));
  }, [history]);

  const maxBpm = React.useMemo(() => {
    if (history.length === 0) return null;
    return Math.max(...history.map((h) => h.bpm));
  }, [history]);

  // Smooth Cubic Bézier Spline Calculation
  const { pathD, areaD, lastPoint } = React.useMemo(() => {
    if (history.length < 2) return { pathD: "", areaD: "", lastPoint: null };

    const min = Math.min(...history.map((h) => h.bpm)) - 4;
    const max = Math.max(...history.map((h) => h.bpm)) + 4;
    const range = Math.max(1, max - min);

    const width = 280;
    const height = 64;

    const points = history.map((h, i) => ({
      x: (i / (history.length - 1)) * width,
      y: height - ((h.bpm - min) / range) * height,
    }));

    // Build smooth cubic Bézier curve
    let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = i > 0 ? points[i - 1] : points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = i != points.length - 2 ? points[i + 2] : p2;

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
    }

    const last = points[points.length - 1];
    const area = `${d} L ${width} ${height} L 0 ${height} Z`;

    return { pathD: d, areaD: area, lastPoint: last };
  }, [history]);

  // Pulse animation duration based on current BPM (60 bpm = 1.0s, 120 bpm = 0.5s)
  const pulseDuration = currentBpm ? `${(60 / Math.max(30, currentBpm)).toFixed(2)}s` : "1.2s";

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden group">
      {/* Subtle background glow when live */}
      {liveState === "connected" && (
        <div className="absolute -top-12 -right-12 w-36 h-36 bg-noop-cyan/10 rounded-full blur-2xl pointer-events-none" />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-noop-cyan animate-pulse" />
            Live Stream
          </span>
          <h2 className="text-sm font-semibold text-white tracking-tight">Real-Time Heart Rate</h2>
        </div>

        {batteryLevel !== undefined && batteryLevel !== null && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-noop-muted shadow-inner">
            {isCharging ? (
              <BatteryCharging className="w-3.5 h-3.5 text-noop-green animate-pulse" />
            ) : (
              <Battery className={`w-3.5 h-3.5 ${batteryLevel <= 20 ? "text-noop-red" : "text-noop-cyan"}`} />
            )}
            <span className="tabular-nums font-mono font-medium">{Math.round(batteryLevel)}%</span>
          </div>
        )}
      </div>

      {/* Main Pulse & Tabular Monospace BPM Display */}
      <div className="flex items-center justify-between my-5">
        <div className="flex items-baseline gap-2.5">
          {currentBpm ? (
            <>
              <span className="text-5xl font-black text-white tracking-tight tabular-nums font-mono drop-shadow-md">
                {currentBpm}
              </span>
              <span className="text-xs font-bold text-noop-subtle uppercase tracking-wider">
                BPM
              </span>
            </>
          ) : (
            <div className="text-2xl font-bold text-noop-subtle flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-noop-yellow animate-ping" />
              <span>{liveState === "connected" ? "Streaming..." : "Standby"}</span>
            </div>
          )}
        </div>

        {/* Pulsing Heart with Harmonic Glow */}
        <div className="relative flex items-center justify-center w-16 h-16">
          {currentBpm && liveState === "connected" && (
            <div
              className="absolute inset-0 rounded-full bg-noop-red/25 animate-ping opacity-75"
              style={{ animationDuration: pulseDuration }}
            />
          )}
          <div
            className={`w-12 h-12 rounded-full flex items-center justify-center border transition-all duration-300 ${
              currentBpm && liveState === "connected"
                ? "bg-noop-red/15 border-noop-red/50 text-noop-red shadow-glowRed"
                : "bg-white/5 border-white/10 text-noop-subtle"
            }`}
            style={{
              animation: currentBpm && liveState === "connected" ? `heartbeat ${pulseDuration} ease-in-out infinite` : "none",
            }}
          >
            <Heart className="w-6 h-6 fill-current" />
          </div>
        </div>
      </div>

      {/* Real-time Smooth Spline Sparkline */}
      <div className="pt-3 border-t border-white/10">
        <div className="flex items-center justify-between text-[11px] text-noop-subtle mb-2">
          <div className="flex items-center gap-3">
            <span>Live Window (30s)</span>
            {minBpm && maxBpm && (
              <span className="tabular-nums font-mono text-[10px] text-noop-muted bg-white/5 px-1.5 py-0.5 rounded">
                {minBpm}–{maxBpm} bpm
              </span>
            )}
          </div>
          {lastTimestamp && (
            <span className="tabular-nums font-mono text-[11px]">
              {new Date(lastTimestamp).toLocaleTimeString()}
            </span>
          )}
        </div>

        <div className="w-full h-16 bg-noop-bg/90 border border-white/5 rounded-xl p-1 flex items-center justify-center overflow-hidden relative shadow-inner">
          {pathD ? (
            <svg className="w-full h-full overflow-visible" viewBox="0 0 280 64" preserveAspectRatio="none">
              <defs>
                <linearGradient id="livePulseFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#00F0FF" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Area Gradient */}
              <path d={areaD} fill="url(#livePulseFill)" />

              {/* Smooth Cubic Spline Line */}
              <path
                d={pathD}
                fill="none"
                stroke="#00F0FF"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="drop-shadow-[0_0_6px_rgba(0,240,255,0.6)]"
              />

              {/* Leading Breathing Head Dot */}
              {lastPoint && (
                <circle
                  cx={lastPoint.x}
                  cy={lastPoint.y}
                  r="4"
                  fill="#ffffff"
                  stroke="#00F0FF"
                  strokeWidth="2.5"
                  className="animate-pulse drop-shadow-[0_0_8px_#00F0FF]"
                />
              )}
            </svg>
          ) : (
            <div className="flex items-center gap-2 text-xs text-noop-subtle">
              <Activity className="w-4 h-4 animate-pulse text-noop-cyan" />
              <span>Awaiting sensor stream...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
