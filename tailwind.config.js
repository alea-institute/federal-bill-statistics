/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/*.html.j2",
    "./dist/**/*.{html,js}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Noto Sans', 'sans-serif'],
        mono: ['ui-monospace', 'monospace']
      },
    },
  },
  plugins: [],
}