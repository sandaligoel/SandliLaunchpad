import { defineConfig, loadEnv } from "vite";
import { cloudflare } from "@cloudflare/vite-plugin";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";
import devPorts from "../config/dev-ports.json";

const defaultAffineTarget = `http://${devPorts.host}:${devPorts.affineApiPort}`;
const defaultMockTarget = `http://${devPorts.host}:${devPorts.mockApiPort}`;

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const affineTarget = env.AFFINE_API_TARGET?.trim() || defaultAffineTarget;
  const mockTarget = env.VITE_MOCK_API_TARGET?.trim() || defaultMockTarget;

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
      port: devPorts.uiPort,
      strictPort: true,
      proxy: {
        // AFFINE backend — port from config/dev-ports.json
        "/api/catalog": {
          target: affineTarget,
          changeOrigin: true,
        },
        "/api/sessions": {
          target: affineTarget,
          changeOrigin: true,
          timeout: 120_000,
        },
        // Launchpad saved workflows (mock API also has /api/workflows for dashboard)
        "/api/launchpad": {
          target: affineTarget,
          changeOrigin: true,
        },
        "/health": {
          target: affineTarget,
          changeOrigin: true,
        },
        // AgentForge mock API (dashboard, workflows, agents, runs, …)
        "/api": {
          target: mockTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
