import React from "react";
import { Battery, BatteryCharging, Clock, Database, Laptop, Shield, Wifi } from "lucide-react";
import { CollectorStatus as CollectorStatusType } from "../types";

interface CollectorStatusProps {
  status?: CollectorStatusType;
}

export const CollectorStatusCard: React.FC<CollectorStatusProps> = ({ status }) => {
  if (!status) {
    return (
      <div className="bg-noop-card border border-noop-border rounded-2xl p-6 text-center">
        <Laptop className="w-8 h-8 text-noop-subtle mx-auto mb-2 animate-pulse" />
        <h4 className="text-sm font-semibold text-white">Collector Offline</h4>
        <p className="text-xs text-noop-subtle mt-1">
          Waiting for Windows 11 background collector telemetry.
        </p>
      </div>
    );
  }

  const isConnected = status.connection_state.toLowerCase() === "connected";
  const lastSyncStr = status.last_sync_timestamp
    ? new Date(status.last_sync_timestamp).toLocaleTimeString()
    : "Never";

  return (
    <div className="bg-noop-card border border-noop-border hover:border-noop-border/80 transition-all rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-noop-subtle flex items-center gap-1.5">
            <Laptop className="w-3.5 h-3.5 text-noop-cyan" />
            Windows 11 Gateway
          </span>
          <h3 className="text-sm font-semibold text-white">Agent Telemetry</h3>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-noop-bg border border-noop-border">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? "bg-noop-green" : "bg-noop-yellow animate-pulse"
            }`}
          />
          <span className={isConnected ? "text-noop-green" : "text-noop-yellow"}>
            {status.connection_state}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Device ID */}
        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-3">
          <div className="flex items-center gap-1 text-noop-subtle text-xs mb-1">
            <Wifi className="w-3.5 h-3.5 text-noop-cyan" />
            <span>Target Strap</span>
          </div>
          <div className="text-sm font-bold text-white truncate" title={status.device_id}>
            {status.device_id}
          </div>
        </div>

        {/* Battery */}
        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-3">
          <div className="flex items-center gap-1 text-noop-subtle text-xs mb-1">
            {status.is_charging ? (
              <BatteryCharging className="w-3.5 h-3.5 text-noop-green" />
            ) : (
              <Battery className="w-3.5 h-3.5 text-noop-cyan" />
            )}
            <span>Battery</span>
          </div>
          <div className="text-sm font-bold text-white">
            {status.battery_percentage !== undefined && status.battery_percentage !== null
              ? `${Math.round(status.battery_percentage)}%`
              : "--"}
            {status.is_charging && <span className="text-xs text-noop-green ml-1">⚡</span>}
          </div>
        </div>

        {/* Local Queue Backlog */}
        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-3">
          <div className="flex items-center gap-1 text-noop-subtle text-xs mb-1">
            <Database className="w-3.5 h-3.5 text-noop-yellow" />
            <span>Local Queue</span>
          </div>
          <div className="text-sm font-bold text-white">
            {status.queued_records}{" "}
            <span className="text-[10px] font-normal text-noop-subtle">pending</span>
          </div>
        </div>

        {/* Last Sync */}
        <div className="bg-noop-bg/60 border border-noop-border/40 rounded-xl p-3">
          <div className="flex items-center gap-1 text-noop-subtle text-xs mb-1">
            <Clock className="w-3.5 h-3.5 text-noop-indigo" />
            <span>Last Sync</span>
          </div>
          <div className="text-sm font-bold text-white">{lastSyncStr}</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-[11px] text-noop-subtle mt-4 pt-3 border-t border-noop-border/40">
        <span className="flex items-center gap-1 text-noop-green">
          <Shield className="w-3 h-3" /> Encrypted via Tailscale Serve
        </span>
        <span>NOOP Collector Agent v{status.agent_version}</span>
      </div>
    </div>
  );
};
