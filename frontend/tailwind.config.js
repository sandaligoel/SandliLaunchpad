/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#060a10",
        panel: "#0f141c",
        border: "#1e2a3a",
        accent: "#3b82f6",
        reuse: "#22c55e",
        adapt: "#14b8a6",
        build: "#6366f1",
        hitl: "#f97316",
        merge: "#a855f7",
        input: "#64748b",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(59, 130, 246, 0.35)",
        "glow-green": "0 0 20px rgba(34, 197, 94, 0.3)",
        glass: "0 8px 32px rgba(0, 0, 0, 0.45)",
      },
      animation: {
        "flow-dash": "flow-dash 1.2s linear infinite",
        "pulse-ring": "pulse-ring 2s ease-out infinite",
      },
      keyframes: {
        "flow-dash": {
          to: { strokeDashoffset: "-24" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.95)", opacity: 0.6 },
          "70%": { transform: "scale(1.08)", opacity: 0 },
          "100%": { transform: "scale(1.08)", opacity: 0 },
        },
      },
    },
  },
  plugins: [],
};
