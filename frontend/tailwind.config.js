/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Betfair brand colors
        'betfair-yellow': '#FFB80C',
        'betfair-gold': '#FFB80C',
        'betfair-black': '#1E1E1E',
        'betfair-dark': '#303030',
        'betfair-gray': '#666666',
        'betfair-light': '#F5F5F5',
        // Exchange colors
        'back-blue': '#A6D8FF',
        'back-blue-deep': '#72BBEF',
        'lay-pink': '#FAC9D1',
        'lay-pink-deep': '#F694AA',
        // UI colors
        'dark-navy': '#1E1E2D',
        'success': '#22C55E',
        'error': '#EF4444',
        'ai-accent': '#7C3AED',
        // Table colors
        'row-even': '#FFFFFF',
        'row-odd': '#F7F7F7',
        'header-bg': '#EBEBEB',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
