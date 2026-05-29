import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import { cloudflare } from "@cloudflare/vite-plugin";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";
import devPorts from "../config/dev-ports.json";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

type PortConfig = {
  host: string;
  affineApiPort: number;
  uiPort: number;
};

function loadMergedPorts(): PortConfig {
  const runtimePath = path.resolve(__dirname, "../config/runtime-ports.json");
  if (fs.existsSync(runtimePath)) {
    const runtime = JSON.parse(fs.readFileSync(runtimePath, "utf8")) as Partial<
      PortConfig
    >;
    return {
      host: runtime.host ?? devPorts.host,
      affineApiPort: runtime.affineApiPort ?? devPorts.affineApiPort,
      uiPort: runtime.uiPort ?? devPorts.uiPort,
    };
  }
  return {
    host: devPorts.host,
    affineApiPort: devPorts.affineApiPort,
    uiPort: devPorts.uiPort,
  };
}

/** Single source of truth: config/runtime-ports.json (written by start-backend / allocate-ports). */
function resolveAffineApiTarget(): string {
  const ports = loadMergedPorts();
  return `http://${ports.host}:${ports.affineApiPort}`;
}

export default defineConfig(() => {
  const ports = loadMergedPorts();
  const affineTarget = resolveAffineApiTarget();

  console.log(`[affine] Vite proxy → ${affineTarget} (from config/runtime-ports.json)`);

  return {
    plugins: [
      cloudflare({ viteEnvironment: { name: "ssr" } }),
      tanstackStart({
        server: { entry: "server" },
      }),
      react(),
      tailwindcss(),
      tsconfigPaths(),
    ],
    server: {
      port: ports.uiPort,
      strictPort: false,
      proxy: {
        "/api": {
          target: affineTarget,
          changeOrigin: true,
          timeout: 120_000,
        },
        "/health": {
          target: affineTarget,
          changeOrigin: true,
          timeout: 120_000,
        },
      },
    },
  };
});
