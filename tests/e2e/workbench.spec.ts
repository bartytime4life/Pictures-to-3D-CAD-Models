import { test, expect, type Locator, type Page } from '@playwright/test';
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

// Pairs of different visible text runs inside `panel` whose drawn line boxes share pixels.
// Text rectangles come from the text nodes themselves, so padding and block width do not count.
async function overlappingText(panel: Locator) {
  return panel.evaluate((root) => {
    const lines: { run: number; text: string; box: DOMRect }[] = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let run = 0;
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.textContent?.trim();
      const shown = node.parentElement?.checkVisibility({
        visibilityProperty: true,
        opacityProperty: true,
      });
      if (!text || !shown) continue;
      run += 1;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const box of range.getClientRects())
        if (box.width > 0 && box.height > 0) lines.push({ run, text, box });
    }
    const clashes = new Set<string>();
    for (const [index, a] of lines.entries())
      for (const b of lines.slice(index + 1)) {
        const wide = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left);
        const tall = Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top);
        if (a.run !== b.run && wide > 1 && tall > 1) clashes.add(`"${a.text}" over "${b.text}"`);
      }
    return [...clashes];
  });
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
  await page.getByText('Drawings & source files', { exact: true }).click();
  for (const format of ['STEP', 'STL', 'DXF', 'SVG', 'PDF', 'OpenSCAD']) {
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
    if (format === 'SVG') {
      expect(download.suggestedFilename()).toMatch(/\.svg$/);
      expect(data.toString('utf8')).toMatch(/<svg [^>]*width="[\d.]+mm"/);
    }
    if (format === 'PDF') {
      expect(download.suggestedFilename()).toMatch(/\.pdf$/);
      expect(data.subarray(0, 8).toString('latin1')).toBe('%PDF-1.4');
      expect(data.toString('latin1')).toContain('drawn at 1:1');
      await expect(page.locator('.notice')).toContainText('Print it at 100 %');
    }
    if (format === 'OpenSCAD') {
      expect(download.suggestedFilename()).toMatch(/\.scad$/);
      expect(data.toString('utf8')).toContain('linear_extrude(height = thickness_mm');
    }
  }
  expect(errors).toEqual([]);
});

test('companion OpenSCAD workspace opens separately while the current model stays available', async ({
  page,
}) => {
  await ready(page);
  const modelId = [...jobs].at(-1)!;
  const popupEvent = page.waitForEvent('popup');
  await page
    .getByRole('link', { name: 'OpenSCAD workspace (opens in a new tab)', exact: true })
    .click();
  const companion = await popupEvent;
  await expect(companion).toHaveURL(/\/reference-library\/index\.html#cad$/);
  await expect(companion.getByRole('tab', { name: 'OpenSCAD', exact: true })).toHaveAttribute(
    'aria-selected',
    'true',
  );
  await expect(companion.locator('#cad')).toBeVisible();
  await companion.close();
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  expect((await page.request.get(`/api/download/${modelId}/scad`)).status()).toBe(200);
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

test('a phone HEIC photo is accepted by its file name and traced', async ({ page }) => {
  await ready(page);
  // Browsers on Linux and Windows report no type for .heic, so the name decides.
  await page
    .getByLabel('Choose photo or project')
    .setInputFiles(path.resolve('tests/fixtures/plain.heic'));
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByText('plain.heic')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole('button', { name: 'Build model', exact: true })).toBeDisabled();
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('40');
  await page.getByLabel('Thickness', { exact: true }).fill('2');
  await page.getByRole('button', { name: 'Build model', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.export-summary')).toContainText('40.00');
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

test('a traced photo without a model shows one CAD preview message, and one while building', async ({
  page,
}) => {
  await ready(page);
  // The sample image under another name is the user's own photo: traced, not yet built.
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'my-bracket.png',
    mimeType: 'image/png',
    buffer: await readFile('frontend/public/sample.png'),
  });
  await expect(page.getByText('my-bracket.png')).toBeVisible({ timeout: 30_000 });
  const preview = page.getByRole('region', { name: 'CAD preview', exact: true });
  // The page's message and the 3D viewer's own placeholder used to be drawn on top of
  // each other here. Only the page's message, which follows the tracing state, is shown.
  const headings = preview
    .getByText(/^(Your solid starts here\.|Your CAD model will appear here)$/)
    .filter({ visible: true });
  for (const viewport of [
    { width: 1488, height: 1058 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await expect(headings).toHaveText(['Your solid starts here.']);
    await expect(
      preview.getByText('Set the measured width and thickness, then build your model.'),
    ).toBeVisible();
    await expect(preview.getByText('Trace a photo and set its dimensions to begin.')).toBeHidden();
    expect(await overlappingText(preview), `text overlap at ${viewport.width}px`).toEqual([]);
  }
  // While the first model builds, the page's message steps aside for the viewer's own
  // loading message. The build is held so that state can be inspected.
  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route('**/api/build', async (route) => {
    await held;
    await route.continue();
  });
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('40');
  await page.getByLabel('Thickness', { exact: true }).fill('2');
  await page.getByRole('button', { name: 'Build model', exact: true }).click();
  await expect(preview.getByText('Building your CAD solid…')).toBeVisible();
  await expect(headings).toHaveCount(0);
  expect(await overlappingText(preview), 'text overlap while building').toEqual([]);
  release();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
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
  // On the narrowest phones nothing may run past the screen edge, even where a panel
  // would clip it: the step bar puts labels under icons and toolbars wrap. The 3D canvas
  // follows the window a frame later, so the check polls until the layout settles.
  for (const width of [320, 360]) {
    await page.setViewportSize({ width, height: 800 });
    await expect(
      page.getByRole('button', { name: 'Search commands and help', exact: true }),
    ).toBeVisible();
    await expect
      .poll(
        () =>
          page.evaluate(() =>
            [...document.querySelectorAll('body *')]
              .filter(
                (e) =>
                  e.getClientRects().length && e.getBoundingClientRect().right > innerWidth + 0.5,
              )
              .map((e) => `${e.tagName}.${e.getAttribute('class') ?? ''}`),
          ),
        { message: `elements past the edge at ${width}px` },
      )
      .toEqual([]);
  }
  await page.setViewportSize({ width: 390, height: 844 });
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
