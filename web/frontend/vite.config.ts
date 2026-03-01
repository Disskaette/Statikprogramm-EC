import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // plotly.js-dist-min is a CommonJS bundle without an ES default export.
  // Tell Vite / Rollup to treat it as CJS so the default import works correctly.
  optimizeDeps: {
    include: ["plotly.js-dist-min"],
  },
  build: {
    commonjsOptions: {
      include: [/plotly\.js-dist-min/, /node_modules/],
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
