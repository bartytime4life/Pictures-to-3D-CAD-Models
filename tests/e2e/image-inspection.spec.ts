import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

const fixture = (name: string) => path.resolve('tests/fixtures/image-inspection', name);
async function open(page: Page, slot: 'A' | 'B', name = 'plate.png') {
  await page.getByLabel(`Choose image ${slot}`, { exact: true }).setInputFiles(fixture(name));
  await expect(
    page.getByRole('img', { name: `Sampled image ${slot}: ${name}`, exact: true }),
  ).toBeVisible();
}

test('region readings, A/B export and studio continuity keep analysis local', async ({ page }) => {
  const uploads: string[] = [];
  page.on('request', (request) => {
    if (request.method() === 'POST') uploads.push(request.url());
  });
  await page.goto('/#image');
  await expect(page.getByRole('heading', { name: 'Understand your source image.' })).toBeVisible();
  await open(page, 'A');
  await open(page, 'B', 'brighter.png');
  await page.getByLabel('Width (%)', { exact: true }).fill('50');
  await page.getByLabel('Height (%)', { exact: true }).fill('50');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save readings', exact: true }).click();
  const report = JSON.parse(await readFile((await (await download).path())!, 'utf8'));
  expect(report.schema).toBe('pictures-to-cad-image-inspection-v1');
  expect(report.metrics.width).toBe(80);
  expect(report.metrics.height).toBe(60);
  expect(report.metrics.histogram.reduce((a: number, b: number) => a + b)).toBe(4800);
  expect(report.difference.changedPercent).toBeGreaterThan(0);
  expect(report.processing.alphaBacking).toBe('white');
  expect(report.sources.A.name).toBe('plate.png');
  expect(JSON.stringify(report)).not.toContain('base64');
  await page.getByRole('link', { name: 'Knowledge base', exact: true }).click();
  await expect(page.locator('[data-studio="knowledge"]')).toBeVisible();
  await page
    .locator('[data-studio="knowledge"]')
    .getByRole('link', { name: 'Image inspection', exact: true })
    .click();
  await expect(page.getByLabel('Width (%)', { exact: true })).toHaveValue('50');
  await expect(
    page.getByRole('img', { name: 'Sampled image B: brighter.png', exact: true }),
  ).toBeVisible();
  expect(uploads).toEqual([]);
});

test('small regions, mismatched frames and failed replacement remain explicit', async ({
  page,
}) => {
  await page.goto('/#image');
  await open(page, 'A');
  await page.getByLabel('Width (%)', { exact: true }).fill('0.1');
  await expect(page.getByText('Unavailable', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Full image', exact: true }).click();
  await open(page, 'B', 'different-size.png');
  await expect(page.getByText(/Sample sizes differ/)).toBeVisible();
  await page.getByLabel('Choose image B', { exact: true }).setInputFiles({
    name: 'broken.png',
    mimeType: 'image/png',
    buffer: Buffer.from('not an image'),
  });
  await expect(page.getByRole('alert')).toContainText('previous image is retained');
  await expect(
    page.getByRole('img', { name: 'Sampled image B: different-size.png', exact: true }),
  ).toBeVisible();
});

test('clearing a pending import prevents late resurrection', async ({ page }) => {
  await page.addInitScript(() => {
    const decode = window.createImageBitmap.bind(window);
    (window as any).releaseInspection = null;
    window.createImageBitmap = (async (...args: any[]) => {
      if (args[0]?.name === 'slow.png')
        await new Promise((resolve) => {
          (window as any).releaseInspection = resolve;
        });
      return (decode as any)(...args);
    }) as typeof createImageBitmap;
  });
  await page.goto('/#image');
  await open(page, 'A');
  await page.getByLabel('Choose image A', { exact: true }).setInputFiles({
    name: 'slow.png',
    mimeType: 'image/png',
    buffer: await readFile(fixture('brighter.png')),
  });
  await expect(page.getByRole('status')).toContainText('Reading image A');
  await page.getByRole('button', { name: 'Clear image A', exact: true }).click();
  await page.evaluate(() => (window as any).releaseInspection());
  await expect(page.getByRole('heading', { name: 'Open an image to inspect it' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save readings', exact: true })).toBeDisabled();
});

test('handoff sends original pixels rather than the inspected crop', async ({ page, request }) => {
  const jobs: string[] = [];
  page.on('response', async (response) => {
    if (/\/api\/build$/.test(response.url()) && response.ok()) {
      const body = await response.json().catch(() => null);
      if (body?.id) jobs.push(body.id);
    }
  });
  try {
    await page.goto('/#image');
    await open(page, 'A', 'large-plate.png');
    await page.getByLabel('Width (%)', { exact: true }).fill('20');
    const tracing = page.waitForResponse(
      (response) => response.url().endsWith('/api/trace') && response.ok(),
    );
    await page.getByRole('button', { name: 'Open original in Flat part', exact: true }).click();
    const traced = await (await tracing).json();
    const direct = await request.post('/api/trace', {
      multipart: {
        file: {
          name: 'large-plate.png',
          mimeType: 'image/png',
          buffer: await readFile(fixture('large-plate.png')),
        },
      },
    });
    expect(direct.ok()).toBe(true);
    // The tracer applies its own 1400 px limit. Its decoded result must match a
    // direct upload of the original, rather than the 720 px inspection or crop.
    expect(traced.image).toEqual((await direct.json()).image);
    expect(traced.image.width).toBe(1400);
    await expect(page).toHaveURL(/#workbench$/);
    await expect(
      page
        .getByRole('region', { name: 'Model dimensions', exact: true })
        .getByText('Outline ready. Enter the full measured width and thickness of your part.', {
          exact: true,
        }),
    ).toBeVisible();
    await page.getByRole('link', { name: 'Image inspection', exact: true }).click();
    await expect(page.getByLabel('Width (%)', { exact: true })).toHaveValue('20');
  } finally {
    for (const id of jobs) await request.delete(`/api/models/${id}`);
  }
});

test('image workspace stays usable at phone/tablet/desktop widths and passes the targeted axe scan', async ({
  page,
}) => {
  await page.goto('/#image');
  await open(page, 'A');
  for (const width of [1920, 1440, 1366, 1251, 1100, 1001, 800, 650, 375, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
      `page overflow at ${width}`,
    ).toBeLessThanOrEqual(width);
    const nav = page.getByRole('navigation', { name: 'Studios', exact: true });
    if (width <= 1100)
      await expect(nav.getByRole('combobox', { name: 'Workspace', exact: true })).toHaveValue(
        'image',
      );
    else
      await expect(nav.getByRole('link', { name: 'Image inspection', exact: true })).toBeVisible();
  }
  const result = await new AxeBuilder({ page }).include('[data-studio="image"]').analyze();
  expect(result.violations).toEqual([]);
  await mkdir('.local/verification', { recursive: true });
  await page.screenshot({
    path: '.local/verification/image-inspection-mobile.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1058 });
  await page.screenshot({
    path: '.local/verification/image-inspection-desktop.png',
    fullPage: true,
  });
});

test('region dragging commits once and Escape cancels the next gesture', async ({ page }) => {
  await page.goto('/#image');
  await open(page, 'A');
  const svg = page.locator('.image-canvas svg');
  const box = (await svg.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.7);
  await page.mouse.up();
  expect(Number(await page.getByLabel('Width (%)', { exact: true }).inputValue())).toBeCloseTo(
    40,
    0,
  );
  expect(Number(await page.getByLabel('Height (%)', { exact: true }).inputValue())).toBeCloseTo(
    50,
    0,
  );
  const previous = await page.getByLabel('Width (%)', { exact: true }).inputValue();
  await svg.focus();
  await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.3);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.8);
  await page.keyboard.press('Escape');
  await page.mouse.up();
  await expect(page.getByLabel('Width (%)', { exact: true })).toHaveValue(previous);
});
