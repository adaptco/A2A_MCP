export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        neon: {
          teal: '#00eaff',
          purple: '#bc13fe',
          dark: '#001018',
        },
        backdrop: 'rgba(0, 20, 30, 0.6)',
      },
    },
  },
  plugins: [],
}
