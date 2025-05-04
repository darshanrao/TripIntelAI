/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#4a90e2",
        secondary: "#50b167",
        accent: "#ffd166",
        background: "#f7f9fc",
        chat: {
          user: "#e1f5fe",
          ai: "#f1f8e9",
        },
      },
      animation: {
        'typing': 'typing 1s infinite',
      },
      keyframes: {
        typing: {
          '0%': { opacity: '.2' },
          '20%': { opacity: '1' },
          '100%': { opacity: '.2' },
        },
      },
    },
  },
  plugins: [],
}; 