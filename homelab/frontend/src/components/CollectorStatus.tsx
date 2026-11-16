import React from "react";
import { Battery, BatteryCharging, CheckCircle2, Clock, Database, Laptop, Shield, Wifi } from "lucide-react";
import { CollectorStatus as CollectorStatusType } from "../types";

interface CollectorStatusProps {
  status?: CollectorStatusType;
}

export const CollectorStatusCard: React.FC<CollectorStatusProps> = ({ status }) => {
  if (!status) {
    return (
      <div className="glass-card rounded-2xl p-6 text-center flex flex-col items-center justify-center min-h-[220px]">
        <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-2 shadow-inner">
          <Laptop className="w-6 h-6 text-noop-subtle animate-pulse" />
        </div>
        <h4 className="text-sm font-semibold text-white">Collector Standby</h4>
        <p className="text-xs text-noop-subtle mt-1 max-w-xs leading-relaxed">
          Waiting for Windows 11 background collector telemetry sync.
        </p>
      </div>
    );
  }

  const isConnected = status.connection_state.toLowerCase() === "connected";
  const lastSyncStr = status.last_sync_timestamp
    ? new Date(status.last_sync_timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "Never";

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-6 relative overflow-hidden group">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Laptop className="w-3.5 h-3.5 text-noop-cyan" />
            Windows 11 Gateway
          </span>
          <h3 className="text-sm font-semibold text-white tracking-tight">Agent Telemetry</h3>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-white/5 border border-white/10 shadow-inner">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? "bg-noop-green animate-pulse shadow-glowGreen" : "bg-noop-yellow animate-ping"
            }`}
          />
          <span className={isConnected ? "text-noop-green font-bold uppercase tracking-wider text-[11px]" : "text-noop-yellow"}>
            {status.connection_state}
          </span>
        </div>
      </div>

      {/* Telemetry Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Device ID */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-3 shadow-inner">
          <div className="flex items-center gap-1 text-noop-subtle text-xs mb-1">
            <Wifi className="w-3.5 h-3.5 text-noop-cyan" />
            <span className="font-medium">Target Strap</span>
          </div>
          <div className="text-sm font-extrabold text-white truncate tabular-nums font-mono" title={status.device_id}>
            {status.device_id}
          </div>
        </div>

        {/* Battery */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-3 shadow-inner">
          <div className="flex items-center gap-1 text-noop-subtle text-xs mb-1">
            {status.is_charging ? (
              <BatteryCharging className="w-3.5 h-3.5 text-noop-green animate-pulse" />
            ) : (
              <Battery className="w-3.5 h-3.5 text-noop-cyan" />
            )}
            <span className="font-medium">Battery</span>
          </div>
          <div className="text-sm font-extrabold text-white tabular-nums font-mono flex items-center gap-1">
            <span>
              {status.battery_percentage !== undefined && status.battery_percentage !== null
                ? `${Math.round(status.battery_percentage)}%`
                : "--"}
            </span>
            {status.is_charging && <span className="text-xs text-noop-green">⚡</span>}
          </div>
        </div>

        {/* Local Queue Backlog */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-3 shadow-inner">
          <div className="flex items-center gap-1 text-noop-subtle text-xs mb-1">
            <Database className="w-3.5 h-3.5 text-noop-yellow" />
            <span className="font-medium">Queue Status</span>
          </div>
          <div className="text-sm font-extrabold text-white tabular-nums font-mono">
            {status.queued_records}{" "}
            <span className="text-[10px] font-normal text-noop-subtle font-sans">pending</span>
          </div>
        </div>

        {/* Last Sync */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-3 shadow-inner">
          <div className="flex items-center gap-1 text-noop-subtle text-xs mb-1">
            <Clock className="w-3.5 h-3.5 text-noop-indigo" />
            <span className="font-medium">Last Sync</span>
          </div>
          <div className="text-sm font-extrabold text-white tabular-nums font-mono truncate">{lastSyncStr}</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-[11px] text-noop-subtle mt-4 pt-3 border-t border-white/10">
        <span className="flex items-center gap-1.5 text-noop-green font-medium">
          <Shield className="w-3.5 h-3.5" /> Encrypted WireGuard (Tailscale)
        </span>
        <span className="font-mono text-[10px] text-noop-subtle">Agent v{status.agent_version}</span>
      </div>
    </div>
  );
};
