/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Betfair design system colors
        'betfair-gold': '#FFB80C',
        'dark-navy': '#1E1E2D',
        'back-blue': '#72BBEF',
        'lay-pink': '#FAA9BA',
        'success': '#22C55E',
        'error': '#EF4444',
        'ai-accent': '#7C3AED',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
