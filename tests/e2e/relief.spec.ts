import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, readFile } from 'node:fs/promises';

const jobs = new Set<string>();

test.beforeEach(async ({ page }) => {
  page.on('response', async (response) => {
    if (response.url().endsWith('/api/relief') && response.ok()) {
      const model = await response.json().catch(() => null);
      if (model?.id) jobs.add(model.id);
    }
  });
});

test.afterEach(async ({ request }) => {
  for (const id of jobs) await request.delete(`/api/models/${id}`);
  jobs.clear();
});

async function loadSample(page: Page) {
  await page.goto('/#relief');
  await page.getByRole('button', { name: 'Try the moon sample' }).click();
  await expect(page.getByRole('button', { name: 'Update model' })).toBeEnabled({
    timeout: 60_000,
  });
  await expect(page.getByText('3D preview is unavailable')).toBeHidden();
  await expect(page.locator('canvas[data-model-ready="true"]')).toBeVisible();
}

async function download(page: Page, name: RegExp, testInfo: { outputPath: (n: string) => string }) {
  const event = page.waitForEvent('download');
  await page.getByRole('button', { name }).click();
  const file = await event;
  const output = testInfo.outputPath(file.suggestedFilename());
  await file.saveAs(output);
  return { name: file.suggestedFilename(), data: await readFile(output) };
}

test('moon sample becomes a verified relief with valid downloads', async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await loadSample(page);
  await expect(
    page.getByText('Watertight: every edge is shared by exactly two faces'),
  ).toBeVisible();
  await expect(page.getByText(/Euler characteristic .* = 2 \(one solid/)).toBeVisible();
  await expect(page.getByText(/Volume by two independent methods agrees/)).toBeVisible();
  await expect(page.locator('.check-bad')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Your relief' })).toBeVisible();
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  await mkdir('docs/images', { recursive: true });
  await page.screenshot({ path: 'docs/images/relief.png', fullPage: true });

  const stl = await download(page, /^STL/, testInfo);
  expect(stl.name).toBe('Moon-relief.stl');
  expect(stl.data.length).toBe(84 + 50 * stl.data.readUInt32LE(80));
  const threeMf = await download(page, /^3MF/, testInfo);
  expect(threeMf.data.subarray(0, 2).toString()).toBe('PK');
  const heightmap = await download(page, /^Height map/, testInfo);
  // PNG IHDR: bytes 24 = bit depth, 25 = colour type (0 = grayscale).
  expect(heightmap.data.subarray(1, 4).toString()).toBe('PNG');
  expect([heightmap.data[24], heightmap.data[25]]).toEqual([16, 0]);
  const blender = await download(page, /^Blender ZIP/, testInfo);
  expect(blender.data.includes(Buffer.from('build_relief.py'))).toBe(true);
  expect(blender.data.includes(Buffer.from('relief.json'))).toBe(true);
  const project = JSON.parse((await download(page, /^Settings/, testInfo)).data.toString());
  expect(project.format).toBe('pictures-to-cad-relief');
  expect(project.settings.mode).toBe('relief');

  // Changing a setting marks the model stale and disables outdated downloads.
  await page.getByLabel('Thickest').fill('6');
  await expect(page.getByText(/Previous model/)).toBeVisible();
  await expect(page.getByRole('button', { name: /^STL/ })).toBeDisabled();
  await page.getByRole('button', { name: 'Update model' }).click();
  await expect(page.getByText(/Previous model/)).toBeHidden({ timeout: 60_000 });
  // The brightest moon pixel is below L* 100, so the top lands just under the 6 mm limit.
  await expect(page.locator('.relief-facts dd').nth(1)).toHaveText(/– (5\.[89]\d|6\.00)\s*mm/);

  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  expect(errors).toEqual([]);
});

test('lithophane reports optics, offers the wedge, and fits a filament', async ({
  page,
}, testInfo) => {
  await loadSample(page);
  await page.getByRole('radio', { name: /Lithophane/ }).click();
  await expect(page.getByRole('heading', { name: 'Your lithophane' })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByLabel('Thinnest')).toHaveValue('0.8');
  await expect(page.getByLabel('Thickest')).toHaveValue('3');
  await expect(page.getByText('4.4 stops (21:1)')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Backlit prediction' })).toBeVisible();
  const wedge = await download(page, /^Calibration wedge/, testInfo);
  expect(wedge.data.length).toBe(84 + 50 * wedge.data.readUInt32LE(80));

  const fit = page.getByRole('button', { name: 'Fit half-value thickness' });
  await page.getByLabel('Step 1 reading').fill('200');
  await fit.click();
  await expect(page.getByText('Enter a number for at least three steps.')).toBeVisible();
  // Synthetic camera readings of exp(-mu t) with a 0.62 mm half-value thickness.
  const thickness = Array.from({ length: 8 }, (_, k) => 0.8 + (2.2 * k) / 7);
  for (const [index, t] of thickness.entries()) {
    const linear = 0.85 * Math.exp((-Math.LN2 / 0.62) * (t - 0.8));
    const srgb = linear <= 0.0031308 ? 12.92 * linear : 1.055 * linear ** (1 / 2.4) - 0.055;
    await page.getByLabel(`Step ${index + 1} reading`).fill(String(Math.round(srgb * 255)));
  }
  await fit.click();
  const result = page.locator('.relief-fit');
  await expect(result).toContainText(/Half-value thickness 0\.6[0-4]\d mm/);
  await result.getByRole('button', { name: 'Use this value' }).click();
  await expect(page.getByLabel('Half-value thickness')).toHaveValue(/^0\.6[0-4]\d$/);
  await expect(page.getByText(/Previous model/)).toBeVisible();
});

test('relief page rejects unsupported files and fits a phone screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#relief');
  // Before any build, only this page's own empty-state message is shown.
  await expect(page.getByText('Your 3D model appears here.')).toBeVisible();
  await expect(page.getByText('Your CAD model will appear here')).toHaveCount(0);
  await page.locator('input[type="file"]').setInputFiles({
    name: 'notes.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('not an image'),
  });
  await expect(page.getByRole('alert')).toContainText(
    'Choose a PNG, JPEG, WebP, HEIC or AVIF image.',
  );
  await page.getByRole('button', { name: 'Dismiss error' }).click();
  await page.getByRole('button', { name: 'Try the moon sample' }).click();
  await expect(page.getByRole('button', { name: 'Update model' })).toBeEnabled({
    timeout: 60_000,
  });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('link', { name: /Flat-part workbench/ }).click();
  await expect(page.getByRole('link', { name: 'Relief and lithophane studio' })).toBeVisible();
  // The workbench loads its own sample. Let that trace and build finish so this test does
  // not hold the server's single trace slot while the next test starts.
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  const leftover = await page.evaluate(async () => {
    const response = await fetch('/api/models', { method: 'DELETE' });
    return response.ok;
  });
  expect(leftover).toBe(true);
});
