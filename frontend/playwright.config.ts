import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8011",
    headless: true,
    channel: process.env.CI ? undefined : "chrome",
    screenshot: "only-on-failure",
  },
  webServer: {
    command:
      "../.venv/bin/uvicorn tests.e2e_server:app --app-dir ../backend --host 127.0.0.1 --port 8011",
    url: "http://127.0.0.1:8011/api/health",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
