import { useEffect, useState, useRef, useCallback } from "react";
import {
  Activity,
  AlertCircle,
  Dumbbell,
  Flame,
  Heart,
  Laptop,
  Moon,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { api, setUnauthorizedHandler } from "./api/client";
import { AmbientSky } from "./components/AmbientSky";
import { AuthModal } from "./components/AuthModal";
import { CollectorStatusCard } from "./components/CollectorStatus";
import { Header } from "./components/Header";
import { HeartRateChart } from "./components/HeartRateChart";
import { LiveHeartRate } from "./components/LiveHeartRate";
import { MobileBottomNav, TabId } from "./components/MobileBottomNav";
import { RecoveryGauge } from "./components/RecoveryGauge";
import { SleepBreakdown } from "./components/SleepBreakdown";
import { StrainMeter } from "./components/StrainMeter";
import { WorkoutsList } from "./components/WorkoutsList";
import { useLiveStream } from "./hooks/useLiveStream";
import {
  CollectorStatus,
  DashboardSummary,
  Device,
  HeartRateSample,
  Workout,
} from "./types";

export function App() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [heartRates, setHeartRates] = useState<HeartRateSample[]>([]);
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [collectorStatus, setCollectorStatus] = useState<CollectorStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);

  // Live WebSocket stream
  const liveStream = useLiveStream();

  useEffect(() => {
    // If backend returns 401, trigger the auth modal
    setUnauthorizedHandler(() => {
      setIsAuthModalOpen(true);
      setErrorMsg("Dashboard authentication required. Please enter your session token.");
    });
  }, []);

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setIsLoading(true);
    setErrorMsg(null);
    try {
      // 1. Fetch devices
      const devs = await api.getDevices().catch(() => []);
      setDevices(devs);

      // 2. Fetch summary
      const sum = await api.getSummary(selectedDeviceId || undefined);
      setSummary(sum);

      // 3. Fetch recent heart rate samples for timeline
      const hrSamples = await api.getHeartRate(150).catch(() => []);
      setHeartRates(hrSamples);

      // 4. Fetch workouts
      const wList = await api.getWorkouts(20).catch(() => []);
      setWorkouts(wList);

      // 5. Fetch collector status
      const col = await api.getCollectorStatus().catch(() => null);
      setCollectorStatus(col || sum.collector_status || null);
    } catch (err: any) {
      if (!silent) {
        setErrorMsg(err.message || "Failed to load dashboard data");
      }
    } finally {
      if (!silent) setIsLoading(false);
    }
  }, [selectedDeviceId]);

  useEffect(() => {
    loadData(false);
  }, [selectedDeviceId, loadData]);

  // Active-tab 20-second silent background auto-polling
  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        loadData(true);
      }
    }, 20000);
    return () => clearInterval(interval);
  }, [loadData]);

  return (
    <div className="min-h-screen flex flex-col bg-noop-bg text-noop-text relative selection:bg-noop-cyan/20 selection:text-noop-cyan">
      {/* Dynamic Ambient Sky Atmospheric Lighting */}
      <AmbientSky />

      {/* Top Glass Navigation */}
      <Header
        devices={devices}
        selectedDeviceId={selectedDeviceId}
        onSelectDevice={setSelectedDeviceId}
        liveState={liveStream.connectionState}
        onRefresh={() => loadData(false)}
        isRefreshing={isLoading}
        onOpenAuth={() => setIsAuthModalOpen(true)}
      />

      {/* Main Responsive Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 py-6 space-y-6 z-10 pb-28 md:pb-12">
        {/* Error / Auth Notice */}
        {errorMsg && (
          <div className="bg-noop-red/10 border border-noop-red/30 rounded-2xl p-4 flex items-center justify-between gap-4 backdrop-blur-md">
            <div className="flex items-center gap-3 text-noop-red text-sm font-medium">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="px-3.5 py-1.5 rounded-xl bg-noop-red text-white text-xs font-semibold hover:bg-noop-red/90 transition-colors whitespace-nowrap shadow-sm"
            >
              Configure Token
            </button>
          </div>
        )}

        {/* Desktop Navigation Tabs */}
        <div className="hidden md:flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-white/10">
          {[
            { id: "overview" as TabId, label: "Today Overview", icon: Activity },
            { id: "recovery" as TabId, label: "Recovery", icon: Sparkles },
            { id: "strain" as TabId, label: "Day Strain", icon: Flame },
            { id: "sleep" as TabId, label: "Sleep", icon: Moon },
            { id: "workouts" as TabId, label: "Workouts", icon: Dumbbell },
            { id: "system" as TabId, label: "Hardware & Gateway", icon: Laptop },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold tracking-wide transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-white/10 text-noop-cyan border border-white/15 shadow-glowCyan backdrop-blur-lg"
                    : "text-noop-muted hover:text-white hover:bg-white/5"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-noop-cyan" : "text-noop-subtle"}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab 1: Overview Screen */}
        {activeTab === "overview" && (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Primary Triad Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Recovery */}
              <RecoveryGauge recovery={summary?.latest_recovery} />

              {/* Day Strain */}
              <StrainMeter strain={summary?.latest_strain} />

              {/* Live Heart Rate & Real-Time Pulse */}
              <LiveHeartRate
                bpm={liveStream.latestBpm || summary?.latest_heart_rate?.bpm || null}
                history={liveStream.bpmHistory}
                liveState={liveStream.connectionState}
                batteryLevel={liveStream.batteryLevel ?? collectorStatus?.battery_percentage}
                isCharging={liveStream.isCharging ?? collectorStatus?.is_charging}
                lastTimestamp={liveStream.latestTimestamp || summary?.latest_heart_rate?.timestamp}
              />
            </div>

            {/* Second Row: Sleep & Recent Heart Rate Trace */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SleepBreakdown sleep={summary?.latest_sleep} />
              <HeartRateChart samples={heartRates} />
            </div>

            {/* Third Row: Workouts & System Gateway */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <WorkoutsList workouts={workouts} />
              <CollectorStatusCard status={collectorStatus || undefined} />
            </div>
          </div>
        )}

        {/* Tab 2: Recovery Detail */}
        {activeTab === "recovery" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in duration-300">
            <RecoveryGauge recovery={summary?.latest_recovery} />
            <HeartRateChart samples={heartRates} />
          </div>
        )}

        {/* Tab 3: Strain Detail */}
        {activeTab === "strain" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in duration-300">
            <StrainMeter strain={summary?.latest_strain} />
            <WorkoutsList workouts={workouts} />
          </div>
        )}

        {/* Tab 4: Sleep Architecture */}
        {activeTab === "sleep" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in duration-300">
            <SleepBreakdown sleep={summary?.latest_sleep} />
            <HeartRateChart samples={heartRates} />
          </div>
        )}

        {/* Tab 5: Workouts */}
        {activeTab === "workouts" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in duration-300">
            <WorkoutsList workouts={workouts} />
            <StrainMeter strain={summary?.latest_strain} />
          </div>
        )}

        {/* Tab 6: Hardware & Gateway */}
        {activeTab === "system" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in duration-300">
            <CollectorStatusCard status={collectorStatus || undefined} />
            <LiveHeartRate
              bpm={liveStream.latestBpm || summary?.latest_heart_rate?.bpm || null}
              history={liveStream.bpmHistory}
              liveState={liveStream.connectionState}
              batteryLevel={liveStream.batteryLevel ?? collectorStatus?.battery_percentage}
              isCharging={liveStream.isCharging ?? collectorStatus?.is_charging}
              lastTimestamp={liveStream.latestTimestamp || summary?.latest_heart_rate?.timestamp}
            />
          </div>
        )}
      </main>

      {/* Floating Mobile Bottom Navigation Bar (< 768px) */}
      <MobileBottomNav activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* Footer */}
      <footer className="border-t border-white/5 py-6 text-center text-xs text-noop-subtle z-10 hidden md:block">
        <p>NOOP Home Lab • Self-Hosted WHOOP 4.0 Platform • Zero Cloud Dependencies</p>
      </footer>

      {/* Auth / Settings Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSaved={() => loadData(false)}
      />
    </div>
  );
}
