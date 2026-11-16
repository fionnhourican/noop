import React, { useState, useRef, useCallback, useMemo } from "react";
import { Activity, Clock, Heart, TrendingUp } from "lucide-react";
import { HeartRateSample } from "../types";

interface HeartRateChartProps {
  samples: HeartRateSample[];
}

export const HeartRateChart: React.FC<HeartRateChartProps> = ({ samples }) => {
  const [hoveredPoint, setHoveredPoint] = useState<HeartRateSample | null>(null);
  const [hoverX, setHoverX] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const chartData = useMemo(() => {
    if (!samples || samples.length === 0) return null;

    // Sort chronological
    const sorted = [...samples].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const bpms = sorted.map((s) => s.bpm);
    const minVal = Math.min(...bpms);
    const maxVal = Math.max(...bpms);
    const avgVal = Math.round(bpms.reduce((a, b) => a + b, 0) / bpms.length);

    const minBpm = Math.max(35, minVal - 5);
    const maxBpm = Math.min(215, maxVal + 8);
    const range = maxBpm - minBpm || 1;

    const width = 800;
    const height = 200;
    const paddingX = 24;
    const paddingY = 24;
    const plotWidth = width - paddingX * 2;
    const plotHeight = height - paddingY * 2;

    const points = sorted.map((s, idx) => {
      const x = paddingX + (idx / (sorted.length - 1 || 1)) * plotWidth;
      const y = paddingY + plotHeight - ((s.bpm - minBpm) / range) * plotHeight;
      return { x, y, sample: s };
    });

    // Smooth cubic spline construction
    let lineD = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = i > 0 ? points[i - 1] : points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = i !== points.length - 2 ? points[i + 2] : p2;

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      lineD += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
    }

    const areaD = `${lineD} L ${points[points.length - 1].x.toFixed(1)} ${height - paddingY} L ${points[0].x.toFixed(1)} ${height - paddingY} Z`;

    return {
      sorted,
      bpms,
      minVal,
      maxVal,
      avgVal,
      minBpm,
      maxBpm,
      range,
      width,
      height,
      paddingX,
      paddingY,
      plotWidth,
      plotHeight,
      points,
      lineD,
      areaD,
    };
  }, [samples]);

  // Pointer scrubber interaction (unconditionally registered)
  const handlePointerMove = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
      if (!svgRef.current || !chartData) return;
      const rect = svgRef.current.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const scaleX = chartData.width / rect.width;
      const svgX = clientX * scaleX;

      // Find nearest point
      let nearest = chartData.points[0];
      let minDiff = Math.abs(chartData.points[0].x - svgX);
      for (const p of chartData.points) {
        const diff = Math.abs(p.x - svgX);
        if (diff < minDiff) {
          minDiff = diff;
          nearest = p;
        }
      }

      setHoveredPoint(nearest.sample);
      setHoverX(nearest.x);
    },
    [chartData]
  );

  const handlePointerLeave = useCallback(() => {
    setHoveredPoint(null);
    setHoverX(null);
  }, []);

  if (!chartData) {
    return (
      <div className="glass-card rounded-2xl p-6 flex flex-col items-center justify-center min-h-[300px] text-center relative overflow-hidden">
        <div className="w-14 h-14 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-3 shadow-inner">
          <Activity className="w-7 h-7 text-noop-subtle animate-pulse" />
        </div>
        <h4 className="text-sm font-semibold text-white">No Heart Rate History Available</h4>
        <p className="text-xs text-noop-subtle mt-1.5 max-w-xs leading-relaxed">
          Historical heart rate records offloaded from your WHOOP strap will render your 24-hour biometric trace here.
        </p>
      </div>
    );
  }

  const {
    sorted,
    minVal,
    maxVal,
    avgVal,
    minBpm,
    range,
    width,
    height,
    paddingX,
    paddingY,
    plotHeight,
    lineD,
    areaD,
  } = chartData;

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-6 relative overflow-hidden group">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-noop-cyan" />
            Heart Rate Timeline
          </span>
          <h3 className="text-sm font-semibold text-white tracking-tight">Recent Biometric Trace</h3>
        </div>

        {/* Hover Readout vs Baseline Summary */}
        {hoveredPoint ? (
          <div className="text-right flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-noop-cyan/15 border border-noop-cyan/30 text-noop-cyan shadow-sm">
              <Heart className="w-3.5 h-3.5 fill-current animate-pulse" />
              <span className="text-sm font-extrabold tabular-nums font-mono">
                {hoveredPoint.bpm} bpm
              </span>
            </div>
            <span className="tabular-nums font-mono text-xs text-noop-subtle">
              {new Date(hoveredPoint.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-3 text-xs text-noop-subtle">
            <span className="bg-white/5 border border-white/10 px-2 py-0.5 rounded text-white tabular-nums font-mono">
              Min {minVal}
            </span>
            <span className="bg-white/5 border border-white/10 px-2 py-0.5 rounded text-noop-cyan tabular-nums font-mono">
              Avg {avgVal}
            </span>
            <span className="bg-white/5 border border-white/10 px-2 py-0.5 rounded text-noop-red tabular-nums font-mono">
              Max {maxVal}
            </span>
          </div>
        )}
      </div>

      {/* SVG Chart Area */}
      <div className="w-full h-52 relative overflow-visible">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible cursor-crosshair touch-none"
          preserveAspectRatio="none"
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
        >
          <defs>
            <linearGradient id="traceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#00F0FF" stopOpacity="0.0" />
            </linearGradient>
            <filter id="scrubberGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#00F0FF" floodOpacity="0.8" />
            </filter>
          </defs>

          {/* Reference guidelines */}
          <line
            x1={paddingX}
            y1={paddingY}
            x2={width - paddingX}
            y2={paddingY}
            stroke="rgba(255,255,255,0.06)"
            strokeDasharray="4 4"
          />
          <line
            x1={paddingX}
            y1={paddingY + plotHeight / 2}
            x2={width - paddingX}
            y2={paddingY + plotHeight / 2}
            stroke="rgba(255,255,255,0.06)"
            strokeDasharray="4 4"
          />
          <line
            x1={paddingX}
            y1={height - paddingY}
            x2={width - paddingX}
            y2={height - paddingY}
            stroke="rgba(255,255,255,0.12)"
          />

          {/* Gradient Shaded Area */}
          <path d={areaD} fill="url(#traceFill)" />

          {/* Smooth Continuous Line Trace */}
          <path
            d={lineD}
            fill="none"
            stroke="#00F0FF"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="drop-shadow-[0_0_8px_rgba(0,240,255,0.4)]"
          />

          {/* Interactive Scrubber Line */}
          {hoverX !== null && (
            <>
              <line
                x1={hoverX}
                y1={paddingY}
                x2={hoverX}
                y2={height - paddingY}
                stroke="#00F0FF"
                strokeWidth="1.5"
                strokeDasharray="3 3"
                className="opacity-75"
              />
              {hoveredPoint && (
                <circle
                  cx={hoverX}
                  cy={paddingY + plotHeight - ((hoveredPoint.bpm - minBpm) / range) * plotHeight}
                  r="5"
                  fill="#ffffff"
                  stroke="#00F0FF"
                  strokeWidth="3"
                  filter="url(#scrubberGlow)"
                />
              )}
            </>
          )}
        </svg>
      </div>

      {/* Axis Footer */}
      <div className="flex items-center justify-between text-[11px] font-mono text-noop-subtle mt-2 px-1">
        <span>
          {new Date(sorted[0].timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
        <span className="text-[10px] text-noop-subtle/70 uppercase tracking-widest font-sans">
          Hover or drag to scrub timeline
        </span>
        <span>
          {new Date(sorted[sorted.length - 1].timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
};
