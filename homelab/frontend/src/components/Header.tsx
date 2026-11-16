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
    <header className="border-b border-white/10 bg-noop-bg/80 backdrop-blur-2xl sticky top-0 z-40 px-4 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4 shadow-glass transition-all">
      {/* Brand & Platform */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-noop-cyan/25 to-noop-cyan/5 border border-noop-cyan/35 flex items-center justify-center text-noop-cyan shadow-glowCyan">
          <Activity className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-extrabold tracking-tight text-white">NOOP Home Lab</h1>
            <span className="text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded-full bg-noop-cyan/15 text-noop-cyan border border-noop-cyan/30 shadow-sm">
              WHOOP 4.0
            </span>
          </div>
          <p className="text-xs text-noop-subtle flex items-center gap-1.5 mt-0.5 font-medium">
            <Shield className="w-3 h-3 text-noop-green" />
            Offline-by-default on-device telemetry
          </p>
        </div>
      </div>

      {/* Middle: Device selector and live indicator */}
      <div className="flex items-center gap-3">
        {/* Live WS Pill */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-semibold shadow-inner">
          {liveState === "connected" ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-noop-green opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-noop-green shadow-glowGreen"></span>
              </span>
              <span className="text-noop-green font-bold tracking-wider text-[11px] uppercase">LIVE</span>
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
          <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-xl px-3 py-1 text-xs shadow-inner">
            <Smartphone className="w-3.5 h-3.5 text-noop-subtle" />
            <select
              value={selectedDeviceId}
              onChange={(e) => onSelectDevice(e.target.value)}
              className="bg-transparent text-white outline-none cursor-pointer pr-1 font-medium"
            >
              <option value="" className="bg-noop-card text-white">All Straps</option>
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
          className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 active:scale-95 border border-white/10 text-noop-muted hover:text-white transition-all shadow-inner"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-noop-cyan" : ""}`} />
        </button>

        <button
          onClick={onOpenAuth}
          title="Dashboard Token Settings"
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 active:scale-95 border border-white/10 text-xs font-semibold text-noop-muted hover:text-white transition-all shadow-inner"
        >
          <Key className="w-3.5 h-3.5 text-noop-cyan" />
          <span className="hidden sm:inline">Auth Token</span>
        </button>
      </div>
    </header>
  );
};
