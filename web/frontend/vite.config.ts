import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  // Base URL for asset paths in the production build.
  // Set VITE_BASE_URL=/statik/ when building for the stark-tools portal
  // so that nginx can proxy /statik/ → FastAPI at root (prefix-stripping via
  // trailing slash in proxy_pass). Falls back to "/" for local development.
  base: process.env.VITE_BASE_URL ?? "/",
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
