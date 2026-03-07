/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#E8F3FF',
          500: '#165DFF',
        },
        success: {
          500: '#00B42A',
        },
        warning: {
          500: '#FF7D00',
        },
        danger: {
          500: '#F53F3F',
        },
        text: {
          primary: '#333333',
          secondary: '#666666',
          tertiary: '#999999',
        },
        bg: {
          primary: '#FFFFFF',
          secondary: '#F5F7FA',
        }
      },
      boxShadow: {
        sm: '0 2px 8px rgba(0, 0, 0, 0.06)',
        md: '0 4px 16px rgba(0, 0, 0, 0.08)',
      }
    },
  },
  plugins: [],
}