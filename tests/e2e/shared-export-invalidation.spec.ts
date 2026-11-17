import { test, expect, type Page, type Response } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import type { ReliefResult } from '../../frontend/src/relief';

const jobs = new Set<string>();
const clearedMessage =
  'Temporary exports cleared. Your picture and settings are still here; update the model to create fresh files.';

test.beforeEach(async ({ page }) => {
  page.on('response', async (response) => {
    if (/\/api\/(build|relief)$/.test(response.url()) && response.ok()) {
      const result = await response.json().catch(() => null);
      if (result?.id) jobs.add(result.id);
    }
  });
  // Expose the launch control consistently; these tests never request a native launch.
  await page.route('**/api/blender', (route) =>
    route.fulfill({
      json: {
        name: 'Blender',
        tested_version: '4.5',
        minimum_version: '4.2',
        download_url: 'https://www.blender.org/download/',
        detected: true,
        bridge_enabled: true,
        launch_available: true,
        launch_reason: '',
      },
    }),
  );
});

test.afterEach(async ({ request }) => {
  for (const id of jobs) await request.delete(`/api/models/${id}`);
  jobs.clear();
});

const reliefResponse = (response: Response) =>
  response.request().method() === 'POST' && response.url().endsWith('/api/relief') && response.ok();

async function studio(page: Page, name: 'workbench' | 'relief') {
  await page
    .getByRole('navigation', { name: 'Studios', exact: true })
    .locator(`a[href="#${name}"]`)
    .click();
  await expect(page.locator(`[data-studio="${name}"]`)).toBeVisible();
}

async function loadRelief(page: Page) {
  await page.goto('/#relief');
  const response = page.waitForResponse(reliefResponse);
  await page.getByRole('button', { name: 'Try the moon sample', exact: true }).click();
  const model = (await (await response).json()) as ReliefResult;
  jobs.add(model.id);
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  await expect(page.getByRole('button', { name: /^STL/ })).toBeEnabled();
  return model;
}

async function readyFlatPart(page: Page) {
  await studio(page, 'workbench');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
}

async function clearFromWorkbench(page: Page) {
  await page.getByRole('button', { name: 'Capture guide', exact: true }).click();
  const response = page.waitForResponse(
    (item) => item.request().method() === 'DELETE' && item.url().endsWith('/api/models'),
  );
  await page.getByRole('button', { name: 'Clear temporary exports', exact: true }).click();
  return response;
}

async function settingsSnapshot(page: Page) {
  return page
    .locator('[data-studio="relief"] input:not([type="file"]), [data-studio="relief"] select')
    .evaluateAll((elements) =>
      elements.map((element) => {
        const input = element as HTMLInputElement | HTMLSelectElement;
        return { id: input.id || input.getAttribute('aria-label'), value: input.value };
      }),
    );
}

async function expectClearedRelief(page: Page) {
  await expect(page.getByText(clearedMessage, { exact: true })).toBeVisible();
  const downloads = page.locator('[data-studio="relief"] .relief-downloads button');
  expect(await downloads.count()).toBeGreaterThan(0);
  for (const button of await downloads.all()) await expect(button).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Open in Blender', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
  // Observe beyond Relief's 700 ms debounce: clearing requires an explicit rebuild.
  const automaticBuild = await page
    .waitForRequest(
      (request) => request.method() === 'POST' && request.url().endsWith('/api/relief'),
      { timeout: 1200 },
    )
    .then(
      () => true,
      () => false,
    );
  expect(automaticBuild).toBe(false);
}

test('clearing flat-part exports invalidates kept-alive Relief files and preserves its editable source', async ({
  page,
  request,
}, testInfo) => {
  const original = await loadRelief(page);
  expect((await request.get(original.downloads.stl!)).status()).toBe(200);
  await page.getByRole('button', { name: 'Photo', exact: true }).click();
  const source = page.getByRole('img', { name: 'Chosen source image', exact: true });
  const sourceUrl = await source.getAttribute('src');
  const settings = await settingsSnapshot(page);

  await readyFlatPart(page);
  expect((await clearFromWorkbench(page)).ok()).toBe(true);
  expect((await request.get(original.downloads.stl!)).status()).toBe(404);
  await studio(page, 'relief');
  await expectClearedRelief(page);
  expect(await settingsSnapshot(page)).toEqual(settings);
  await expect(source).toHaveAttribute('src', sourceUrl!);
  expect(
    await source.evaluate((image) => (image as HTMLImageElement).naturalWidth),
  ).toBeGreaterThan(0);

  const rebuilding = page.waitForResponse(reliefResponse);
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  const fresh = (await (await rebuilding).json()) as ReliefResult;
  jobs.add(fresh.id);
  expect(fresh.id).not.toBe(original.id);
  expect(fresh.settings).toEqual({ ...original.settings, revision: fresh.settings.revision });
  await expect(page.getByRole('button', { name: /^STL/ })).toBeEnabled();
  await expect(page.getByText(clearedMessage, { exact: true })).toBeHidden();
  const downloading = page.waitForEvent('download');
  await page.getByRole('button', { name: /^STL/ }).click();
  const download = await downloading;
  const output = testInfo.outputPath('rebuilt-relief.stl');
  await download.saveAs(output);
  const data = await readFile(output);
  expect(data.length).toBeGreaterThan(84);
  expect(data.length).toBe(84 + 50 * data.readUInt32LE(80));
  expect((await request.get(fresh.downloads.stl!)).status()).toBe(200);
});

test('failed global cleanup leaves the existing Relief exports valid', async ({
  page,
  request,
}) => {
  const original = await loadRelief(page);
  const settings = await settingsSnapshot(page);
  await readyFlatPart(page);
  await page.route('**/api/models', (route) =>
    route.request().method() === 'DELETE'
      ? route.fulfill({ status: 503, json: { detail: 'Cleanup unavailable for this test.' } })
      : route.continue(),
  );
  expect((await clearFromWorkbench(page)).status()).toBe(503);
  await expect(page.getByRole('alert')).toContainText('Cleanup unavailable for this test.');
  await studio(page, 'relief');
  await expect(page.getByRole('button', { name: /^STL/ })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Open in Blender', exact: true })).toBeEnabled();
  await expect(page.getByText(clearedMessage, { exact: true })).toHaveCount(0);
  expect(await settingsSnapshot(page)).toEqual(settings);
  expect((await request.get(original.downloads.stl!)).status()).toBe(200);
});

test('a successful Relief build response arriving after cleanup cannot restore deleted exports', async ({
  page,
  request,
}) => {
  const original = await loadRelief(page);
  await readyFlatPart(page);
  await studio(page, 'relief');
  let release!: () => void;
  const responseGate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let built!: (model: ReliefResult) => void;
  const backendCompleted = new Promise<ReliefResult>((resolve) => {
    built = resolve;
  });
  await page.route(
    '**/api/relief',
    async (route) => {
      const response = await route.fetch();
      expect(response.ok()).toBe(true);
      const model = (await response.json()) as ReliefResult;
      jobs.add(model.id);
      built(model);
      await responseGate;
      await route.fulfill({ response }).catch(() => {});
    },
    { times: 1 },
  );
  try {
    await page.getByLabel('Thickest', { exact: true }).fill('6');
    await page.getByRole('button', { name: 'Update model', exact: true }).click();
    const held = await backendCompleted;
    expect(held.id).not.toBe(original.id);
    expect((await request.get(held.downloads.stl!)).status()).toBe(200);
    const settings = await settingsSnapshot(page);
    await studio(page, 'workbench');
    expect((await clearFromWorkbench(page)).ok()).toBe(true);
    expect((await request.get(held.downloads.stl!)).status()).toBe(404);
    expect((await request.get(original.downloads.stl!)).status()).toBe(404);
    const delivered = page.waitForResponse(reliefResponse);
    release();
    await delivered;
    await studio(page, 'relief');
    await expectClearedRelief(page);
    expect(await settingsSnapshot(page)).toEqual(settings);
    await expect(page.getByLabel('Thickest', { exact: true })).toHaveValue('6');
  } finally {
    release();
  }
});
