import { defineConfig } from "@playwright/test";

// Browser tests get their own backend on a fresh copy of the seeded scenario, with the
// copilot switched off, and their own Vite server pointing at it. Nothing touches the
// committed database or the developer's running servers.
const API_PORT = 8010;
const WEB_PORT = 5180;
const DB = "/tmp/datalens-e2e.db";

export default defineConfig({
  testDir: "e2e",
  testMatch: "*.spec.ts",
  timeout: 300_000,
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: `http://localhost:${WEB_PORT}` },
  webServer: [
    {
      command:
        `cp ../backend/data/scenario.db ${DB} && cd ../backend && ` +
        `DATABASE_URL=sqlite:///${DB} DATALENS_MEDIA_DIR=/tmp/datalens-e2e-media DATALENS_LIVE_WEATHER=0 DATALENS_AI=0 ` +
        `uv run uvicorn app.main:app --port ${API_PORT}`,
      url: `http://localhost:${API_PORT}/api/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `DATALENS_API=http://localhost:${API_PORT} npx vite --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
