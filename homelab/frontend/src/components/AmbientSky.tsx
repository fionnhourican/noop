import React, { useEffect, useState } from "react";

export const AmbientSky: React.FC = () => {
  const [hour, setHour] = useState<number>(() => new Date().getHours());

  useEffect(() => {
    const timer = setInterval(() => {
      setHour(new Date().getHours());
    }, 60000);
    return () => clearInterval(timer);
  }, []);

  // Determine time-of-day sky theme
  const getAtmosphere = () => {
    if (hour >= 5 && hour < 8) {
      // Dawn / Sunrise
      return {
        label: "Dawn",
        glowPrimary: "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(245, 158, 11, 0.12), transparent 70%)",
        glowSecondary: "radial-gradient(circle at 10% 20%, rgba(244, 63, 94, 0.08), transparent 50%)",
        accent: "rgba(251, 146, 60, 0.05)",
      };
    } else if (hour >= 8 && hour < 18) {
      // Daytime Solar
      return {
        label: "Day",
        glowPrimary: "radial-gradient(ellipse 90% 60% at 50% -15%, rgba(0, 240, 255, 0.10), transparent 75%)",
        glowSecondary: "radial-gradient(circle at 90% 15%, rgba(59, 130, 246, 0.08), transparent 60%)",
        accent: "rgba(0, 240, 255, 0.04)",
      };
    } else if (hour >= 18 && hour < 21) {
      // Dusk / Sunset
      return {
        label: "Dusk",
        glowPrimary: "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(168, 85, 247, 0.12), transparent 70%)",
        glowSecondary: "radial-gradient(circle at 20% 15%, rgba(249, 115, 22, 0.08), transparent 50%)",
        accent: "rgba(168, 85, 247, 0.05)",
      };
    } else {
      // Night / Deep Space
      return {
        label: "Night",
        glowPrimary: "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(0, 230, 118, 0.06), transparent 70%)",
        glowSecondary: "radial-gradient(circle at 85% 20%, rgba(99, 102, 241, 0.08), transparent 60%)",
        accent: "rgba(0, 240, 255, 0.03)",
      };
    }
  };

  const atmosphere = getAtmosphere();

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden transition-all duration-1000"
    >
      {/* Primary Atmospheric Glow */}
      <div
        className="absolute inset-0 transition-all duration-1000 opacity-90"
        style={{ backgroundImage: atmosphere.glowPrimary }}
      />

      {/* Secondary Dynamic Accent */}
      <div
        className="absolute inset-0 transition-all duration-1000 opacity-80"
        style={{ backgroundImage: atmosphere.glowSecondary }}
      />

      {/* Subtle Mesh Grid */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
    </div>
  );
};
