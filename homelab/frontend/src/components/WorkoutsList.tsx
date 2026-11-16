import React from "react";
import { Dumbbell, Flame, Heart, Timer } from "lucide-react";
import { Workout } from "../types";

interface WorkoutsListProps {
  workouts: Workout[];
}

function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const h = Math.floor(m / 60);
  if (h > 0) {
    return `${h}h ${m % 60}m`;
  }
  return `${m}m`;
}

export const WorkoutsList: React.FC<WorkoutsListProps> = ({ workouts }) => {
  if (!workouts || workouts.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-6 text-center flex flex-col items-center justify-center min-h-[220px]">
        <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-2 shadow-inner">
          <Dumbbell className="w-6 h-6 text-noop-subtle animate-pulse" />
        </div>
        <h4 className="text-sm font-semibold text-white">No Workouts Logged Today</h4>
        <p className="text-xs text-noop-subtle mt-1 max-w-xs leading-relaxed">
          Auto-detected activities or recorded workouts will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Flame className="w-3.5 h-3.5 text-noop-yellow" />
            Activities
          </span>
          <h3 className="text-sm font-semibold text-white tracking-tight">Recorded Workouts</h3>
        </div>
        <span className="text-xs font-bold text-noop-cyan tabular-nums font-mono px-2 py-0.5 rounded-full bg-noop-cyan/10 border border-noop-cyan/20">
          {workouts.length} total
        </span>
      </div>

      <div className="space-y-3">
        {workouts.map((w) => (
          <div
            key={w.workout_id}
            className="flex items-center justify-between p-3.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-all shadow-inner"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-noop-yellow/15 border border-noop-yellow/30 flex items-center justify-center text-noop-yellow shadow-sm">
                <Dumbbell className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white capitalize">{w.sport_name || "Activity"}</h4>
                <div className="flex items-center gap-3 text-xs text-noop-subtle mt-0.5">
                  <span className="flex items-center gap-1 tabular-nums font-mono">
                    <Timer className="w-3 h-3" />
                    {formatDuration(w.duration_seconds)}
                  </span>
                  {w.avg_heart_rate && (
                    <span className="flex items-center gap-1 tabular-nums font-mono">
                      <Heart className="w-3 h-3 text-noop-red" />
                      {Math.round(w.avg_heart_rate)} bpm
                    </span>
                  )}
                </div>
              </div>
            </div>

            {w.strain_score !== undefined && w.strain_score !== null && (
              <div className="text-right">
                <span className="text-sm font-extrabold text-noop-cyan tabular-nums font-mono">
                  {w.strain_score.toFixed(1)}
                </span>
                <span className="text-[10px] text-noop-subtle block font-semibold uppercase">Strain</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
