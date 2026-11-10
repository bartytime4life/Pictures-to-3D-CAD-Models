import { expect, test, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import type { ProjectRecipe, TraceResult } from '../../frontend/src/types';

// The sample and CAD builds use the real service. Only retrace responses and AI
// answers are fixtures, to isolate image-frame and scale lifecycle transitions.
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

async function ready(page: Page): Promise<TraceResult> {
  const traced = page.waitForResponse((r) => r.url().endsWith('/api/trace') && r.ok());
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  return (await traced).json();
}

async function applyReference(page: Page, trace: TraceResult) {
  await page.locator('.reference-tool').first().locator(':scope > summary').click();
  const points = [
    [trace.bounds.x, trace.bounds.y],
    [trace.bounds.x + 100, trace.bounds.y],
  ];
  for (const [index, point] of points.entries()) {
    await page.getByLabel(`Endpoint ${index + 1} X`, { exact: true }).fill(String(point[0]));
    await page.getByLabel(`Endpoint ${index + 1} Y`, { exact: true }).fill(String(point[1]));
  }
  await page
    .getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true })
    .fill(String((80 * 100) / trace.bounds.width));
  await page.getByRole('button', { name: 'Apply reference scale', exact: true }).click();
  await expect(page.locator('.reference-tool').first().locator(':scope > summary')).toContainText(
    'scale applied',
  );
  await expect
    .poll(async () =>
      Number(await page.getByLabel('Reference width', { exact: true }).inputValue()),
    )
    .toBeCloseTo(80, 8);
}

function narrowerTrace(trace: TraceResult): TraceResult {
  const shrink = (ring: [number, number][]) =>
    ring.map(([x, y]): [number, number] => [trace.bounds.x + (x - trace.bounds.x) * 0.8, y]);
  return {
    ...trace,
    bounds: { ...trace.bounds, width: trace.bounds.width * 0.8 },
    profile: { outer: shrink(trace.profile.outer), holes: trace.profile.holes.map(shrink) },
  };
}

async function saveRecipe(page: Page): Promise<ProjectRecipe> {
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const filename = await (await downloaded).path();
  expect(filename).not.toBeNull();
  return JSON.parse(await readFile(filename!, 'utf8'));
}

async function rebuild(page: Page) {
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
}

test('same-frame retracing keeps measured pixel scale and recomputes outside width', async ({
  page,
}) => {
  const original = await ready(page);
  await applyReference(page, original);
  const before = await saveRecipe(page);
  await page.route('**/api/trace', (route) => route.fulfill({ json: narrowerTrace(original) }));
  await page.getByLabel('Outline detail', { exact: true }).selectOption('fine');
  await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('fine');
  await expect(page.locator('.notice')).toContainText('measured feature scale is retained');
  const after = await saveRecipe(page);
  expect(after.width_mm).toBeCloseTo(64, 8);
  expect(after.reference_calibration).toEqual(before.reference_calibration);
  expect(after.profile.outer).toEqual(narrowerTrace(original).profile.outer);
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
});

test('a failed retrace preserves applied reference evidence and the current model', async ({
  page,
}) => {
  const original = await ready(page);
  await applyReference(page, original);
  await rebuild(page);
  const before = await saveRecipe(page);
  await page.route('**/api/trace', (route) =>
    route.fulfill({ status: 422, json: { detail: 'Fixture trace could not find an outline.' } }),
  );
  await page.getByLabel('Outline detail', { exact: true }).selectOption('fine');
  await expect(page.getByRole('alert')).toContainText('Fixture trace could not find an outline.');
  await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('standard');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  await expect(page.getByText('Previous model · update to apply your changes')).toHaveCount(0);
  const after = await saveRecipe(page);
  expect(after.width_mm).toEqual(before.width_mm);
  expect(after.reference_calibration).toEqual(before.reference_calibration);
  expect(after.profile).toEqual(before.profile);
});

test('a changed working-image frame clears applied provenance and asks for verification', async ({
  page,
}) => {
  const original = await ready(page);
  await applyReference(page, original);
  const newWidth = original.image.width === 1400 ? 1399 : original.image.width + 1;
  await page.route('**/api/trace', (route) =>
    route.fulfill({ json: { ...original, image: { ...original.image, width: newWidth } } }),
  );
  await page.getByLabel('Outline detail', { exact: true }).selectOption('fine');
  await expect(page.locator('.notice')).toContainText('different working-image size');
  await expect(
    page.locator('.reference-tool').first().locator(':scope > summary'),
  ).not.toContainText('scale applied');
  await expect(
    page.getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true }),
  ).toHaveValue('');
  const saved = await saveRecipe(page);
  expect(saved.reference_calibration).toBeUndefined();
  expect(saved.width_mm).toBeCloseTo(80, 8);
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
});

test('fixture AI retrace and Undo restore reference scale after switching to inches', async ({
  page,
}) => {
  await page.route('**/api/assistant/status', (route) =>
    route.fulfill({
      json: {
        running: true,
        models: [
          {
            name: 'fixture:model',
            size_bytes: 1_000_000,
            parameter_size: 'fixture',
            quantization: 'fixture',
          },
        ],
        recommended_model: 'fixture:model',
        detail: 'Fixture response only; no model is run.',
      },
    }),
  );
  await page.route('**/api/assistant/chat', (route) =>
    route.fulfill({
      json: {
        model: 'fixture:model',
        answer: 'Try fine outline detail and review its result.',
        proposal: { detail: 'fine' },
        warnings: [],
        elapsed_seconds: 0.01,
      },
    }),
  );
  const original = await ready(page);
  await applyReference(page, original);
  await rebuild(page);
  const before = await saveRecipe(page);
  await page.route('**/api/trace', (route) => route.fulfill({ json: narrowerTrace(original) }));
  await page.getByRole('button', { name: /^Local AI assistant/ }).click();
  const assistant = page.getByRole('region', { name: 'Local AI assistant', exact: true });
  await assistant
    .getByRole('textbox', { name: 'What would you like help with?' })
    .fill('Improve trace');
  await assistant.getByRole('button', { name: 'Ask local AI', exact: true }).click();
  await assistant.getByRole('button', { name: 'Apply suggestion', exact: true }).click();
  await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('fine');
  await expect
    .poll(async () =>
      Number(await page.getByLabel('Reference width', { exact: true }).inputValue()),
    )
    .toBeCloseTo(64, 8);
  await page.getByRole('button', { name: 'in', exact: true }).click();
  await assistant.getByRole('button', { name: 'Undo suggestion', exact: true }).click();
  await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('standard');
  await expect(page.getByRole('button', { name: 'in', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect
    .poll(async () =>
      Number(await page.getByLabel('Reference width', { exact: true }).inputValue()),
    )
    .toBeCloseTo(80 / 25.4, 5);
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  const restored = await saveRecipe(page);
  expect(restored.width_mm).toBeCloseTo(80, 8);
  expect(restored.reference_calibration).toEqual(before.reference_calibration);
  expect(restored.profile).toEqual(before.profile);
});
