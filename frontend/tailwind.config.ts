import type { Config } from "tailwindcss";

// Tokens copiés de ../DESIGN.md — sous-ensemble utilisé par la démo (doc 17
// §9 semaine 2). Ne pas diverger des valeurs de DESIGN.md sans mettre à
// jour les deux ; DESIGN.md fait foi en cas de conflit (doc 11 §0).
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#2563EB",
        "primary-bright": "#3B82F6",
        "primary-deep": "#1D4ED8",
        "primary-subtle": "#EFF6FF",
        ink: "#0F172A",
        body: "#1E293B",
        subtle: "#475569",
        muted: "#94A3B8",
        faint: "#CBD5E1",
        "canvas-app": "#F8FAFC",
        canvas: "#FFFFFF",
        "surface-soft": "#F1F5F9",
        "surface-dark": "#0F172A",
        border: "#E2E8F0",
        "border-strong": "#CBD5E1",
        success: "#16A34A",
        "success-subtle": "#F0FDF4",
        warning: "#D97706",
        "warning-subtle": "#FFFBEB",
        danger: "#DC2626",
        "danger-subtle": "#FEF2F2",
        "amount-positive": "#16A34A",
        "amount-negative": "#DC2626",
        validated: "#16A34A",
        "validated-subtle": "#F0FDF4",
        pending: "#D97706",
        "pending-subtle": "#FFFBEB",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xs: "4px",
        sm: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
      },
    },
  },
  plugins: [],
};

export default config;
