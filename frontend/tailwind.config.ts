import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand colors - customizable per tenant
        brand: {
          50: "var(--color-brand-50, #eff6ff)",
          100: "var(--color-brand-100, #dbeafe)",
          200: "var(--color-brand-200, #bfdbfe)",
          300: "var(--color-brand-300, #93c5fd)",
          400: "var(--color-brand-400, #60a5fa)",
          500: "var(--color-brand-500, #3b82f6)",
          600: "var(--color-brand-600, #2563eb)",
          700: "var(--color-brand-700, #1d4ed8)",
          800: "var(--color-brand-800, #1e40af)",
          900: "var(--color-brand-900, #1e3a8a)",
        },
        // Semantic colors
        surface: {
          DEFAULT: "var(--color-surface, #ffffff)",
          secondary: "var(--color-surface-secondary, #f9fafb)",
          tertiary: "var(--color-surface-tertiary, #f3f4f6)",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-in-out",
        "slide-up": "slideUp 0.3s ease-out",
        "pulse-dot": "pulseDot 1.5s infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
