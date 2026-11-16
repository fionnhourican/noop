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
        },
      },
      animation: {
        pulseFast: "pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        heartbeat: "heartbeat 1.2s ease-in-out infinite",
      },
      keyframes: {
        heartbeat: {
          "0%, 100%": { transform: "scale(1)" },
          "14%": { transform: "scale(1.15)" },
          "28%": { transform: "scale(1)" },
          "42%": { transform: "scale(1.15)" },
          "70%": { transform: "scale(1)" },
        },
      },
    },
  },
  plugins: [],
};
