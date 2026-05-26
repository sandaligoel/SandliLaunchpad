import { defineConfig, loadEnv } from "vite";
import { cloudflare } from "@cloudflare/vite-plugin";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const affineTarget =
    env.AFFINE_API_TARGET?.trim() || "http://127.0.0.1:8003";
  const mockTarget =
    env.VITE_MOCK_API_TARGET?.trim() || "http://127.0.0.1:3001";

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
      port: 5173,
      proxy: {
        // AFFINE agent_catalog — must match uvicorn port (see AFFINE_API_TARGET)
        "/api/catalog": {
          target: affineTarget,
          changeOrigin: true,
        },
        "/api/sessions": {
          target: affineTarget,
          changeOrigin: true,
          timeout: 120_000,
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
