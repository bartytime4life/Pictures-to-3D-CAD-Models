import { test, expect } from '@playwright/test';

const jobs = new Set<string>();
const evidence = {
  known_length_mm: 40,
  reference_points: [
    [10, 20],
    [60, 20],
  ],
  image_size: { width: 100, height: 60 },
};

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

test('restored and edited measurement notes reach the generated exports without changing geometry', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  const imported = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'measured.cad-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(
      JSON.stringify({
        format: 'pictures-to-cad',
        version: 1,
        name: 'Reference plate',
        profile: {
          outer: [
            [0, 0],
            [100, 0],
            [100, 60],
            [0, 60],
          ],
          holes: [],
        },
        width_mm: 80,
        thickness_mm: 4,
        reference_calibration: evidence,
        measured_height_mm: 47,
      }),
    ),
  });
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  const first = await (await imported).json();
  const recipe = await (await page.request.get(first.downloads.project)).json();
  expect(recipe.reference_calibration).toEqual(evidence);
  expect(recipe.measured_height_mm).toBe(47);

  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Independent height check' })
    .click();
  const height = page.getByRole('spinbutton', {
    name: 'Measured outside height (mm)',
    exact: true,
  });
  await height.fill('49');
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
  const updated = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  const second = await (await updated).json();
  expect(second.dimensions).toEqual(first.dimensions);
  const updatedRecipe = await (await page.request.get(second.downloads.project)).json();
  expect(updatedRecipe.reference_calibration).toEqual(evidence);
  expect(updatedRecipe.measured_height_mm).toBe(49);
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  await height.fill('0');
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeDisabled();
  await height.fill('');
  const cleared = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  const third = await (await cleared).json();
  expect(
    (await (await page.request.get(third.downloads.project)).json()).measured_height_mm,
  ).toBeUndefined();
});
