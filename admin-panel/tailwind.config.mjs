/** @type {import('tailwindcss').Config} */
const config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        page:  "#0d0d0f",
        card:  "#17171a",
        card2: "#1e1e22",
        rim:   "#26262b",
        ink:   "#f2f2f3",
        dim:   "#9a9aa0",
        ac:    "#1d9e75",
        "ac-h":"#17876a",
      },
    },
  },
  plugins: [],
};

export default config;
