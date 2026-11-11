import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { DEFAULT_DESIGN } from '../../frontend/src/design';
import type { ProjectRecipe, ReferenceCalibration } from '../../frontend/src/types';

// A 7 px reference spans 2000 * 7 / 1379 mm on this synthetic rectangular profile.
// Keeping full numeric precision gives exactly 2000 mm outside width. Reducing the
// reference to 12 significant figures puts the draft just beyond the supported limit.
const reference: ReferenceCalibration = {
  known_length_mm: (2000 * 7) / 1379,
  reference_points: [
    [0, 0],
    [7, 0],
  ],
  image_size: { width: 1379, height: 100 },
};
const fixture: ProjectRecipe = {
  format: 'pictures-to-cad',
  version: 2,
  name: 'Reference at maximum width',
  profile: {
    outer: [
      [0, 0],
      [1379, 0],
      [1379, 100],
      [0, 100],
    ],
    holes: [],
  },
  width_mm: 2000,
  thickness_mm: 4,
  design: { ...DEFAULT_DESIGN, bed_width_mm: 2500 },
  reference_calibration: reference,
};

// The sample and restored rectangle use the real CAD service; clean up every build.
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

async function openReference(page: Page) {
  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Use a known feature' })
    .click();
}

async function saveRecipe(page: Page, testInfo: TestInfo) {
  const event = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const download = await event;
  const file = testInfo.outputPath('reference-at-maximum-width.cad-project.json');
  await download.saveAs(file);
  return { file, recipe: JSON.parse(await readFile(file, 'utf8')) as ProjectRecipe };
}

test('boundary reference stays applicable across unit changes and recipe restoration', async ({
  page,
}, testInfo) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'reference-at-maximum-width.cad-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(fixture)),
  });
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  await openReference(page);
  const apply = page.getByRole('button', { name: 'Apply reference scale', exact: true });
  await expect(
    page.getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true }),
  ).toHaveValue(String(reference.known_length_mm));
  await expect(apply).toBeEnabled();

  for (const unit of ['in', 'mm', 'in', 'mm'] as const) {
    await page.getByRole('button', { name: unit, exact: true }).click();
    await expect(
      page.getByRole('spinbutton', { name: `Known feature length (${unit})`, exact: true }),
    ).toHaveValue(String(reference.known_length_mm / (unit === 'in' ? 25.4 : 1)));
    await expect(apply).toBeEnabled();
    await expect(page.locator('.reference-tool').first()).not.toContainText('beyond 0.1–2000 mm');
  }

  await apply.click();
  const saved = await saveRecipe(page, testInfo);
  expect(saved.recipe.width_mm).toBe(2000);
  expect(saved.recipe.reference_calibration).toEqual(reference);
  await page.getByLabel('Choose photo or project').setInputFiles(saved.file);
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  await openReference(page);
  await expect(
    page.getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true }),
  ).toHaveValue(String(reference.known_length_mm));
  await expect(apply).toBeEnabled();

  // A genuine increase still exceeds the limit; editing a reference draft does not
  // silently resize the current CAD model or discard its valid saved scale.
  await page
    .getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true })
    .fill(String(reference.known_length_mm * 1.001));
  await expect(apply).toBeDisabled();
  await expect(page.locator('.reference-tool').first()).toContainText('beyond 0.1–2000 mm');
  await expect(page.getByLabel('Reference width', { exact: true })).toHaveValue('2000.0000');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
});
