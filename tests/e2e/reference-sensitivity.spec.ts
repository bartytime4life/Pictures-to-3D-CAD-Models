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

async function openScenario(page: Page, span = 50) {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'reference.cad-project.json',
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
        reference_calibration: {
          known_length_mm: span * 0.8,
          reference_points: [
            [10, 20],
            [10 + span, 20],
          ],
          image_size: { width: 100, height: 60 },
        },
      }),
    ),
  });
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Use a known feature' })
    .click();
  await page.getByText('Explore endpoint placement', { exact: true }).click();
}

test('sensitivity uses exact span scenarios, converts units and leaves the current project unchanged', async ({
  page,
}) => {
  await openScenario(page);
  const values = page.locator('.sensitivity-values dd');
  await expect(values).toHaveText(['76.923 mm', '80.000 mm', '83.333 mm']);
  await expect(page.locator('.sensitivity-scale')).toContainText('50.0 px');
  await expect(page.locator('.sensitivity-scale')).toContainText('0.8000 mm/px');
  const shift = page.getByRole('spinbutton', {
    name: 'Assumed shift per endpoint (px)',
    exact: true,
  });
  await shift.fill('0.5');
  await expect(values).toHaveText(['78.431 mm', '80.000 mm', '81.633 mm']);
  await page.getByRole('button', { name: 'in', exact: true }).click();
  await expect(shift).toBeVisible();
  await expect(shift).toHaveValue('0.5');
  await expect(values).toHaveText(['3.0878 in', '3.1496 in', '3.2139 in']);
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  await expect(page.locator('.reference-sensitivity')).toContainText('not a measured error range');
  const savedEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const saved = await savedEvent;
  const file = await saved.path();
  const { readFile } = await import('node:fs/promises');
  const recipe = JSON.parse(await readFile(file!, 'utf8'));
  expect(recipe.width_mm).toBe(80);
  expect(recipe.reference_calibration.reference_points).toEqual([
    [10, 20],
    [60, 20],
  ]);
  expect(JSON.stringify(recipe)).not.toContain('offset');
});

test('a collapsing span and invalid shifts cannot display a finite scenario', async ({ page }) => {
  await openScenario(page, 2);
  await expect(page.locator('#reference-sensitivity-result')).toContainText(
    'collapse the reference span to zero',
  );
  await expect(page.locator('.sensitivity-plot')).toHaveCount(0);
  const shift = page.getByRole('spinbutton', {
    name: 'Assumed shift per endpoint (px)',
    exact: true,
  });
  await shift.fill('0');
  await expect(page.locator('.sensitivity-values dd')).toHaveText([
    '80.000 mm',
    '80.000 mm',
    '80.000 mm',
  ]);
  await expect(page.locator('.sensitivity-range')).toHaveAttribute('x1', '240');
  await expect(page.locator('.sensitivity-range')).toHaveAttribute('x2', '240');
  for (const value of ['', '-1', '6']) {
    await shift.fill(value);
    await expect(shift).toHaveAttribute('aria-invalid', 'true');
    await expect(page.locator('.sensitivity-plot')).toHaveCount(0);
  }
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
});

test('expanded sensitivity is keyboard accessible and fits a phone viewport', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openScenario(page);
  const shift = page.getByRole('spinbutton', {
    name: 'Assumed shift per endpoint (px)',
    exact: true,
  });
  await shift.focus();
  await page.keyboard.press('ArrowUp');
  await expect(shift).toHaveValue('1.1');
  const scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(scan.violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page
    .locator('.reference-sensitivity')
    .screenshot({ path: testInfo.outputPath('reference-sensitivity-mobile.png') });
});
