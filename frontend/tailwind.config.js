/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        pokered: "#e63946",
        pokegold: "#f0a500",
        pokenavy: "#1a1a2e",
        pokecard: "#16213e",
        pokeborder: "#0f3460",
        // Type colours
        type: {
          Normal:   "#A8A878",
          Fire:     "#F08030",
          Water:    "#6890F0",
          Electric: "#F8D030",
          Grass:    "#78C850",
          Ice:      "#98D8D8",
          Fighting: "#C03028",
          Poison:   "#A040A0",
          Ground:   "#E0C068",
          Flying:   "#A890F0",
          Psychic:  "#F85888",
          Bug:      "#A8B820",
          Rock:     "#B8A038",
          Ghost:    "#705898",
          Dragon:   "#7038F8",
          Dark:     "#705848",
          Steel:    "#B8B8D0",
        },
      },
      fontFamily: {
        pixel: ['"Press Start 2P"', "monospace"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        glow: "0 0 12px rgba(230, 57, 70, 0.6)",
        gold: "0 0 12px rgba(240, 165, 0, 0.5)",
      },
    },
  },
  plugins: [],
};
