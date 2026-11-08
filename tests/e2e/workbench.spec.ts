import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

const jobs = new Set<string>();

test.beforeEach(async ({ page }) => {
  page.on('response', async (response) => {
    if (response.url().endsWith('/api/build') && response.ok()) {
      const model = await response.json().catch(() => null);
      if (model?.id) jobs.add(model.id);
    }
  });
});

test.afterEach(async ({ request }) => {
  for (const id of jobs) await request.delete(`/api/models/${id}`);
  jobs.clear();
});

async function ready(page: Page) {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  // Canvas fallback text is present in the DOM even when WebGL renders correctly.
  await expect(page.getByText('3D preview is unavailable')).toBeHidden();
  await expect(page.locator('canvas[data-model-ready="true"]')).toBeVisible();
}

test('sample creates real CAD, downloads valid formats, and renders the selected workbench', async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await ready(page);
  await expect(page.getByText('3 through holes detected')).toBeVisible();
  await expect(page.getByText('Sample · mounting plate')).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(2);
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  await mkdir('docs/images', { recursive: true });
  await page.screenshot({ path: 'docs/images/workbench.png', fullPage: true });
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  for (const format of ['STEP', 'STL', 'DXF']) {
    const downloadEvent = page.waitForEvent('download');
    await page.locator('.export-row').filter({ hasText: format }).click();
    const download = await downloadEvent;
    const output = testInfo.outputPath(download.suggestedFilename());
    await download.saveAs(output);
    const data = await readFile(output);
    expect(data.length).toBeGreaterThan(100);
    if (format === 'STEP') expect(data.toString('utf8')).toContain('ISO-10303-21');
    if (format === 'STL') expect(data.length).toBe(84 + 50 * data.readUInt32LE(80));
    if (format === 'DXF') expect(data.toString('utf8')).toContain('LWPOLYLINE');
  }
  expect(errors).toEqual([]);
});

test('dimension edits invalidate exports; inch display and saved recipes retain physical scale', async ({
  page,
}, testInfo) => {
  await ready(page);
  await page.getByLabel('Thickness', { exact: true }).fill('6');
  await expect(page.getByText('Previous model · update to apply your changes')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.export-summary')).toContainText('6.00 mm');
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  await page.getByRole('button', { name: 'in', exact: true }).click();
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    /3\.1496/,
  );
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const download = await downloadEvent;
  const saved = testInfo.outputPath('recipe.json');
  await download.saveAs(saved);
  const recipe = JSON.parse(await readFile(saved, 'utf8'));
  expect(recipe.width_mm).toBeCloseTo(80, 6);
  expect(recipe.thickness_mm).toBeCloseTo(6, 6);
  expect(recipe.profile.holes).toHaveLength(3);
  await page.getByLabel('Choose photo or project').setInputFiles(saved);
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue(/6\.0/);
  await expect(page.getByText('Restored project · outline only')).toBeVisible();
});

test('own photo requires measurements and a failed upload preserves the previous valid model', async ({
  page,
}) => {
  await ready(page);
  await page
    .getByLabel('Choose photo or project')
    .setInputFiles(path.resolve('frontend/public/sample.png'));
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '',
  );
  await expect(page.getByRole('button', { name: 'Build model', exact: true })).toBeDisabled();
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('40');
  await page.getByLabel('Thickness', { exact: true }).fill('2');
  await page.getByRole('button', { name: 'Build model', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.export-summary')).toContainText('40.00');
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'broken.png',
    mimeType: 'image/png',
    buffer: Buffer.from('not an image'),
  });
  await expect(page.getByRole('alert')).toContainText('could not be decoded');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '40',
  );
});

test('keyboard dialogs, accessibility checks, and mobile layout keep the workflow usable', async ({
  page,
}) => {
  await ready(page);
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.getByRole('button', { name: 'Capture guide', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Capture guide', exact: true })).toBeFocused();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole('spinbutton', { name: 'Reference width', exact: true }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'docs/images/workbench-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});

test('missing exports recover through rebuilding without downloading an error file', async ({
  page,
  request,
}) => {
  await ready(page);
  const currentId = [...jobs].at(-1)!;
  expect((await request.delete(`/api/models/${currentId}`)).status()).toBe(204);
  const downloads: string[] = [];
  page.on('download', (download) => downloads.push(download.suggestedFilename()));
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  await page.locator('.export-row').filter({ hasText: 'STEP' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  expect(downloads).toEqual([]);
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.export-row').filter({ hasText: 'STEP' })).toBeEnabled();
});

test('temporary-file cleanup preserves editable inputs and the workbench can build again', async ({
  page,
}) => {
  await ready(page);
  await page.getByRole('button', { name: 'Capture guide', exact: true }).click();
  await page.getByRole('button', { name: 'Clear temporary exports', exact: true }).click();
  await expect(page.getByText('Temporary exports cleared.', { exact: false }).last()).toBeVisible();
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await page.getByRole('button', { name: 'Build model', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
});
