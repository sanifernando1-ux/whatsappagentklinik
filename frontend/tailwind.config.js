/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        kf: {
          blue: "#0B6FB8",
          blueDark: "#075291",
          blueLight: "#E7F1FA",
          orange: "#F58220",
          orangeDark: "#D96F10",
          ink: "#0F2033",
          panel: "#F4F7FA",
        },
      },
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(15,32,51,0.06), 0 1px 2px rgba(15,32,51,0.04)",
      },
    },
  },
  plugins: [],
};
