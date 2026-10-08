import { defineConfig, devices } from '@playwright/test'

const python = process.platform === 'win32' ? '..\\.venv\\Scripts\\python.exe' : '../.venv/bin/python'
const apiPort = Number(process.env.SCOUT_E2E_API_PORT) || 8000
const webPort = Number(process.env.SCOUT_E2E_WEB_PORT) || 5173
export default defineConfig({
  testDir: './e2e', timeout: 90000, expect: { timeout: 15000 }, workers: 1,
  use: { baseURL: `http://127.0.0.1:${webPort}`, trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } },
  ],
  webServer: [
    { command: `${python} -m uvicorn scout.api:app --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/health/live`, timeout: 60000, reuseExistingServer: !process.env.CI,
      env: { SCOUT_DATABASE_URL: process.env.SCOUT_E2E_DATABASE_URL || 'sqlite:///../data/scout.db', SCOUT_ALLOW_SYNTHETIC: 'true', SCOUT_SERVE_PRIVATE_EVIDENCE: 'false' } },
    { command: `npm run dev -- --port ${webPort} --strictPort`, url: `http://127.0.0.1:${webPort}`, timeout: 60000,
      env: { SCOUT_DEV_API_PORT: String(apiPort) },
      reuseExistingServer: !process.env.CI },
  ],
})
