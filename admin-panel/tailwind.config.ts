import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#2563eb", hover: "#1d4ed8" },
      },
    },
  },
  plugins: [],
};

export default config;
