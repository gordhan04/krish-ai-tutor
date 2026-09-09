/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7cc5fb',
          400: '#38a5f6',
          500: '#0e87e9',
          600: '#026bc7',
          700: '#0355a1',
          800: '#074884',
          900: '#0c3c6e',
        },
        tutor: {
          bg: '#f8fafc',
          card: '#ffffff',
          accent: '#4f46e5',
          gold: '#f59e0b',
          success: '#10b981',
          error: '#ef4444',
        }
      },
    },
  },
  plugins: [],
};
