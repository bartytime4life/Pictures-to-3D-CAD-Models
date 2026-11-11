import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { DEFAULT_DESIGN } from '../../frontend/src/design';

const arc = (cx: number, start: number) =>
  Array.from({ length: 61 }, (_, k) => {
    const angle = start + (k * Math.PI) / 60;
    return [cx + 10 * Math.cos(angle), 10 + 10 * Math.sin(angle)];
  });
const recipe = {
  format: 'pictures-to-cad',
  version: 3,
  name: 'Fitted capsule',
  profile: {
    outer: [
      [10, 0],
      [115, 0],
      ...arc(115, -Math.PI / 2).slice(1),
      [10, 20],
      ...arc(10, Math.PI / 2).slice(1, -1),
    ],
    holes: [],
    primitives: {
      outer: [
        { kind: 'line', start: [10, 0], end: [115, 0] },
        { kind: 'arc', start: [115, 0], mid: [125, 10], end: [115, 20] },
        { kind: 'line', start: [115, 20], end: [10, 20] },
        { kind: 'arc', start: [10, 20], mid: [0, 10], end: [10, 0] },
      ],
      holes: [],
    },
  },
  width_mm: 125,
  thickness_mm: 4,
  design: { ...DEFAULT_DESIGN, bed_width_mm: 110, bed_depth_mm: 110 },
};

for (const mobile of [false, true]) {
  test(`fitted curve placement preserves exact geometry and explains its outer bound (${mobile ? 'mobile' : 'desktop'})`, async ({
    page,
    request,
  }, testInfo) => {
    const jobs = new Set<string>();
    page.on('response', async (response) => {
      if (response.url().endsWith('/api/build') && response.ok())
        jobs.add((await response.json()).id);
    });
    try {
      if (mobile) await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/');
      await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
        timeout: 60_000,
      });
      const pending = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
      await page.getByLabel('Choose photo or project').setInputFiles({
        name: 'fitted-capsule.json',
        mimeType: 'application/json',
        buffer: Buffer.from(JSON.stringify(recipe)),
      });
      const model = await (await pending).json();
      await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.');
      expect(model.geometry).toMatchObject({ kind: 'fitted', arcs: 2 });
      expect(model.parts).toHaveLength(1);
      expect(model.parts[0].bed_fit).toMatchObject({
        status: 'fits',
        basis: 'curve_envelope',
        enclosure_directions: 256,
      });
      await page.getByRole('button', { name: /^Design & print/ }).click();
      const table = page.getByRole('table', { name: 'Built parts · dimensions in millimeters' });
      await expect(table.getByRole('cell', { name: '125 × 20 × 4', exact: true })).toBeVisible();
      const placement = table.locator('.part-placement');
      await expect(placement.locator('summary')).toHaveText('Fits after ≈45° turn');
      await placement.locator('summary').focus();
      await page.keyboard.press('Enter');
      await expect(placement).toContainText('Conservative rotated footprint: 94.25 × 94.25 mm.');
      await expect(placement).toContainText('Uses an outer enclosure of the fitted curves.');
      await expect(placement).toContainText('Geometry exports keep their original orientation.');
      await expect(
        page.getByRole('spinbutton', { name: 'Reference width', exact: true }),
      ).toHaveValue(/^125(?:\.0+)?$/);
      await expect(
        page.getByRole('region', { name: 'Suggested split plan', exact: true }),
      ).toHaveCount(0);
      const saved = await request.get(model.downloads.project);
      const savedRecipe = await saved.json();
      expect(savedRecipe.profile.primitives).toEqual(recipe.profile.primitives);
      expect(savedRecipe.design.output_mode).toBe('single');
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      ).toBe(true);
      expect(
        (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
          .violations,
      ).toEqual([]);
      await table.screenshot({ path: testInfo.outputPath('curve-placement.png') });
      await page.getByLabel('Bed width (mm)', { exact: true }).fill('90');
      await expect(table).toHaveCount(0);
      const rebuilt = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
      await page.getByRole('button', { name: 'Update model', exact: true }).click();
      const result = await (await rebuilt).json();
      expect(result.print_fit.status).toBe('unknown');
      expect(result.geometry.kind).toBe('fitted');
      expect(result.dimensions).toEqual(model.dimensions);
      await page.getByRole('button', { name: 'Back to model', exact: true }).click();
      await expect(table.locator('summary')).toHaveText('Check in slicer');
    } finally {
      for (const id of jobs) await request.delete(`/api/models/${id}`);
    }
  });
}
