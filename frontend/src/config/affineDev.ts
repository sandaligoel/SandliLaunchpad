import {
  AFFINE_API_PORT,
  AFFINE_API_TARGET,
  UI_DEV_URL,
} from "@/config/ports";

export const AFFINE_DEV_PORT = String(AFFINE_API_PORT);
export const AFFINE_DEV_TARGET = AFFINE_API_TARGET;

export const AFFINE_START_CMD = "./scripts/start-backend.sh";

export const AFFINE_ENV_LOCAL_LINE = `AFFINE_API_TARGET=${AFFINE_API_TARGET}`;

export const AFFINE_DEV_UI_URL = UI_DEV_URL;
