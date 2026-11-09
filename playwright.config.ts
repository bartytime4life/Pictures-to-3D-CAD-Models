import { chromium, defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';

// Browser order: an explicit executable, a system Chromium, Playwright's own installed
// Chromium, then an installed Google Chrome (as the reference library's checks do).
const playwrightChromium = (() => {
  try {
    return existsSync(chromium.executablePath());
  } catch {
    return false;
  }
})();
const systemChrome = [
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].find((path) => existsSync(path));
const executable =
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ||
  (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined) ||
  (playwrightChromium ? undefined : systemChrome);

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
