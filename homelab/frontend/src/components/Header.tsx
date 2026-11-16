import React from "react";
import { Activity, Key, RefreshCw, Shield, Smartphone, Wifi, WifiOff } from "lucide-react";
import { Device } from "../types";

interface HeaderProps {
  devices: Device[];
  selectedDeviceId: string;
  onSelectDevice: (id: string) => void;
  liveState: "connected" | "connecting" | "disconnected";
  onRefresh: () => void;
  isRefreshing: boolean;
  onOpenAuth: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  devices,
  selectedDeviceId,
  onSelectDevice,
  liveState,
  onRefresh,
  isRefreshing,
  onOpenAuth,
}) => {
  return (
    <header className="border-b border-noop-border bg-noop-card/80 backdrop-blur-md sticky top-0 z-40 px-4 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
      {/* Brand & Platform */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-noop-cyan/20 to-noop-cyan/5 border border-noop-cyan/30 flex items-center justify-center text-noop-cyan shadow-sm shadow-noop-cyan/10">
          <Activity className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-white">NOOP Home Lab</h1>
            <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-noop-cyan/10 text-noop-cyan border border-noop-cyan/20">
              WHOOP 4.0
            </span>
          </div>
          <p className="text-xs text-noop-subtle flex items-center gap-1.5">
            <Shield className="w-3 h-3 text-noop-green" />
            Offline-by-default on-device telemetry
          </p>
        </div>
      </div>

      {/* Middle: Device selector and live indicator */}
      <div className="flex items-center gap-3">
        {/* Live WS Pill */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-noop-bg border border-noop-border text-xs font-medium">
          {liveState === "connected" ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-noop-green opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-noop-green"></span>
              </span>
              <span className="text-noop-green font-semibold">LIVE</span>
            </>
          ) : liveState === "connecting" ? (
            <>
              <Wifi className="w-3 h-3 text-noop-yellow animate-spin" />
              <span className="text-noop-yellow">Connecting</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3 h-3 text-noop-subtle" />
              <span className="text-noop-subtle">Disconnected</span>
            </>
          )}
        </div>

        {/* Device selector */}
        {devices.length > 0 && (
          <div className="flex items-center gap-1.5 bg-noop-bg border border-noop-border rounded-lg px-2.5 py-1 text-xs">
            <Smartphone className="w-3.5 h-3.5 text-noop-subtle" />
            <select
              value={selectedDeviceId}
              onChange={(e) => onSelectDevice(e.target.value)}
              className="bg-transparent text-white outline-none cursor-pointer pr-1"
            >
              <option value="" className="bg-noop-card text-white">All Devices</option>
              {devices.map((d) => (
                <option key={d.device_id} value={d.device_id} className="bg-noop-card text-white">
                  {d.name || d.device_id}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh Dashboard Data"
          className="p-2 rounded-lg bg-noop-bg hover:bg-noop-card border border-noop-border text-noop-muted hover:text-white transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-noop-cyan" : ""}`} />
        </button>

        <button
          onClick={onOpenAuth}
          title="Dashboard Token Settings"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-noop-bg hover:bg-noop-card border border-noop-border text-xs text-noop-muted hover:text-white transition-colors"
        >
          <Key className="w-3.5 h-3.5 text-noop-cyan" />
          <span className="hidden sm:inline">Auth Token</span>
        </button>
      </div>
    </header>
  );
};
