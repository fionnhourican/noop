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
      <div className="bg-noop-card border border-noop-border rounded-2xl p-6 text-center">
        <Dumbbell className="w-8 h-8 text-noop-subtle mx-auto mb-2 animate-pulse" />
        <h4 className="text-sm font-semibold text-white">No Workouts Recorded</h4>
        <p className="text-xs text-noop-subtle mt-1">
          Auto-detected activities or recorded workouts will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-noop-card border border-noop-border rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Flame className="w-3.5 h-3.5 text-noop-yellow" />
            Activities
          </span>
          <h3 className="text-sm font-semibold text-white">Recorded Workouts</h3>
        </div>
        <span className="text-xs font-semibold text-noop-cyan">{workouts.length} total</span>
      </div>

      <div className="space-y-3">
        {workouts.map((w) => (
          <div
            key={w.workout_id}
            className="flex items-center justify-between p-3.5 bg-noop-bg/70 hover:bg-noop-bg border border-noop-border/50 rounded-xl transition-all"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-noop-yellow/10 border border-noop-yellow/20 flex items-center justify-center text-noop-yellow">
                <Dumbbell className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white capitalize">{w.sport_name || "Activity"}</h4>
                <div className="flex items-center gap-3 text-xs text-noop-subtle mt-0.5">
                  <span className="flex items-center gap-1">
                    <Timer className="w-3 h-3" />
                    {formatDuration(w.duration_seconds)}
                  </span>
                  <span>{new Date(w.start_time).toLocaleDateString([], { month: "short", day: "numeric" })}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 text-right">
              {w.avg_heart_rate && (
                <div className="hidden sm:block">
                  <div className="flex items-center justify-end gap-1 text-xs text-noop-subtle">
                    <Heart className="w-3 h-3 text-noop-red" />
                    <span>Avg HR</span>
                  </div>
                  <div className="text-sm font-bold text-white">{w.avg_heart_rate} bpm</div>
                </div>
              )}

              {w.strain_score !== undefined && w.strain_score !== null && (
                <div>
                  <div className="text-[10px] text-noop-subtle uppercase tracking-wider">Strain</div>
                  <div className="text-base font-extrabold text-noop-yellow">
                    {w.strain_score.toFixed(1)}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
