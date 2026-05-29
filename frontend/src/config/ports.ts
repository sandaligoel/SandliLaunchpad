/**
 * Dev API targets — synced from config/runtime-ports.json via scripts/sync-dev-env.sh
 */
import devPorts from "../../../config/dev-ports.json";

function targetFromEnv(name: string, fallback: string): string {
  const v = import.meta.env[name];
  return typeof v === "string" && v.trim() ? v.trim() : fallback;
}

const defaultAffine = `http://${devPorts.host}:${devPorts.affineApiPort}`;

export const AFFINE_API_TARGET = targetFromEnv(
  "VITE_AFFINE_API_TARGET",
  targetFromEnv("AFFINE_API_TARGET", defaultAffine),
);

export const UI_PORT = Number(import.meta.env.VITE_UI_PORT) || devPorts.uiPort;

function portFromTarget(target: string, fallback: number): number {
  try {
    return Number(new URL(target).port) || fallback;
  } catch {
    return fallback;
  }
}

export const AFFINE_API_PORT = portFromTarget(
  AFFINE_API_TARGET,
  devPorts.affineApiPort,
);

export const UI_DEV_URL = `http://localhost:${UI_PORT}`;
