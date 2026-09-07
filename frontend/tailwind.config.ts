import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: { extend: {
    colors: { ink: "var(--ink)", paper: "var(--paper)", canvas: "var(--canvas)", muted: "var(--muted)", line: "var(--line)", olive: "var(--olive)" },
    fontFamily: { sans: ["var(--font-sans)", "Arial", "sans-serif"], display: ["var(--font-display)", "Georgia", "serif"] },
    boxShadow: { soft: "0 18px 55px rgba(30, 28, 24, 0.08)" }
  } }, plugins: []
};
export default config;
