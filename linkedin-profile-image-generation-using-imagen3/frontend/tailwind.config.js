/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        'custom-gray': '#DDE6F6',
        'light-gray': '#e0e0e0',
        'lighter-gray': '#f0f0f0',
      },
    },
  },
  plugins: [],
};
