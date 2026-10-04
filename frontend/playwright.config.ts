import { defineConfig, devices } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const API_PORT = 8000;
const WEB_PORT = 5173;
const runtimeDir = join(tmpdir(), 'paybridge-e2e');
// Tokens exist only in the test environment and are typed into the UI by the tests.
export const TOKENS = { alice: 'customer-alice-e2e-token-0001', bob: 'customer-bob-e2e-token-000001', ops: 'ops-olivia-e2e-token-0000001' };
const authTokens = JSON.stringify({
  [TOKENS.alice]: { subject: 'alice', role: 'CUSTOMER' },
  [TOKENS.bob]: { subject: 'bob', role: 'CUSTOMER' },
  [TOKENS.ops]: { subject: 'olivia', role: 'OPS' },
});
// Optional: use an already-installed Chromium instead of the version Playwright expects.
const executablePath = process.env.PW_CHROMIUM_PATH || undefined;

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: `http://127.0.0.1:${WEB_PORT}`, trace: 'on-first-retry', ...devices['Desktop Chrome'], launchOptions: { executablePath } },
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.02 } },
  projects: [
    // Mocked backend: isolated UI and error-path tests, plus the visual baseline.
    { name: 'mocked', testMatch: /dashboard(\.visual)?\.spec\.ts/ },
    // Real FastAPI + SQLite: proves authentication, API contracts and the proxy actually work.
    { name: 'integration', testMatch: /integration\.spec\.ts/ },
  ],
  webServer: [
    {
      // Fresh database every run; the backend is the real application, not a mock.
      command: `python -c "import shutil;shutil.rmtree(r'${runtimeDir}',ignore_errors=True)" && python -m uvicorn paybridge.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: '..',
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: false,
      env: {
        PAYBRIDGE_ENVIRONMENT: 'dev',
        PAYBRIDGE_DATABASE_PATH: join(runtimeDir, 'e2e.db'),
        PAYBRIDGE_SETTLEMENT_DIR: join(runtimeDir, 'settlements'),
        PAYBRIDGE_AUTH_TOKENS: authTokens,
        PAYBRIDGE_REFUND_AUTO_APPROVE: 'true',
      },
    },
    { command: `npm run dev -- --host 127.0.0.1 --port ${WEB_PORT}`, url: `http://127.0.0.1:${WEB_PORT}`, reuseExistingServer: true },
  ],
});
