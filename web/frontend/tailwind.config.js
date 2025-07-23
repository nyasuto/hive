/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        hive: {
          primary: '#F59E0B',     // Amber-500 (bee theme)
          secondary: '#EF4444',   // Red-500
          success: '#10B981',     // Emerald-500
          warning: '#F59E0B',     // Amber-500
          danger: '#EF4444',      // Red-500
          info: '#3B82F6',        // Blue-500
          dark: '#1F2937',        // Gray-800
          light: '#F9FAFB',       // Gray-50
        },
        agent: {
          queen: '#8B5CF6',       // Violet-500
          developer: '#10B981',   // Emerald-500
          qa: '#F59E0B',          // Amber-500
          analyst: '#3B82F6',     // Blue-500
        },
        status: {
          idle: '#6B7280',        // Gray-500
          busy: '#F59E0B',        // Amber-500
          waiting: '#3B82F6',     // Blue-500
          offline: '#9CA3AF',     // Gray-400
          error: '#EF4444',       // Red-500
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      },
      fontFamily: {
        'mono': ['Monaco', 'Menlo', 'Ubuntu Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}