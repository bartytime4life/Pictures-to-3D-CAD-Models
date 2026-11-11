import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

// tests/e2e/fixtures/plate-on-a4.jpg is rendered by tests/synthetic.py: a 120 x 70 x 4 mm
// plate (4 x D6 holes, a D22 bore, a 24 x 8 slot, R8 corners) on an A4 sheet, photographed
// with a 22-degree tilt, lens distortion, uneven light and visible side walls.
const photo = path.resolve('tests/e2e/fixtures/plate-on-a4.jpg');
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

async function sampleReady(page: Page) {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
}

test('a photo on an A4 sheet is scaled by the sheet and exported with exact circles and arcs', async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await sampleReady(page);

  await page.getByRole('button', { name: 'Change photo' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Scale reference').selectOption('a4');
  const scan = await new AxeBuilder({ page }).include('dialog').analyze();
  expect(scan.violations).toEqual([]);
  await page.getByLabel('Choose photo or project').setInputFiles(photo);

  // The sheet supplies the width; the user supplies only the thickness. Until the
  // thickness is known the visible side walls still widen the outline (about 121.5 mm).
  const width = page.getByRole('spinbutton', { name: 'Reference width' });
  await expect(width).toHaveValue(/^12[01]\.\d+/, { timeout: 30_000 });
  await expect(page.getByText(/From the A4 sheet/)).toBeVisible();
  await expect(page.getByText(/6 through holes detected · fitted/)).toBeVisible();

  // Building with a thickness re-traces once to remove the visible side walls.
  await page.getByLabel('Thickness', { exact: true }).fill('4');
  const traces: number[] = [];
  page.on('response', async (response) => {
    if (response.url().endsWith('/api/trace') && response.ok()) {
      const body = await response.json().catch(() => null);
      traces.push(body?.profile?.reference?.thickness_mm ?? 0);
    }
  });
  await page.getByRole('button', { name: 'Build model', exact: true }).click();
  const exportDialog = page.getByRole('dialog');
  await expect(exportDialog.getByText('5 circles · 6 arcs · 6 lines')).toBeVisible({
    timeout: 60_000,
  });
  expect(traces).toEqual([4]);
  expect(Math.abs(Number(await width.inputValue()) - 120)).toBeLessThan(0.1);
  await expect(page.getByText(/6 through holes detected · fitted 5 circles, 6 arcs/)).toBeVisible();
  const size = await exportDialog
    .locator('.export-summary div')
    .first()
    .locator('strong')
    .innerText();
  const [w, h, t] = size.match(/[\d.]+/g)!.map(Number);
  expect(Math.abs(w - 120)).toBeLessThan(0.1);
  expect(Math.abs(h - 70)).toBeLessThan(0.1);
  expect(t).toBe(4);

  await page.getByText('Drawings & source files', { exact: true }).click();
  for (const format of ['STEP', 'DXF', 'SVG', 'PDF', 'OpenSCAD']) {
    const downloadEvent = page.waitForEvent('download');
    await page.locator('.export-row').filter({ hasText: format }).click();
    const download = await downloadEvent;
    const output = testInfo.outputPath(download.suggestedFilename());
    await download.saveAs(output);
    const text = (await readFile(output)).toString('latin1');
    if (format === 'STEP') expect(text.match(/CYLINDRICAL_SURFACE/g)).toHaveLength(11);
    if (format === 'DXF') {
      expect(text).toContain('CIRCLE');
      expect(text).toContain('ARC');
      expect(text).not.toContain('LWPOLYLINE');
    }
    if (format === 'SVG') {
      // True circles and arcs at one unit per millimetre, not a traced polyline.
      expect(text.match(/<circle /g)).toHaveLength(5);
      expect(text).toMatch(/ A [\d.]+ [\d.]+ 0 0 [01] /);
      const [, svgWidth] = text.match(/<svg [^>]*width="([\d.]+)mm"/)!;
      expect(Math.abs(Number(svgWidth) - 2 - w)).toBeLessThan(0.01);
    }
    if (format === 'PDF') {
      expect(text.startsWith('%PDF-1.4')).toBe(true);
      // 210 x 279.4 mm: the area A4 and US Letter share.
      expect(text).toContain('/MediaBox [0 0 595.276 792]');
      expect(text).toContain('mm, drawn at 1:1');
    }
    if (format === 'OpenSCAD') expect(text.match(/circle\(r = /g)).toHaveLength(5);
  }
  await exportDialog.getByRole('button', { name: 'Close dialog' }).click();

  // The saved project keeps the fitted geometry and how it was measured.
  const saved = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save project' }).click();
  const project = JSON.parse(
    await readFile(await (await saved).path()).then((data) => data.toString('utf8')),
  );
  expect(project.version).toBe(3);
  expect(project.profile.reference.kind).toBe('a4');
  expect(project.profile.reference.thickness_mm).toBe(4);
  expect(project.profile.primitives.holes).toHaveLength(6);
  expect(errors).toEqual([]);
});

test('the outline dialog switches an existing photo to a sheet reference', async ({ page }) => {
  await sampleReady(page);
  await page.getByRole('button', { name: 'Change photo' }).click();
  // Without a reference the full-frame photo cannot be traced; the error says what to do.
  await page.getByLabel('Choose photo or project').setInputFiles(photo);
  await expect(page.getByRole('alert')).toContainText('choose that sheet under Scale reference');
  await page.getByRole('button', { name: 'Change photo' }).click();
  await page.getByRole('dialog').getByLabel('Scale reference').selectOption('letter');
  await page.getByLabel('Choose photo or project').setInputFiles(photo);
  // The photo is traced to the size the user chose, but its proportions reveal the mistake.
  await expect(page.getByText(/From the US Letter sheet/)).toBeVisible({ timeout: 30_000 });
  await expect(
    page
      .locator('p.notice')
      .getByText(/proportions in the photo differ from the chosen size by -8\.5 %/),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Adjust outline' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByLabel('Scale reference')).toHaveValue('letter');
  await expect(dialog.getByLabel('Contrast threshold')).toBeDisabled();
  await dialog.getByLabel('Scale reference').selectOption('a4');
  await dialog.getByRole('button', { name: 'Apply trace' }).click();
  await expect(page.getByText(/From the A4 sheet/)).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('p.notice')).toContainText(/the width comes from the sheet/i);
});
