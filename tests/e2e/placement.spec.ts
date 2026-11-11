import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { DEFAULT_DESIGN } from '../../frontend/src/design';

for (const mobile of [false, true]) {
  test(`diagonal placement is inspectable, keeps measurements and invalidates after edits (${mobile ? 'mobile' : 'desktop'})`, async ({
    page,
    request,
  }, testInfo) => {
    const jobs = new Set<string>();
    page.on('response', async (response) => {
      if (response.url().endsWith('/api/build') && response.ok()) {
        const result = await response.json();
        jobs.add(result.id);
      }
    });
    try {
      if (mobile) await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/');
      await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
        timeout: 60_000,
      });
      await page.getByLabel('Choose photo or project').setInputFiles({
        name: 'diagonal-bar.json',
        mimeType: 'application/json',
        buffer: Buffer.from(
          JSON.stringify({
            format: 'pictures-to-cad',
            version: 2,
            name: 'Diagonal bar',
            profile: {
              outer: [
                [0, 0],
                [125, 0],
                [125, 10],
                [0, 10],
              ],
              holes: [],
            },
            width_mm: 125,
            thickness_mm: 4,
            design: { ...DEFAULT_DESIGN, bed_width_mm: 110, bed_depth_mm: 110 },
          }),
        ),
      });
      await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
        timeout: 60_000,
      });
      await page.getByRole('button', { name: /^Design & print/ }).click();
      const table = page.getByRole('table', { name: 'Built parts · dimensions in millimeters' });
      const placement = table.locator('.part-placement');
      await expect(placement.locator('summary')).toContainText(/Fits after ≈[\d.]+° turn/);
      await placement.locator('summary').focus();
      await page.keyboard.press('Enter');
      await expect(placement.getByText(/Rotated footprint:/)).toBeVisible();
      await expect(placement).toContainText('counterclockwise');
      await expect(placement).toContainText('Geometry exports keep their original orientation.');
      await expect(placement).toContainText('Uses the built polygon outline.');
      await expect(
        page.getByRole('spinbutton', { name: 'Reference width', exact: true }),
      ).toHaveValue(/^125(?:\.0+)?$/);
      await expect(page.locator('.dimensions-summary')).toContainText('125.00 mm (W)');
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      ).toBe(true);
      await table.screenshot({ path: testInfo.outputPath('diagonal-placement.png') });
      expect(
        (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
          .violations,
      ).toEqual([]);
      await page.getByLabel('Bed width (mm)', { exact: true }).fill('90');
      await expect(table).toHaveCount(0);
      await expect(page.getByText('Build to check printer fit', { exact: true })).toBeVisible();
      const result = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
      await page.getByRole('button', { name: 'Update model', exact: true }).click();
      expect((await (await result).json()).print_fit.status).toBe('too_large');
      await page.getByRole('button', { name: 'Back to model', exact: true }).click();
      await expect(table.locator('.part-placement summary')).toHaveText('Too large');
    } finally {
      for (const id of jobs) await request.delete(`/api/models/${id}`);
    }
  });
}
