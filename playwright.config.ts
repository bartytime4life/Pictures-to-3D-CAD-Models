import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';

const executable =
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ||
  (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.PICAD_TEST_URL || 'http://127.0.0.1:8000',
    viewport: { width: 1488, height: 1058 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions: {
      executablePath: executable,
      args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    },
  },
  webServer: process.env.PICAD_TEST_URL
    ? undefined
    : {
        command: './scripts/start.sh',
        url: 'http://127.0.0.1:8000/api/health',
        reuseExistingServer: !process.env.CI,
        timeout: 30_000,
      },
});
