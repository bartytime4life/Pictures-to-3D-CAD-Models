import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const runtime = {
  ready: true,
  checks: [
    {
      id: 'core',
      label: 'CAD dependencies',
      status: 'ready',
      required: true,
      detail: 'Core dependencies found.',
    },
  ],
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/runtime', (route) => route.fulfill({ json: runtime }));
});

test('fresh Start lets users choose a task without creating an unseen model', async ({ page }) => {
  const jobs: string[] = [];
  page.on('request', (request) => {
    if (/\/api\/(trace|build|relief|designer\/build)$/.test(request.url()))
      jobs.push(request.url());
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'What would you like to make?' })).toBeVisible();
  await expect(page.getByText('Core requirements found', { exact: true })).toBeVisible();
  await expect(page.locator('[data-studio="workbench"]')).toHaveCount(0);
  const accessibility = await new AxeBuilder({ page }).include('[data-studio="start"]').analyze();
  expect(accessibility.violations).toEqual([]);
  await page.getByRole('link', { name: /Trace a photo into CAD/ }).click();
  await expect(page.getByRole('dialog', { name: 'Start from a photo.' })).toBeVisible();
  await expect(page).toHaveURL(/#workbench$/);
  await page.keyboard.press('Escape');
  await page
    .getByRole('navigation', { name: 'Studios', exact: true })
    .getByRole('link', { name: 'Start', exact: true })
    .click();
  await page.getByRole('link', { name: 'Saved flat-part projects', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Project library', exact: true })).toBeVisible();
  expect(jobs).toEqual([]);
});

test('compact workspace picker works at phone and tablet widths without overflow', async ({
  page,
}) => {
  await page.goto('/');
  for (const width of [320, 375, 800, 1100]) {
    await page.setViewportSize({ width, height: 900 });
    const picker = page.getByRole('combobox', { name: 'Workspace', exact: true });
    await expect(picker).toHaveValue('start');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      width,
    );
    await picker.selectOption('image');
    await expect(page).toHaveURL(/#image$/);
    await picker.selectOption('start');
    await expect(page.getByRole('heading', { name: 'What would you like to make?' })).toBeVisible();
  }
});

test('malformed setup metadata offers recovery without crashing Start', async ({ page }) => {
  await page.route('**/api/runtime', (route) =>
    route.fulfill({ json: { ready: true, checks: [null] } }),
  );
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('setup');
  await expect(page.getByRole('heading', { name: 'What would you like to make?' })).toBeVisible();
  await page.unroute('**/api/runtime');
  await page.route('**/api/runtime', (route) => route.fulfill({ json: runtime }));
  await page.getByRole('button', { name: 'Refresh setup', exact: true }).click();
  await expect(page.getByText('Core requirements found', { exact: true })).toBeVisible();
});

test('phone section jumps focus their target while keeping the designer route', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto('/#designer');
  const sections = page.getByRole('navigation', { name: 'Shape designer sections', exact: true });
  for (const [name, id] of [
    ['CAD preview', 'shape-preview-section'],
    ['2D outline', 'shape-outline-section'],
    ['Shape tools', 'shape-tools-section'],
  ]) {
    await sections.getByRole('button', { name, exact: true }).click();
    await expect(page.locator(`#${id}`)).toBeFocused();
    await expect(page).toHaveURL(/#designer$/);
  }
});

test('creative tools stay usable for drafting when local AI status fails', async ({ page }) => {
  await page.route('**/api/assistant/status', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Local AI status unavailable' } }),
  );
  await page.goto('/#creative');
  const example = page.getByRole('button', { name: 'Try an example', exact: true });
  await expect(example).toBeEnabled();
  await example.click();
  await expect(
    page.getByRole('textbox', { name: 'What would you like to make?', exact: true }),
  ).not.toHaveValue('');
  await expect(
    page.getByRole('button', { name: 'Generate creative notes', exact: true }),
  ).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Plan the making', exact: true })).toBeEnabled();
});
