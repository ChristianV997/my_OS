/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#111113",
        "surface-raised": "#18181b",
        "surface-overlay": "#1e1e21",
      },
      fontFamily: {
        mono: ["ui-monospace", "SF Mono", "Menlo", "Consolas", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};
