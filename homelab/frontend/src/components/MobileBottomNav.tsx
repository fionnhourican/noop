import React from "react";
import { Activity, Dumbbell, Flame, Laptop, Moon, Sparkles, TrendingUp } from "lucide-react";

export type TabId = "overview" | "recovery" | "strain" | "sleep" | "workouts" | "system";

interface MobileBottomNavProps {
  activeTab: TabId;
  onSelectTab: (tab: TabId) => void;
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({ activeTab, onSelectTab }) => {
  const tabs = [
    { id: "overview" as TabId, label: "Today", icon: Activity },
    { id: "recovery" as TabId, label: "Recovery", icon: Sparkles },
    { id: "strain" as TabId, label: "Strain", icon: Flame },
    { id: "sleep" as TabId, label: "Sleep", icon: Moon },
    { id: "system" as TabId, label: "Gateway", icon: Laptop },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 px-3 pb-safe pt-2 bg-noop-bg/85 backdrop-blur-2xl border-t border-white/10 shadow-2xl">
      <div className="flex items-center justify-around max-w-md mx-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              className={`flex flex-col items-center justify-center py-1.5 px-3 rounded-xl transition-all relative ${
                isActive
                  ? "text-noop-cyan"
                  : "text-noop-subtle hover:text-white active:scale-95"
              }`}
            >
              {isActive && (
                <span className="absolute -top-1 w-6 h-1 rounded-full bg-noop-cyan shadow-glowCyan" />
              )}
              <Icon className={`w-5 h-5 transition-transform ${isActive ? "scale-110" : ""}`} />
              <span className={`text-[10px] mt-1 font-semibold tracking-tight ${isActive ? "text-white" : ""}`}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
