import React, { useState } from "react";
import { AlertTriangle, Info, ShieldAlert, Sparkles, X } from "lucide-react";
import { IllnessEvaluationResponse } from "../types";

interface IllnessAlertBannerProps {
  illness?: IllnessEvaluationResponse;
}

export const IllnessAlertBanner: React.FC<IllnessAlertBannerProps> = ({ illness }) => {
  const [dismissed, setDismissed] = useState(false);

  if (!illness || dismissed || illness.level === "quiet") {
    return null;
  }

  const isRaised = illness.level === "raised";
  const isSuppressed = illness.level === "suppressed";

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border transition-all duration-300 p-4 mb-6 backdrop-blur-xl ${
        isRaised
          ? "bg-amber-500/[0.12] border-amber-500/40 shadow-glowAmber"
          : isSuppressed
          ? "bg-blue-500/[0.08] border-blue-500/30"
          : "bg-white/[0.04] border-white/10"
      }`}
    >
      {/* Decorative ambient flare */}
      <div
        className={`absolute -top-12 -left-12 w-48 h-48 rounded-full blur-3xl pointer-events-none ${
          isRaised ? "bg-amber-500/20" : "bg-blue-500/15"
        }`}
      />

      <div className="flex items-start justify-between relative z-10">
        <div className="flex items-start space-x-3.5">
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border ${
              isRaised
                ? "bg-amber-500/20 border-amber-500/40 text-amber-400"
                : isSuppressed
                ? "bg-blue-500/20 border-blue-500/40 text-blue-400"
                : "bg-white/10 border-white/20 text-noop-subtle"
            }`}
          >
            {isRaised ? (
              <ShieldAlert className="w-5 h-5 animate-pulse" />
            ) : isSuppressed ? (
              <Sparkles className="w-5 h-5" />
            ) : (
              <AlertTriangle className="w-5 h-5" />
            )}
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h4 className="text-sm font-semibold text-white tracking-wide">
                {isRaised
                  ? "Health Early-Warning · Body Under Strain"
                  : isSuppressed
                  ? "Biometric Shift Explained"
                  : "Biometric Shift Noted"}
              </h4>
              <span
                className={`text-[9px] font-mono px-2 py-0.5 rounded-full border uppercase tracking-wider font-semibold ${
                  isRaised
                    ? "bg-amber-500/20 border-amber-500/40 text-amber-300"
                    : "bg-white/10 border-white/15 text-noop-subtle"
                }`}
              >
                Anomaly Score: {illness.score}/100
              </span>
            </div>

            <p className="text-xs text-noop-muted mt-1 leading-relaxed">
              {illness.copy}
            </p>

            {/* Fired signals badges */}
            {illness.fired_signals && illness.fired_signals.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                <span className="text-[10px] text-noop-subtle font-mono mr-1">
                  Corroborating:
                </span>
                {illness.fired_signals.map((sig, idx) => (
                  <span
                    key={idx}
                    className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-black/40 border border-white/10 text-white flex items-center gap-1"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    {sig}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        <button
          onClick={() => setDismissed(true)}
          className="text-noop-subtle hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"
          title="Dismiss notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
