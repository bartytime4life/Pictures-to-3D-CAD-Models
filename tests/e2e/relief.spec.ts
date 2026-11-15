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
  await expect(page.getByText(/Volume cross-check agrees/)).toBeVisible();
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

  // Changing a setting marks the model stale and disables outdated downloads; once the
  // settings rest, the model rebuilds by itself and the superseded model is deleted.
  const firstId = [...jobs].at(-1);
  expect(firstId).toBeTruthy();
  const deleted = page.waitForResponse(
    (response) =>
      response.request().method() === 'DELETE' && response.url().endsWith(`/api/models/${firstId}`),
  );
  await page.getByLabel('Thickest').fill('6');
  await expect(page.getByText('Previous model · updating when you pause')).toBeVisible();
  await expect(page.getByRole('button', { name: /^STL/ })).toBeDisabled();
  await expect(page.getByText(/Previous model/)).toBeHidden({ timeout: 60_000 });
  expect((await deleted).status()).toBe(204);
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

test('moon depth map builds a hemisphere dome', async ({ page }) => {
  await page.goto('/#relief');
  await page.getByRole('button', { name: 'Try the moon depth map' }).click();
  await expect(page.getByRole('heading', { name: 'Your relief' })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByLabel('Thickest')).toHaveValue('34.6');
  await page.getByText('Fine-tune (optional)').click();
  await expect(page.getByLabel('Picture type')).toHaveValue('depth');
  // A 100 mm wide sample has a 30 mm sphere radius: 1.6 mm base + 30 mm dome.
  await expect(page.locator('.relief-facts dd').first()).toHaveText(/× 31\.(59|60) mm/);
  await expect(page.locator('.check-bad')).toHaveCount(0);
});

test('moon lamp wraps a world map into a verified hollow sphere', async ({ page }, testInfo) => {
  await page.goto('/#relief');
  await page.getByRole('button', { name: 'Try the moon lamp' }).click();
  await expect(page.getByRole('heading', { name: 'Your lamp' })).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.locator('canvas[data-model-ready="true"]')).toBeVisible();
  const shape = page.getByRole('group', { name: 'Shape' });
  await expect(shape.getByRole('button', { name: 'Sphere' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect(page.getByLabel('Sphere diameter')).toHaveValue('100');
  await expect(page.getByText(/Ø 100\.0 mm, .* mm tall/)).toBeVisible();
  await expect(page.getByText(/V − E \+ F = .* = 2/)).toBeVisible();
  await expect(page.locator('.check-bad')).toHaveCount(0);
  await expect(page.getByText(/flat ring around the 35 mm opening/)).toBeVisible();
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  await page.screenshot({ path: 'docs/images/relief-sphere.png', fullPage: true });
  const stl = await download(page, /^STL/, testInfo);
  expect(stl.data.length).toBe(84 + 50 * stl.data.readUInt32LE(80));
  const blender = await download(page, /^Blender ZIP/, testInfo);
  expect(blender.data.includes(Buffer.from('build_relief.py'))).toBe(true);

  // An impossible sphere is explained before anything is sent.
  await page.getByLabel('Sphere diameter').fill('30');
  // A 30 mm sphere has a 24 mm inside, too small around a 35 mm opening.
  await expect(
    page.getByText('The opening must be narrower than 90% of the inside diameter.'),
  ).toBeVisible();
  await page.getByLabel('Thickest').fill('6'); // Leaves 18 mm inside a 30 mm sphere.
  await expect(page.getByText('The sphere is too small for its thickest wall.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Update model' })).toBeDisabled();
});

test('AI depth follows the model status and stays out of lithophanes', async ({ page }) => {
  let available = false;
  await page.route('**/api/relief/depth', (route) =>
    route.fulfill({
      json: {
        available,
        model: 'Depth Anything V2 Small',
        license: 'Apache-2.0',
        revision: '4472b7362082',
        bytes: 99060839,
        reason: available ? '' : 'The depth model is not installed.',
      },
    }),
  );
  // Without the model: no AI sample, and the picture type explains how to install it.
  await page.goto('/#relief');
  await expect(page.getByRole('button', { name: 'Try the moon sample' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Try AI depth on the moon' })).toHaveCount(0);
  await page.getByText('Fine-tune (optional)').click();
  await expect(page.getByRole('option', { name: /AI depth/ })).toBeDisabled();
  await expect(page.locator('#relief-ai-hint')).toHaveText(/depth-model\.sh install/);

  // With the model reported: the choice is offered. A lithophane uses the photo's light
  // instead, so the request the server receives must say photo.
  available = true;
  await page.reload();
  await expect(page.getByRole('button', { name: 'Try AI depth on the moon' })).toBeVisible();
  await page.getByRole('button', { name: 'Try the moon sample' }).click();
  await expect(page.getByRole('heading', { name: 'Your relief' })).toBeVisible({
    timeout: 60_000,
  });
  await page.getByText('Fine-tune (optional)').click();
  await page.getByLabel('Picture type').selectOption('ai');
  await expect(page.getByText('AI depth: nearer = raised')).toBeVisible();
  // Choosing AI depth starts an automatic relief rebuild of its own, which may be sent
  // before or after the mode switch, so wait for the first lithophane request.
  const settingsOf = (request: { postData(): string | null }) =>
    JSON.parse(/"settings"\r\n\r\n(.*)\r\n/.exec(request.postData() ?? '')![1]);
  const sent = page.waitForRequest(
    (r) =>
      r.url().endsWith('/api/relief') &&
      r.method() === 'POST' &&
      settingsOf(r).mode === 'lithophane',
  );
  await page.getByRole('radio', { name: /Lithophane/ }).click();
  const settings = settingsOf(await sent);
  expect([settings.mode, settings.source]).toEqual(['lithophane', 'photo']);
  await expect(page.getByRole('heading', { name: 'Your lithophane' })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.locator('.check-bad')).toHaveCount(0);
});

test('installed AI depth model turns the moon photo into a dome', async ({
  page,
  request,
}, testInfo) => {
  const state = await (await request.get('/api/relief/depth')).json();
  test.skip(!state.available, 'Optional depth model not installed (./scripts/depth-model.sh)');
  await page.goto('/#relief');
  await page.getByRole('button', { name: 'Try AI depth on the moon' }).click();
  await expect(page.getByRole('heading', { name: 'Your relief' })).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.locator('canvas[data-model-ready="true"]')).toBeVisible();
  await expect(page.locator('.check-bad')).toHaveCount(0);
  await expect(
    page.getByText(/Depth Anything V2 Small \(Apache-2\.0, rev 4472b7362082\)/),
  ).toBeVisible();
  await expect(page.getByText(/not measured distances/)).toBeVisible();
  await page.getByRole('button', { name: 'Heights' }).click();
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  await page.screenshot({ path: 'docs/images/relief-ai-depth.png', fullPage: true });
  const estimate = await download(page, /^AI depth map/, testInfo);
  expect(estimate.name).toBe('Moon-dome-AI-depth.png');
  expect([estimate.data[24], estimate.data[25]]).toEqual([16, 0]);
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
});

test('moon elevation map builds a true-scale exaggerated globe', async ({ page }) => {
  await page.goto('/#relief');
  await page.getByRole('button', { name: 'Try the moon elevation globe' }).click();
  await expect(page.getByRole('heading', { name: 'Your globe' })).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.getByLabel('Exaggeration')).toHaveValue('12');
  await expect(page.getByLabel('Heights are in')).toHaveValue('km');
  await expect(page.getByLabel('Thickest')).toHaveCount(0); // Set by the data.
  await expect(page.getByRole('group', { name: 'Bright areas are' })).toHaveCount(0);
  // 11.8 km of relief on a 50 mm-radius Moon (1737.4 km) is 0.34 mm; 12x is 4.07 mm.
  await expect(page.getByText(/0\.3[34]\d mm at true scale × 12\.0 = 4\.0\d mm/)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Height map' })).toBeVisible();
  await expect(page.locator('.check-bad')).toHaveCount(0);

  // The server rejects this; the automatic rebuild reports it once and does not retry the
  // same settings in a loop. Update model stays available as the manual retry.
  let builds = 0;
  page.on('request', (request) => {
    if (request.url().endsWith('/api/relief') && request.method() === 'POST') builds += 1;
  });
  await page.getByLabel('Exaggeration').fill('1000');
  await expect(page.getByRole('alert')).toContainText('Use at most', { timeout: 60_000 });
  await expect(page.getByText('Previous model · press Update model to try again')).toBeVisible();
  const afterFailure = builds;
  await page.waitForTimeout(2_000);
  expect(builds).toBe(afterFailure);
  expect(afterFailure).toBe(1);
  await expect(page.getByRole('button', { name: 'Update model' })).toBeEnabled();
});

test('both studios share one header that keeps the name whole and labels every icon', async ({
  page,
}) => {
  // Report no AI model so the sample gallery is the same on every machine.
  await page.route('**/api/relief/depth', (route) =>
    route.fulfill({ json: { available: false, reason: 'The depth model is not installed.' } }),
  );
  const widths = [1920, 1366, 1280, 1251, 1100, 1001, 800, 375];
  async function checkHeader(studio: 'workbench' | 'relief') {
    const tabs = page.getByRole('navigation', { name: 'Studios' });
    const current = studio === 'workbench' ? 'Flat-part workbench' : 'Relief and lithophane studio';
    await expect(tabs.getByRole('link', { name: current })).toHaveAttribute('aria-current', 'page');
    await expect(tabs.getByRole('link', { name: /OpenSCAD workspace/ })).toBeVisible();
    for (const width of widths) {
      await page.setViewportSize({ width, height: 900 });
      const layout = await page.evaluate(() => {
        const bar = document.querySelector('.topbar')!;
        const name = document.querySelector<HTMLInputElement>('.project-name input')!;
        // Every header link and button shows a visible text label, not just an icon.
        const unlabeled = [...bar.querySelectorAll('nav a, .header-actions > *')].filter(
          (item) =>
            ![...item.querySelectorAll('span')].some(
              (span) => span.getBoundingClientRect().width > 0 && span.textContent!.trim(),
            ),
        ).length;
        return {
          barOverflow: bar.scrollWidth - bar.clientWidth,
          nameCut: name.scrollWidth > name.clientWidth + 1,
          unlabeled,
        };
      });
      expect(layout, `${studio} at ${width}px`).toEqual({
        barOverflow: 0,
        nameCut: false,
        unlabeled: 0,
      });
    }
    await page.setViewportSize({ width: 1280, height: 900 });
  }

  await page.goto('/');
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue('Mounting plate');
  await checkHeader('workbench');
  // The workbench loads its own sample. Let that trace and build finish so this test does
  // not hold the server's single trace slot while the next test starts.
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  expect(
    await page.evaluate(async () => (await fetch('/api/models', { method: 'DELETE' })).ok),
  ).toBe(true);

  await page
    .getByRole('navigation', { name: 'Studios' })
    .getByRole('link', { name: 'Relief and lithophane studio' })
    .click();
  await expect(page).toHaveURL(/#relief$/);
  await checkHeader('relief');

  // The start screen offers the samples as a captioned gallery; the TIFF one uses an icon.
  const samples = page.getByRole('list', { name: 'Samples' }).getByRole('listitem');
  await expect(samples).toHaveCount(4);
  await expect(samples.nth(0)).toContainText('Flat relief from lightness');
  await expect(samples.nth(2)).toContainText('Backlit sphere lithophane');
  await expect(samples.nth(3).locator('img')).toHaveCount(0);
  await expect(samples.locator('img')).toHaveCount(3);
  for (const image of await samples.locator('img').all())
    await expect
      .poll(() => image.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0))
      .toBe(true);
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
});

test('a busy server delays the relief build instead of failing it', async ({ page }) => {
  // The first request meets another build in progress; the page waits out Retry-After.
  let attempts = 0;
  await page.route('**/api/relief', async (route) => {
    attempts += 1;
    if (attempts === 1)
      return route.fulfill({
        status: 429,
        headers: { 'Retry-After': '1' },
        json: { detail: 'Another model is being built. Wait a moment and try again.' },
      });
    return route.continue();
  });
  await page.goto('/#relief');
  await page.getByRole('button', { name: 'Try the moon sample' }).click();
  await expect(page.getByText('Waiting for another build to finish…').first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Your relief' })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(attempts).toBe(2);
});
