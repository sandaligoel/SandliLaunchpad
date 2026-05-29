import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import devPorts from "../config/dev-ports.json";

const apiTarget = `http://${devPorts.host}:${devPorts.affineApiPort}`;

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "/static/architecture/" : "/",
  build: {
    outDir: path.resolve(__dirname, "../backend/api/static/architecture"),
    emptyOutDir: true,
    assetsDir: "assets",
    rollupOptions: {
      output: {
        entryFileNames: "assets/index.js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
  server: {
    port: devPorts.uiPort,
    strictPort: false,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true, timeout: 120_000 },
      "/health": { target: apiTarget, changeOrigin: true },
      "/ui": { target: apiTarget, changeOrigin: true },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
