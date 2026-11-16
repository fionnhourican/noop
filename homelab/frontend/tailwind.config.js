/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        noop: {
          bg: "#090a0f",
          card: "#12151e",
          cardHover: "#181b26",
          border: "#1f2433",
          borderSubtle: "#171a24",
          text: "#f8fafc",
          muted: "#94a3b8",
          subtle: "#64748b",
          cyan: "#00F0FF",
          green: "#00E676",
          yellow: "#FFD600",
          red: "#FF1744",
          indigo: "#6366f1",
          purple: "#a855f7",
          blue: "#3b82f6",
          amber: "#f59e0b",
        },
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
        glowCyan: "0 0 25px -4px rgba(0, 240, 255, 0.35)",
        glowGreen: "0 0 25px -4px rgba(0, 230, 118, 0.35)",
        glowYellow: "0 0 25px -4px rgba(255, 214, 0, 0.35)",
        glowRed: "0 0 25px -4px rgba(255, 23, 68, 0.35)",
        innerGlow: "inset 0 1px 1px 0 rgba(255, 255, 255, 0.08)",
      },
      animation: {
        pulseFast: "pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        heartbeat: "heartbeat 1.2s ease-in-out infinite",
        shimmer: "shimmer 3s infinite linear",
        breath: "breath 3s ease-in-out infinite",
      },
      keyframes: {
        heartbeat: {
          "0%, 100%": { transform: "scale(1)" },
          "14%": { transform: "scale(1.15)" },
          "28%": { transform: "scale(1)" },
          "42%": { transform: "scale(1.15)" },
          "70%": { transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        breath: {
          "0%, 100%": { opacity: "0.6", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.08)" },
        },
      },
    },
  },
  plugins: [],
};
