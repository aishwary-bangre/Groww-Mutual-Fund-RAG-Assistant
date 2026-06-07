/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#00D09C", // Groww official green
        "primary-hover": "#2fe0aa",
        background: "#0f131c", // Base canvas background
        "surface-elevated": "#111827", // Sidebar surface
        "surface-container": "#1c1f29", // Bubble base
        "surface-card": "#1f2937", // Interactive cards
        "glass-border": "rgba(255, 255, 255, 0.1)",
        "text-primary": "#F3F4F6",
        "text-secondary": "#9CA3AF",
        "accent-glow": "rgba(0, 208, 156, 0.3)",
        "accent-secondary": "#44edb7" // Accent cyan/green from Luminous design
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        headline: ["Outfit", "sans-serif"]
      },
      boxShadow: {
        glow: "0 0 15px rgba(0, 208, 156, 0.2)",
        btn: "0px 4px 20px rgba(0, 208, 156, 0.4)"
      }
    },
  },
  plugins: [],
}
