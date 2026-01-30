import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        "ai-accent": "hsl(var(--ai-accent))",
      },
      boxShadow: {
        "glow": "0 0 24px -4px hsl(var(--primary) / 0.3), 0 0 48px -8px hsl(var(--ai-accent) / 0.2)",
        "glow-lg": "0 0 40px -8px hsl(var(--primary) / 0.35), 0 0 80px -16px hsl(var(--ai-accent) / 0.2)",
        "card": "0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)",
        "card-hover": "0 20px 25px -5px rgb(0 0 0 / 0.08), 0 8px 10px -6px rgb(0 0 0 / 0.05), 0 0 0 1px hsl(var(--primary) / 0.08)",
      },
      fontFamily: {
        heading: ["var(--font-heading)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "monospace"],
      },
      fontSize: {
        "fluid-xs": ["clamp(0.75rem, 2vw, 0.8125rem)", { lineHeight: "1.4" }],
        "fluid-sm": ["clamp(0.875rem, 2.2vw, 0.9375rem)", { lineHeight: "1.45" }],
        "fluid-base": ["clamp(1rem, 2.5vw, 1.0625rem)", { lineHeight: "1.5" }],
        "fluid-lg": ["clamp(1.125rem, 2.8vw, 1.25rem)", { lineHeight: "1.4" }],
        "fluid-xl": ["clamp(1.25rem, 3.5vw, 1.5rem)", { lineHeight: "1.3" }],
        "fluid-2xl": ["clamp(1.5rem, 4vw, 2rem)", { lineHeight: "1.25" }],
        "fluid-3xl": ["clamp(1.875rem, 5vw, 2.5rem)", { lineHeight: "1.2" }],
        "fluid-4xl": ["clamp(2.25rem, 6vw, 3.5rem)", { lineHeight: "1.15" }],
        "fluid-5xl": ["clamp(2.5rem, 7vw, 4rem)", { lineHeight: "1.1" }],
      },
      animation: {
        "fade-in": "fadeIn 0.35s ease-out",
        "slide-up": "slideUp 0.35s ease-out",
        "scale-in": "scaleIn 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
      },
      container: {
        center: true,
        padding: { DEFAULT: "1rem", sm: "1.5rem", lg: "2rem" },
      },
    },
  },
  plugins: [],
};
export default config;
