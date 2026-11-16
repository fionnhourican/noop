import React, { useState } from "react";
import { Activity } from "lucide-react";
import { HeartRateSample } from "../types";

interface HeartRateChartProps {
  samples: HeartRateSample[];
}

export const HeartRateChart: React.FC<HeartRateChartProps> = ({ samples }) => {
  const [hoveredPoint, setHoveredPoint] = useState<HeartRateSample | null>(null);

  if (!samples || samples.length === 0) {
    return (
      <div className="bg-noop-card border border-noop-border rounded-2xl p-6 flex flex-col items-center justify-center min-h-[260px] text-center">
        <Activity className="w-8 h-8 text-noop-subtle mb-2 animate-pulse" />
        <h4 className="text-sm font-semibold text-white">No Heart Rate History Available</h4>
        <p className="text-xs text-noop-subtle mt-1">
          Historical heart rate offloads from your strap will populate this timeline.
        </p>
      </div>
    );
  }

  // Sort chronological
  const sorted = [...samples].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  const bpms = sorted.map((s) => s.bpm);
  const minBpm = Math.max(30, Math.min(...bpms) - 5);
  const maxBpm = Math.min(220, Math.max(...bpms) + 5);
  const range = maxBpm - minBpm || 1;

  const width = 800;
  const height = 180;
  const paddingX = 20;
  const paddingY = 20;
  const plotWidth = width - paddingX * 2;
  const plotHeight = height - paddingY * 2;

  const points = sorted.map((s, idx) => {
    const x = paddingX + (idx / (sorted.length - 1 || 1)) * plotWidth;
    const y = paddingY + plotHeight - ((s.bpm - minBpm) / range) * plotHeight;
    return { x, y, sample: s };
  });

  const polylineStr = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  // Gradient area points
  const areaStr = `${points[0].x.toFixed(1)},${height - paddingY} ${polylineStr} ${points[points.length - 1].x.toFixed(1)},${height - paddingY}`;

  return (
    <div className="bg-noop-card border border-noop-border hover:border-noop-border/80 transition-all rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-noop-cyan" />
            Heart Rate Timeline
          </span>
          <h3 className="text-sm font-semibold text-white">Recent Biometric Trace</h3>
        </div>

        {hoveredPoint ? (
          <div className="text-right">
            <div className="text-sm font-bold text-noop-cyan">{hoveredPoint.bpm} bpm</div>
            <div className="text-[10px] text-noop-subtle">
              {new Date(hoveredPoint.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ) : (
          <div className="text-right">
            <div className="text-xs text-noop-subtle">
              Min: <span className="text-white font-semibold">{Math.min(...bpms)}</span> | Max:{" "}
              <span className="text-white font-semibold">{Math.max(...bpms)}</span>
            </div>
          </div>
        )}
      </div>

      <div className="w-full h-48 relative overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="hrGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#00F0FF" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid reference lines */}
          <line
            x1={paddingX}
            y1={paddingY}
            x2={width - paddingX}
            y2={paddingY}
            stroke="#1c2130"
            strokeDasharray="4"
          />
          <line
            x1={paddingX}
            y1={paddingY + plotHeight / 2}
            x2={width - paddingX}
            y2={paddingY + plotHeight / 2}
            stroke="#1c2130"
            strokeDasharray="4"
          />
          <line
            x1={paddingX}
            y1={height - paddingY}
            x2={width - paddingX}
            y2={height - paddingY}
            stroke="#1c2130"
          />

          {/* Shaded Area */}
          <polygon points={areaStr} fill="url(#hrGradient)" />

          {/* Line Chart */}
          <polyline
            fill="none"
            stroke="#00F0FF"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={polylineStr}
          />

          {/* Interactive Hover Nodes */}
          {points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={hoveredPoint === p.sample ? 5 : 2}
              fill={hoveredPoint === p.sample ? "#00F0FF" : "#12151e"}
              stroke="#00F0FF"
              strokeWidth="1.5"
              className="cursor-pointer transition-all"
              onMouseEnter={() => setHoveredPoint(p.sample)}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          ))}
        </svg>
      </div>

      <div className="flex justify-between items-center text-[10px] text-noop-subtle pt-2 border-t border-noop-border/40">
        <span>{new Date(sorted[0].timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
        <span>{sorted.length} recorded samples</span>
        <span>{new Date(sorted[sorted.length - 1].timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
      </div>
    </div>
  );
};
