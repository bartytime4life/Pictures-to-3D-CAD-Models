import { test, expect } from '@playwright/test';
import { LAB_DEFAULTS } from '../../frontend/src/science';
import { EMPTY_NOTEBOOK } from '../../frontend/src/knowledge';

test('science deep links open the named experiment while plain studio switches preserve selection', async ({
  page,
}) => {
  await page.goto('/#science?experiment=fit');
  await expect(page.getByRole('button', { name: /Measured fit/ })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await page.getByRole('button', { name: /Layer stack/ }).click();
  await page.getByRole('link', { name: 'Knowledge base', exact: true }).click();
  await page.getByRole('button', { name: /Measure from a known object/ }).click();
  await page.getByRole('link', { name: 'Explore pixel scale', exact: true }).click();
  await expect(page.getByRole('button', { name: /Pixel scale/ })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await page.getByRole('link', { name: 'Knowledge base', exact: true }).click();
  await page.getByRole('button', { name: /Use a coupon to investigate fit/ }).click();
  await page.getByRole('link', { name: 'Open the fit experiment', exact: true }).click();
  await expect(page.getByRole('button', { name: /Measured fit/ })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await page.getByRole('button', { name: /Layer stack/ }).click();
  await page.getByRole('link', { name: 'Knowledge base', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Knowledge base', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Science lab', exact: true }).click();
  await expect(page.getByRole('button', { name: /Layer stack/ })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await page.goto('/#science?experiment=scale');
  await expect(page.getByRole('button', { name: /Pixel scale/ })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
});

test('pending notebook imports cannot race undo or recovery replacement', async ({ page }) => {
  await page.addInitScript(() => {
    const originalText = File.prototype.text;
    File.prototype.text = async function () {
      if (this.name === 'pending-notebook.json')
        await new Promise<void>((resolve) => {
          (window as typeof window & { releaseNotebookImport?: () => void }).releaseNotebookImport =
            resolve;
        });
      return originalText.call(this);
    };
  });
  await page.goto('/#knowledge');
  const input = page.getByLabel('Import knowledge notebook JSON', { exact: true });
  const notes = page.getByRole('textbox', {
    name: 'Your notes for Capture a traceable flat part',
    exact: true,
  });
  await notes.fill('Original notes');
  const notebook = (text: string) => ({ ...EMPTY_NOTEBOOK, notes: { capture: text } });
  await input.setInputFiles({
    name: 'first.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(notebook('First import'))),
  });
  await expect(notes).toHaveValue('First import');
  const undo = page.getByRole('button', { name: 'Undo notebook import', exact: true });
  await expect(undo).toBeEnabled();
  await input.setInputFiles({
    name: 'pending-notebook.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(notebook('Second import'))),
  });
  await expect(undo).toBeDisabled();
  await expect(notes).toBeDisabled();
  await expect(notes).toHaveValue('First import');
  await page.evaluate(() =>
    (window as typeof window & { releaseNotebookImport?: () => void }).releaseNotebookImport?.(),
  );
  await expect(notes).toHaveValue('Second import');
  await undo.click();
  await expect(notes).toHaveValue('First import');

  await page.evaluate(() => localStorage.setItem('pictures-to-cad.notebook.v1', '{broken'));
  await page.reload();
  const fresh = page.getByRole('button', { name: 'Start a fresh notebook', exact: true });
  await expect(fresh).toBeEnabled();
  await input.setInputFiles({
    name: 'pending-notebook.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(notebook('Recovered import'))),
  });
  await expect(fresh).toBeDisabled();
  await page.evaluate(() =>
    (window as typeof window & { releaseNotebookImport?: () => void }).releaseNotebookImport?.(),
  );
  await expect(notes).toHaveValue('Recovered import');
  await expect(fresh).toHaveCount(0);
});

test('one and two layer diagram bands stay inside the SVG and above the bed', async ({ page }) => {
  await page.goto('/#science?experiment=layers');
  for (const [height, count] of [
    [0.1, 1],
    [0.4, 2],
  ]) {
    await page.getByLabel('Part height (mm)', { exact: true }).fill(String(height));
    const diagram = page.getByRole('img', { name: new RegExp(`^${count} conceptual layers`) });
    const bands = diagram.locator('rect');
    await expect(bands).toHaveCount(count);
    const coordinates = await bands.evaluateAll((elements) =>
      elements.map((element) => ({
        y: Number(element.getAttribute('y')),
        height: Number(element.getAttribute('height')),
      })),
    );
    for (const band of coordinates) {
      expect(band.y).toBeGreaterThanOrEqual(0);
      expect(band.height).toBeGreaterThan(0);
      expect(band.y + band.height).toBeLessThanOrEqual(185);
    }
  }
  await expect(page.getByLabel('First layer height (mm)', { exact: true })).toHaveValue(
    String(LAB_DEFAULTS.layers.firstLayerMm),
  );
});
