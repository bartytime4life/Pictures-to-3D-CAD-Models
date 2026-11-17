import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';

test('science scenarios recalculate, export, restore and reject invalid imports atomically', async ({
  page,
}) => {
  await page.goto('/#science');
  const output = page.locator('.lab-big-number');
  await expect(output).toContainText('78.845');
  await page.getByLabel('Known reference length (mm)', { exact: true }).fill('25');
  await page.getByLabel('Marked reference span (px)', { exact: true }).fill('100');
  await page.getByLabel('Part outline span (px)', { exact: true }).fill('400');
  await expect(output).toContainText('100.000');
  await expect(page.getByRole('img', { name: /Endpoint sensitivity/ })).toHaveAccessibleName(
    /98.039.*102.041/,
  );
  const saving = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export scenarios', exact: true }).click();
  const download = await saving;
  const saved = JSON.parse(await readFile((await download.path())!, 'utf8'));
  expect(saved.scale).toMatchObject({ knownMm: 25, referencePx: 100, outlinePx: 400 });

  await page.getByRole('button', { name: /Layer stack/ }).click();
  await page.getByLabel('Part height (mm)', { exact: true }).fill('4.1');
  await expect(output).toContainText('21');
  await expect(page.getByRole('img', { name: /conceptual layers/ })).toHaveAccessibleName(
    /4.200 millimeters.*0.100 millimeters/,
  );
  await page.getByRole('button', { name: /Measured fit/ }).click();
  await expect(output).toContainText('10.400');
  await page.getByLabel('Desired diametral clearance (mm)', { exact: true }).fill('0.4');
  await expect(output).toContainText('10.600');
  await page.getByLabel('Import science scenario JSON').setInputFiles({
    name: 'scenario.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(saved)),
  });
  await expect(page.getByRole('status').filter({ hasText: 'Scenario imported' })).toBeVisible();
  await expect(output).toContainText('100.000');

  const bad = {
    ...saved,
    scale: { ...saved.scale, knownMm: 12 },
    layers: { ...saved.layers, layerMm: 0 },
  };
  await page.getByLabel('Import science scenario JSON').setInputFiles({
    name: 'bad.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(bad)),
  });
  await expect(page.getByRole('alert')).toContainText('Regular layer height');
  await expect(page.getByLabel('Known reference length (mm)', { exact: true })).toHaveValue('25');
  await expect(output).toContainText('100.000');
  await page.getByLabel('Marked reference span (px)', { exact: true }).fill('2');
  await expect(
    page.getByRole('alert').filter({ hasText: 'twice the endpoint shift' }),
  ).toBeVisible();
  await expect(output).toHaveCount(0);
  await page.getByRole('button', { name: 'Reset experiment', exact: true }).click();
  await expect(output).toContainText('78.845');
});

test('knowledge search, notes and pins survive reload; offline guides download the same source', async ({
  page,
}) => {
  await page.goto('/#knowledge');
  await page.getByRole('searchbox', { name: 'Search knowledge base' }).fill('known object');
  await expect(
    page.getByRole('heading', { name: 'Measure from a known object', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Pin article', exact: true }).click();
  const notes = page.getByRole('textbox', {
    name: 'Your notes for Measure from a known object',
    exact: true,
  });
  await notes.fill('Quarter measured with calipers: 24.24 mm. Use same plane.');
  await expect(page.getByRole('status').filter({ hasText: 'Saved locally' })).toBeVisible();
  const saving = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export notebook', exact: true }).click();
  const notebook = JSON.parse(await readFile((await (await saving).path())!, 'utf8'));
  expect(notebook.pins).toContain('measurement');
  expect(notebook.notes.measurement).toContain('24.24');
  await page.reload();
  await page.getByRole('checkbox', { name: /Pinned only/ }).check();
  await expect(
    page.getByRole('heading', { name: 'Measure from a known object', exact: true }),
  ).toBeVisible();
  await expect(notes).toHaveValue('Quarter measured with calipers: 24.24 mm. Use same plane.');
  await page.getByRole('button', { name: /Read detailed local guide/ }).click();
  const guide = page.getByRole('region', { name: 'Detailed local guide', exact: true });
  await expect(guide.locator('pre')).toContainText('# ');
  const content = await guide.locator('pre').textContent();
  const downloading = page.waitForEvent('download');
  await guide.getByRole('link', { name: 'Download Markdown', exact: true }).click();
  expect(await readFile((await (await downloading).path())!, 'utf8')).toBe(content);
  await page.getByLabel('Import knowledge notebook JSON').setInputFiles({
    name: 'bad-notebook.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify({ ...notebook, pins: ['unknown-article'] })),
  });
  await expect(page.getByRole('alert')).toContainText('unknown pinned guide');
  await expect(notes).toHaveValue('Quarter measured with calipers: 24.24 mm. Use same plane.');
});

test('unavailable browser storage is reported while notes remain exportable', async ({ page }) => {
  await page.addInitScript(() => {
    Storage.prototype.setItem = () => {
      throw new DOMException('Full', 'QuotaExceededError');
    };
  });
  await page.goto('/#knowledge');
  await page
    .getByRole('textbox', { name: 'Your notes for Capture a traceable flat part', exact: true })
    .fill('Keep this local draft in the export.');
  await expect(
    page.getByRole('status').filter({ hasText: 'Could not save to browser storage' }),
  ).toBeVisible();
  const saving = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export notebook', exact: true }).click();
  const notebook = JSON.parse(await readFile((await (await saving).path())!, 'utf8'));
  expect(notebook.notes.capture).toBe('Keep this local draft in the export.');
});

test('science and knowledge remain usable and accessible at phone width', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#science');
  await expect(page.getByRole('heading', { name: 'Science lab', exact: true })).toBeVisible();
  for (const experiment of [/Pixel scale/, /Layer stack/, /Measured fit/]) {
    await page.getByRole('button', { name: experiment }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
  await page.locator('a[href="#knowledge"]:visible').first().click();
  await expect(page.getByRole('heading', { name: 'Knowledge base', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});
