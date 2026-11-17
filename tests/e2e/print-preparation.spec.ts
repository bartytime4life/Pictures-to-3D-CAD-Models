import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

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
  await expect(page.getByRole('button', { name: 'Choose an export', exact: true })).toBeEnabled({
    timeout: 60000,
  });
  await page.getByRole('button', { name: 'Prepare for slicing', exact: true }).click();
}

test('process plan builds, persists, and is reversible through design history', async ({
  page,
}) => {
  await ready(page);
  await page.getByRole('button', { name: 'Fine surface', exact: false }).click();
  await page.getByRole('combobox', { name: 'Supports', exact: true }).selectOption('build_plate');
  await page.getByRole('combobox', { name: 'Bed adhesion', exact: true }).selectOption('brim');
  await expect(
    page.getByRole('button', { name: 'Review slicer handoff', exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByText('Update the preview to check this plan.', { exact: true }),
  ).toBeVisible();
  const built = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
  await page.getByRole('button', { name: 'Update preparation preview', exact: true }).click();
  const result = await (await built).json();
  expect(result.design).toMatchObject({
    layer_height_mm: 0.12,
    wall_count: 3,
    infill_percent: 20,
    supports: 'build_plate',
    adhesion: 'brim',
  });
  const recipe = await page.request.get(`/api/download/${result.id}/project`);
  expect((await recipe.json()).design).toMatchObject(result.design);
  await expect(page.getByRole('img', { name: /Top-down bed preview/ })).toBeVisible();
  await page.getByRole('button', { name: 'Review slicer handoff', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Prepare in your slicer' })).toContainText(
    '0.12 mm layers · 3 walls · 20% infill',
  );
  for (const name of ['OrcaSlicer', 'UltiMaker Cura']) {
    await page.getByRole('radio', { name: new RegExp(name) }).check();
    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: `Download ${name} handoff ZIP`, exact: true }).click();
    expect((await download).suggestedFilename()).toMatch(/\.zip$/);
  }
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  await page.getByRole('button', { name: 'Edit model', exact: true }).click();
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await page.getByRole('button', { name: 'Prepare for slicing', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Bed adhesion', exact: true })).toHaveValue(
    'none',
  );
  await expect(page.getByRole('button', { name: 'Update preparation preview' })).toBeEnabled();
});

test('invalid process drafts do not change saved plan; smaller nozzle keeps plan valid', async ({
  page,
}) => {
  await ready(page);
  const height = page.getByLabel('Layer height (mm)', { exact: true });
  await height.fill('0.9');
  await height.press('Tab');
  await expect(height).toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByText(/Current plan still uses 0.2/)).toBeVisible();
  await height.press('Escape');
  await expect(height).toHaveValue('0.2');
  await page.getByRole('button', { name: 'Printer & split settings' }).click();
  await page.getByLabel('Nozzle diameter (mm)', { exact: true }).fill('');
  await page.getByLabel('Nozzle diameter (mm)', { exact: true }).fill('0.6');
  await expect(height).toHaveValue('0.2');
  await page.getByLabel('Nozzle diameter (mm)', { exact: true }).fill('0.1');
  await expect(height).toHaveValue('0.1');
  await expect(page.getByRole('button', { name: 'Update preparation preview' })).toBeEnabled();
});

test('preparation controls and handoff are accessible on a narrow screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  await page
    .getByRole('heading', { name: 'Prepare for slicing', exact: true })
    .scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  const results = await new AxeBuilder({ page }).include('.print-preparation').analyze();
  expect(results.violations).toEqual([]);
  await page.getByRole('button', { name: 'Quick prototype', exact: false }).click();
  await expect(page.getByLabel('Layer height (mm)')).toHaveValue('0.28');
});

test('bed inspection changes the view without changing the model or saved process plan', async ({
  page,
}) => {
  await ready(page);
  const panel = page.locator('.print-preparation');
  const preview = panel.getByRole('img', { name: /Top-down bed preview/ });
  const originalName = await preview.getAttribute('aria-label');
  const builds: string[] = [];
  page.on('request', (request) => {
    if (request.url().endsWith('/api/build')) builds.push(request.url());
  });
  const originalLayers = await panel.getByLabel('Layer height (mm)', { exact: true }).inputValue();
  await panel.getByRole('button', { name: '45°', exact: true }).click();
  await expect(preview).toHaveAccessibleName(/preview turn 45.0 degrees/);
  const rotation = panel.getByRole('slider', { name: /Preview turn/ });
  await rotation.fill('30');
  await expect(preview).toHaveAccessibleName(/preview turn 30.0 degrees/);
  for (const label of ['Grid', 'Margin', 'Dimensions']) {
    await panel.getByRole('checkbox', { name: label, exact: true }).uncheck();
    await expect(panel.getByRole('checkbox', { name: label, exact: true })).not.toBeChecked();
  }
  await panel.getByRole('button', { name: 'Reset view', exact: true }).click();
  await expect(preview).toHaveAccessibleName(originalName!);
  for (const label of ['Grid', 'Margin', 'Dimensions']) {
    await expect(panel.getByRole('checkbox', { name: label, exact: true })).toBeChecked();
  }
  expect(builds).toEqual([]);
  await expect(panel.getByLabel('Layer height (mm)', { exact: true })).toHaveValue(originalLayers);
  await expect(
    page.getByRole('button', { name: 'Review slicer handoff', exact: true }),
  ).toBeEnabled();
});
