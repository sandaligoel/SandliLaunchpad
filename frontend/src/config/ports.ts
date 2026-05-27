import devPorts from "../../../config/dev-ports.json";

export const DEV_HOST = devPorts.host;
export const AFFINE_API_PORT = devPorts.affineApiPort;
export const MOCK_API_PORT = devPorts.mockApiPort;
export const UI_DEV_PORT = devPorts.uiPort;

export const AFFINE_API_TARGET = `http://${DEV_HOST}:${AFFINE_API_PORT}`;
export const MOCK_API_TARGET = `http://${DEV_HOST}:${MOCK_API_PORT}`;
export const UI_DEV_URL = `http://localhost:${UI_DEV_PORT}`;
