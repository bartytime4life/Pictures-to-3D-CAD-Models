import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { DEFAULT_DESIGN } from '../../frontend/src/design';

const recipe = {
  format: 'pictures-to-cad',
  version: 2,
  name: 'Split planning example',
  profile: {
    outer: [
      [0, 0],
      [250, 0],
      [250, 80],
      [0, 80],
    ],
    holes: [
      [
        [20, 20],
        [30, 20],
        [30, 30],
        [20, 30],
      ],
    ],
  },
  width_mm: 250,
  thickness_mm: 4,
  design: { ...DEFAULT_DESIGN, bed_width_mm: 150, bed_depth_mm: 110 },
};

async function importRecipe(page: Page) {
  const pending = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'split-planning.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(recipe)),
  });
  const model = await (await pending).json();
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.');
  return model;
}

for (const mobile of [false, true]) {
  test(`split proposal requires apply and rebuild and preserves measured geometry (${mobile ? 'mobile' : 'desktop'})`, async ({
    page,
    request,
  }, testInfo) => {
    const jobs = new Set<string>();
    let builds = 0;
    page.on('response', async (response) => {
      if (response.url().endsWith('/api/build') && response.ok()) {
        builds++;
        jobs.add((await response.json()).id);
      }
    });
    try {
      if (mobile) await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/');
      await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
        timeout: 60_000,
      });
      const original = await importRecipe(page);
      expect(original.print_fit.status).toBe('too_large');
      expect(original.parts).toHaveLength(1);
      expect(original.split_plan).toMatchObject({
        status: 'suggested',
        columns: 2,
        rows: 1,
        piece_count: 2,
        grids_failed: 0,
      });
      await page.getByRole('button', { name: /^Design & print/ }).click();
      const proposal = page.getByRole('region', { name: 'Suggested split plan', exact: true });
      await expect(proposal).toContainText('Try a 2 × 1 split · 2 pieces');
      await expect(proposal).toContainText('rebuild to generate');
      await expect(page.getByRole('combobox', { name: 'Output', exact: true })).toHaveValue(
        'single',
      );
      const saved = await page.request.get(original.downloads.project);
      expect((await saved.json()).design.output_mode).toBe('single');
      if (!mobile) {
        await page.getByLabel('Bed margin (mm)', { exact: true }).fill('6');
        await expect(proposal).toHaveCount(0);
        await expect(
          page.getByRole('button', { name: 'Use suggested split', exact: true }),
        ).toHaveCount(0);
        await importRecipe(page);
        await expect(proposal).toBeVisible();
      }
      await proposal.screenshot({ path: testInfo.outputPath('split-proposal.png') });
      expect(
        (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
          .violations,
      ).toEqual([]);
      const beforeApply = builds;
      await proposal.getByRole('button', { name: 'Use suggested split', exact: true }).focus();
      await page.keyboard.press('Enter');
      await expect(proposal).toHaveCount(0);
      await expect(page.getByRole('combobox', { name: 'Output', exact: true })).toHaveValue(
        'split',
      );
      await expect(page.getByLabel('Columns', { exact: true })).toHaveValue('2');
      await expect(page.getByLabel('Rows', { exact: true })).toHaveValue('1');
      await expect(
        page.getByRole('spinbutton', { name: 'Reference width', exact: true }),
      ).toHaveValue(/^250(?:\.0+)?$/);
      await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue(/^4(?:\.0+)?$/);
      await expect(page.getByText('Build to check printer fit', { exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Review export', exact: true })).toHaveCount(0);
      expect(builds).toBe(beforeApply);
      const pending = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
      await page.getByRole('button', { name: 'Update model', exact: true }).click();
      const rebuilt = await (await pending).json();
      expect(rebuilt.parts).toHaveLength(2);
      expect(rebuilt.print_fit.status).toBe('fits');
      expect(rebuilt.dimensions).toEqual(original.dimensions);
      expect(rebuilt.volume_mm3).toBeCloseTo(original.volume_mm3, 5);
      expect(rebuilt.split_plan).toBeUndefined();
      await page.getByRole('button', { name: 'Back to model', exact: true }).click();
      await expect(
        page.getByText('Built parts fit the selected build volume', { exact: true }),
      ).toBeVisible();
      await expect(
        page
          .getByRole('table', { name: 'Built parts · dimensions in millimeters' })
          .locator('tbody tr'),
      ).toHaveCount(2);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      ).toBe(true);
    } finally {
      for (const id of jobs) await request.delete(`/api/models/${id}`);
    }
  });
}
