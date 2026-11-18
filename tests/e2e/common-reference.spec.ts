import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import type { ModelResult, ProjectRecipe, TraceResult } from '../../frontend/src/types';

test('a user-marked common object sets scale, keeps numeric evidence, and supports measured overrides', async ({
  page,
}, testInfo) => {
  const jobs = new Set<string>();
  page.on('response', async (response) => {
    if (response.url().endsWith('/api/build') && response.ok()) {
      const model = await response.json().catch(() => null);
      if (model?.id) jobs.add(model.id);
    }
  });
  try {
    await page.goto('/#workbench');
    await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
      timeout: 60_000,
    });
    // A synthetic scene with a 400 px flat part and a separate 100 px circular reference.
    // This exercises explicit user-selected points; no object recognition is involved.
    const dataUrl = await page.evaluate(() => {
      const canvas = document.createElement('canvas');
      canvas.width = 1000;
      canvas.height = 700;
      const context = canvas.getContext('2d')!;
      context.fillStyle = '#fff';
      context.fillRect(0, 0, 1000, 700);
      context.fillStyle = '#30343a';
      context.fillRect(100, 250, 400, 200);
      context.beginPath();
      context.arc(750, 350, 50, 0, Math.PI * 2);
      context.fill();
      return canvas.toDataURL('image/png');
    });
    const traced = page.waitForResponse(
      (response) => response.url().endsWith('/api/trace') && response.ok(),
    );
    await page.getByLabel('Choose photo or project').setInputFiles({
      name: 'synthetic-part-and-reference.png',
      mimeType: 'image/png',
      buffer: Buffer.from(dataUrl.split(',')[1], 'base64'),
    });
    const trace = (await (await traced).json()) as TraceResult;
    await page
      .locator('.reference-tool > summary')
      .filter({ hasText: 'Use a known feature' })
      .click();
    const object = page.getByLabel('Reference object (optional)', { exact: true });
    await object.selectOption('us-quarter');
    await expect(page.getByLabel('Known feature length (mm)', { exact: true })).toHaveValue(
      '24.26',
    );
    const apply = page.getByRole('button', { name: 'Apply reference scale', exact: true });
    await expect(apply).toBeDisabled();
    await expect(page.getByLabel('Reference width', { exact: true })).toHaveValue('');
    await expect(page.locator('#common-reference-help')).toContainText('nominal size');
    await expect(page.locator('#common-reference-help a')).toHaveAttribute(
      'href',
      'https://www.usmint.gov/learn/coins-and-medals/circulating-coins/coin-specifications',
    );
    for (const [label, value] of [
      ['Endpoint 1 X', '700'],
      ['Endpoint 1 Y', '350'],
      ['Endpoint 2 X', '800'],
      ['Endpoint 2 Y', '350'],
    ])
      await page.getByRole('spinbutton', { name: label, exact: true }).fill(value);
    const expectedWidth = (trace.bounds.width * 24.26) / 100;
    await expect(page.locator('.reference-scale-math')).toContainText(
      '24.260 mm ÷ 100.00 px = 0.24260 mm/px',
    );
    await apply.click();
    await expect
      .poll(async () =>
        Number(await page.getByLabel('Reference width', { exact: true }).inputValue()),
      )
      .toBeCloseTo(expectedWidth, 4);
    await page.getByLabel('Thickness', { exact: true }).fill('4');
    const building = page.waitForResponse(
      (response) => response.url().endsWith('/api/build') && response.ok(),
    );
    await page.getByRole('button', { name: 'Build model', exact: true }).click();
    const model = (await (await building).json()) as ModelResult;
    expect(model.dimensions.width).toBeCloseTo(expectedWidth, 6);
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: 'Back to model', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
    const saving = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Save project', exact: true }).click();
    const download = await saving;
    const projectPath = testInfo.outputPath('coin-reference.cad-project.json');
    await download.saveAs(projectPath);
    const recipe = JSON.parse(await readFile(projectPath, 'utf8')) as ProjectRecipe;
    expect(recipe.reference_calibration).toEqual({
      known_length_mm: 24.26,
      reference_points: [
        [700, 350],
        [800, 350],
      ],
      image_size: { width: 1000, height: 700 },
    });
    expect(recipe.width_mm).toBeCloseTo(expectedWidth, 6);
    await page.screenshot({
      path: testInfo.outputPath('common-object-reference.png'),
      fullPage: true,
    });
    await page
      .locator('.reference-tool')
      .first()
      .screenshot({
        path: testInfo.outputPath('common-reference-detail.png'),
      });

    await page.getByRole('button', { name: 'in', exact: true }).click();
    await expect
      .poll(async () =>
        Number(await page.getByLabel('Known feature length (in)', { exact: true }).inputValue()),
      )
      .toBeCloseTo(24.26 / 25.4, 12);
    await object.selectOption('us-penny');
    await expect
      .poll(async () =>
        Number(await page.getByLabel('Known feature length (in)', { exact: true }).inputValue()),
      )
      .toBeCloseTo(19.05 / 25.4, 12);
    await expect(page.getByRole('spinbutton', { name: 'Endpoint 1 X', exact: true })).toHaveValue(
      '',
    );
    await expect(page.getByRole('spinbutton', { name: 'Endpoint 2 X', exact: true })).toHaveValue(
      '',
    );
    await expect(apply).toBeDisabled();
    await page.getByLabel('Known feature length (in)', { exact: true }).fill('0.751');
    await expect(object).toHaveValue('custom');
    await page.getByRole('button', { name: 'mm', exact: true }).click();
    await expect
      .poll(async () =>
        Number(await page.getByLabel('Known feature length (mm)', { exact: true }).inputValue()),
      )
      .toBeCloseTo(0.751 * 25.4, 12);
    // Draft selection and measurement edits do not overwrite the previously applied scale.
    await expect
      .poll(async () =>
        Number(await page.getByLabel('Reference width', { exact: true }).inputValue()),
      )
      .toBeCloseTo(expectedWidth, 4);

    // The project stores numeric evidence, not a claim that a coin was recognized.
    const restoring = page.waitForResponse(
      (response) => response.url().endsWith('/api/build') && response.ok(),
    );
    await page.getByLabel('Choose photo or project').setInputFiles(projectPath);
    await restoring;
    await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.');
    await page
      .locator('.reference-tool > summary')
      .filter({ hasText: 'Use a known feature' })
      .click();
    await expect(object).toHaveValue('custom');
    await expect(object).toBeDisabled();
    await expect(page.getByLabel('Known feature length (mm)', { exact: true })).toHaveValue(
      '24.26',
    );
    await expect(page.getByRole('spinbutton', { name: 'Endpoint 1 X', exact: true })).toHaveValue(
      '700',
    );
    await expect(page.getByRole('spinbutton', { name: 'Endpoint 2 X', exact: true })).toHaveValue(
      '800',
    );
  } finally {
    for (const id of jobs) await page.request.delete(`/api/models/${id}`);
  }
});

test('an unapplied reference draft survives the same image and resets when the image frame changes', async ({
  page,
}) => {
  const jobs = new Set<string>();
  page.on('response', async (response) => {
    if (response.url().endsWith('/api/build') && response.ok()) {
      const model = await response.json().catch(() => null);
      if (model?.id) jobs.add(model.id);
    }
  });
  try {
    const traced = page.waitForResponse(
      (response) => response.url().endsWith('/api/trace') && response.ok(),
    );
    await page.goto('/#workbench');
    const trace = (await (await traced).json()) as TraceResult;
    await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
      timeout: 60_000,
    });
    await page
      .locator('.reference-tool > summary')
      .filter({ hasText: 'Use a known feature' })
      .click();
    const object = page.getByLabel('Reference object (optional)', { exact: true });
    await object.selectOption('us-quarter');
    for (const [label, value] of [
      ['Endpoint 1 X', '100'],
      ['Endpoint 1 Y', '100'],
      ['Endpoint 2 X', '200'],
      ['Endpoint 2 Y', '100'],
    ])
      await page.getByRole('spinbutton', { name: label, exact: true }).fill(value);
    const apply = page.getByRole('button', { name: 'Apply reference scale', exact: true });
    await expect(apply).toBeEnabled();
    let nextTrace = trace;
    await page.route('**/api/trace', (route) => route.fulfill({ json: nextTrace }));
    await page.getByLabel('Outline detail', { exact: true }).selectOption('fine');
    await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('fine');
    await expect(apply).toBeEnabled();
    await expect(object).toHaveValue('us-quarter');
    await expect(page.getByRole('spinbutton', { name: 'Endpoint 1 X', exact: true })).toHaveValue(
      '100',
    );

    // Simulate a rectified image with the same dimensions but changed pixel coordinates.
    const movedImage = await page.evaluate(async (original) => {
      const image = await createImageBitmap(await (await fetch(original.data_url)).blob());
      const canvas = document.createElement('canvas');
      canvas.width = original.width;
      canvas.height = original.height;
      canvas.getContext('2d')!.drawImage(image, 20, 0);
      image.close();
      return canvas.toDataURL('image/png');
    }, trace.image);
    nextTrace = { ...trace, image: { ...trace.image, data_url: movedImage } };
    await page.getByLabel('Outline detail', { exact: true }).selectOption('coarse');
    await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('coarse');
    await expect(object).toHaveValue('custom');
    await expect(page.getByLabel('Known feature length (mm)', { exact: true })).toHaveValue('');
    await expect(page.getByRole('spinbutton', { name: 'Endpoint 1 X', exact: true })).toHaveValue(
      '',
    );
    await expect(page.getByRole('spinbutton', { name: 'Endpoint 2 X', exact: true })).toHaveValue(
      '',
    );
    await expect(apply).toBeDisabled();
  } finally {
    for (const id of jobs) await page.request.delete(`/api/models/${id}`);
  }
});
