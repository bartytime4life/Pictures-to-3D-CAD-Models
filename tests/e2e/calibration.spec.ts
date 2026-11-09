import { expect, test, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';
import type {
  ModelResult,
  ProjectRecipe,
  ReferenceCalibration,
  TraceResult,
} from '../../frontend/src/types';

// Use the synthetic sample and real CAD service. Expected dimensions come from the saved
// outline and independently measured endpoint span, not the application's calculation helper.
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

async function ready(page: Page): Promise<TraceResult> {
  const traceResponse = page.waitForResponse(
    (response) => response.url().endsWith('/api/trace') && response.ok(),
  );
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  await expect(page.locator('canvas[data-model-ready="true"]')).toBeVisible();
  return (await traceResponse).json();
}

async function saveRecipe(page: Page, testInfo: TestInfo, name: string) {
  const event = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const download = await event;
  const file = testInfo.outputPath(name);
  await download.saveAs(file);
  return { file, recipe: JSON.parse(await readFile(file, 'utf8')) as ProjectRecipe };
}

function calibrationFor(trace: TraceResult, recipe: ProjectRecipe) {
  const xs = recipe.profile.outer.map(([x]) => x);
  const ys = recipe.profile.outer.map(([, y]) => y);
  const left = Math.min(...xs);
  const top = Math.min(...ys);
  const width = Math.max(...xs) - left;
  const height = Math.max(...ys) - top;
  const evidence: ReferenceCalibration = {
    known_length_mm: 25.4,
    reference_points: [
      [left + width / 4, top + height / 2],
      [left + (3 * width) / 4, top + height / 2],
    ],
    image_size: { width: trace.image.width, height: trace.image.height },
  };
  const [[x1, y1], [x2, y2]] = evidence.reference_points;
  const expectedWidth = (width / Math.hypot(x2 - x1, y2 - y1)) * evidence.known_length_mm;
  return { evidence, expectedWidth, expectedHeight: (expectedWidth * height) / width };
}

async function openReference(page: Page) {
  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Use a known feature' })
    .click();
}

async function enterEvidence(page: Page, evidence: ReferenceCalibration) {
  for (let index = 0; index < 2; index++) {
    const point = evidence.reference_points[index];
    await page
      .getByRole('spinbutton', { name: `Endpoint ${index + 1} X`, exact: true })
      .fill(String(point[0]));
    await page
      .getByRole('spinbutton', { name: `Endpoint ${index + 1} Y`, exact: true })
      .fill(String(point[1]));
  }
  await page
    .getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true })
    .fill(String(evidence.known_length_mm));
}

async function rebuild(page: Page): Promise<ModelResult> {
  const response = page.waitForResponse(
    (item) => item.url().endsWith('/api/build') && item.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  expect((await response).ok()).toBe(true);
  const model: ModelResult = await (await response).json();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  return model;
}

test('known-feature scale rebuilds physical dimensions and round-trips its evidence while importing from inches', async ({
  page,
}, testInfo) => {
  const trace = await ready(page);
  const original = await saveRecipe(page, testInfo, 'original-sample.json');
  expect(original.recipe).not.toHaveProperty('measured_height_mm');
  const { evidence, expectedWidth, expectedHeight } = calibrationFor(trace, original.recipe);
  await openReference(page);
  await enterEvidence(page, evidence);
  await page.getByRole('button', { name: 'Apply reference scale', exact: true }).click();
  await expect
    .poll(async () =>
      Number(
        await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).inputValue(),
      ),
    )
    .toBeCloseTo(expectedWidth, 8);
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toHaveCount(0);

  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Independent height check' })
    .click();
  const measuredHeight = expectedHeight + 2;
  await page
    .getByRole('spinbutton', { name: 'Measured outside height (mm)', exact: true })
    .fill(String(measuredHeight));
  await expect(page.locator('#height-check-result')).toContainText(
    'Difference (estimate − measured): -2.000 mm',
  );
  await page.getByRole('button', { name: 'in', exact: true }).click();
  await expect(
    page.getByRole('spinbutton', { name: 'Known feature length (in)', exact: true }),
  ).toHaveValue('1');
  const built = await rebuild(page);
  expect(built.dimensions.width).toBeCloseTo(expectedWidth, 6);
  expect(built.dimensions.height).toBeCloseTo(expectedHeight, 6);
  expect(built.dimensions.thickness).toBeCloseTo(4, 6);

  const saved = await saveRecipe(page, testInfo, 'calibrated-inches.json');
  expect(saved.recipe.reference_calibration).toEqual(evidence);
  expect(saved.recipe.width_mm).toBeCloseTo(expectedWidth, 6);
  expect(saved.recipe.measured_height_mm).toBeCloseTo(measuredHeight, 6);
  expect(JSON.stringify(saved.recipe)).not.toContain('data:image/');

  // Restore while the interface is in inches: the stored millimeter evidence must not be
  // converted a second time as the component and display units reset.
  const restoredBuild = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.ok(),
  );
  await page.getByLabel('Choose photo or project').setInputFiles(saved.file);
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  expect((await (await restoredBuild).json()).dimensions.width).toBeCloseTo(expectedWidth, 6);
  await expect(page.getByText('Restored project · outline only', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'mm', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await openReference(page);
  await expect(
    page.getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true }),
  ).toHaveValue('25.4');
  for (let index = 0; index < 2; index++) {
    await expect(
      page.getByRole('spinbutton', { name: `Endpoint ${index + 1} X`, exact: true }),
    ).toHaveValue(String(evidence.reference_points[index][0]));
    await expect(
      page.getByRole('spinbutton', { name: `Endpoint ${index + 1} Y`, exact: true }),
    ).toHaveValue(String(evidence.reference_points[index][1]));
  }
  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Independent height check' })
    .click();
  await expect
    .poll(async () =>
      Number(
        await page
          .getByRole('spinbutton', { name: 'Measured outside height (mm)', exact: true })
          .inputValue(),
      ),
    )
    .toBeCloseTo(measuredHeight, 6);
  await expect(page.locator('#height-check-result')).toContainText(
    'Difference (estimate − measured): -2.000 mm',
  );
  const sourceHeightResult = (await page.locator('#height-check-result').textContent()) ?? '';
  await page.getByRole('button', { name: /^Design & print/ }).click();
  await page.getByRole('spinbutton', { name: 'XY scale (%)', exact: true }).fill('150');
  await expect(page.locator('#height-check-result')).toHaveText(sourceHeightResult);
  const again = await saveRecipe(page, testInfo, 'calibrated-restored.json');
  expect(again.recipe.reference_calibration).toEqual(evidence);
  expect(again.recipe.measured_height_mm).toBeCloseTo(measuredHeight, 6);
  expect(again.recipe.design?.scale_percent).toBe(150);
  await page
    .getByRole('spinbutton', { name: 'Measured outside height (mm)', exact: true })
    .fill('');
  const cleared = await saveRecipe(page, testInfo, 'height-cleared.json');
  expect(cleared.recipe).not.toHaveProperty('measured_height_mm');
  expect(cleared.recipe.reference_calibration).toEqual(evidence);
});

test('invalid endpoint drafts cannot apply and a manual width removes applied reference evidence', async ({
  page,
}, testInfo) => {
  const trace = await ready(page);
  const original = await saveRecipe(page, testInfo, 'validation-sample.json');
  const { evidence } = calibrationFor(trace, original.recipe);
  await openReference(page);
  const apply = page.getByRole('button', { name: 'Apply reference scale', exact: true });
  await expect(apply).toBeDisabled();
  await enterEvidence(page, evidence);
  await expect(apply).toBeEnabled();

  await page
    .getByRole('spinbutton', { name: 'Endpoint 2 X', exact: true })
    .fill(String(evidence.reference_points[0][0]));
  await page
    .getByRole('spinbutton', { name: 'Endpoint 2 Y', exact: true })
    .fill(String(evidence.reference_points[0][1]));
  await expect(apply).toBeDisabled();
  await expect(
    page.getByText('Separate the endpoints by at least one working-image pixel.', { exact: true }),
  ).toBeVisible();
  await page
    .getByRole('spinbutton', { name: 'Endpoint 2 X', exact: true })
    .fill(String(trace.image.width + 1));
  await expect(apply).toBeDisabled();
  await expect(
    page.getByText('Place both endpoints inside the working image.', { exact: true }),
  ).toBeVisible();
  await enterEvidence(page, evidence);
  await page.getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true }).fill('0');
  await expect(apply).toBeDisabled();
  await page
    .getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true })
    .fill('100000');
  await expect(apply).toBeDisabled();
  await expect(page.getByText(/outside width beyond 0.1–2000 mm/)).toBeVisible();

  // A 3-4-5 diagonal distinguishes Euclidean length from accidental X-only scaling.
  // Editing a valid draft must leave the current physical width alone until Apply.
  const diagonal: ReferenceCalibration = {
    ...evidence,
    known_length_mm: 50,
    reference_points: [
      [100, 100],
      [400, 500],
    ],
  };
  const diagonalWidth = trace.bounds.width / 10;
  await enterEvidence(page, diagonal);
  const draft = await saveRecipe(page, testInfo, 'diagonal-draft.json');
  expect(draft.recipe.width_mm).toBe(original.recipe.width_mm);
  expect(draft.recipe).not.toHaveProperty('reference_calibration');
  await apply.click();
  const applied = await saveRecipe(page, testInfo, 'diagonal-applied.json');
  expect(applied.recipe.width_mm).toBeCloseTo(diagonalWidth, 8);
  expect(applied.recipe.reference_calibration).toEqual(diagonal);
  const reversed: ReferenceCalibration = {
    ...diagonal,
    reference_points: [diagonal.reference_points[1], diagonal.reference_points[0]],
  };
  await enterEvidence(page, reversed);
  await apply.click();
  const reversedRecipe = await saveRecipe(page, testInfo, 'diagonal-reversed.json');
  expect(reversedRecipe.recipe.width_mm).toBeCloseTo(diagonalWidth, 8);
  expect(reversedRecipe.recipe.reference_calibration).toEqual(reversed);
  await expect(
    page.locator('.reference-tool > summary').filter({ hasText: 'Use a known feature' }),
  ).toContainText('scale applied');
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('60');
  await expect(
    page.locator('.reference-tool > summary').filter({ hasText: 'Use a known feature' }),
  ).not.toContainText('scale applied');
  const manual = await saveRecipe(page, testInfo, 'manual-width.json');
  expect(manual.recipe.width_mm).toBe(60);
  expect(manual.recipe).not.toHaveProperty('reference_calibration');
});

test('invalid imported reference evidence is rejected before replacing the current project', async ({
  page,
}, testInfo) => {
  const trace = await ready(page);
  const original = await saveRecipe(page, testInfo, 'import-sample.json');
  const { evidence, expectedWidth } = calibrationFor(trace, original.recipe);
  await openReference(page);
  await enterEvidence(page, evidence);
  await page.getByRole('button', { name: 'Apply reference scale', exact: true }).click();
  await rebuild(page);
  const valid = await saveRecipe(page, testInfo, 'valid-calibrated.json');
  let buildRequests = 0;
  page.on('request', (request) => {
    if (request.url().endsWith('/api/build') && request.method() === 'POST') buildRequests++;
  });
  const invalidRecipes = [
    {
      ...valid.recipe,
      reference_calibration: {
        ...evidence,
        reference_points: [evidence.reference_points[0], evidence.reference_points[0]],
      },
    },
    {
      ...valid.recipe,
      reference_calibration: {
        ...evidence,
        reference_points: [[-1, 0], evidence.reference_points[1]],
      },
    },
    { ...valid.recipe, width_mm: expectedWidth + 5 },
    { ...valid.recipe, measured_height_mm: 0 },
  ];
  for (const [index, recipe] of invalidRecipes.entries()) {
    await page.getByLabel('Choose photo or project').setInputFiles({
      name: `invalid-reference-${index}.cad-project.json`,
      mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify(recipe)),
    });
    await expect(page.getByRole('alert')).toContainText(/reference|calibration|height/i);
    await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
    await expect(page.locator('canvas[data-model-ready="true"]')).toBeVisible();
    const retained = await saveRecipe(page, testInfo, `retained-project-${index}.json`);
    expect(retained.recipe.width_mm).toBeCloseTo(expectedWidth, 6);
    expect(retained.recipe.reference_calibration).toEqual(evidence);
    expect(retained.recipe.profile).toEqual(valid.recipe.profile);
  }
  expect(buildRequests).toBe(0);
});

test.describe('mobile reference picking', () => {
  test.use({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    hasTouch: true,
    isMobile: true,
  });

  test('touch endpoints map to working-image pixels and remain accessible at phone width', async ({
    page,
  }, testInfo) => {
    const trace = await ready(page);
    await openReference(page);
    const picker = page.getByRole('img', { name: /^Reference endpoints on the working image/ });
    await picker.scrollIntoViewIfNeeded();
    const mapping = await picker.evaluate((element) => {
      const rect = element.getBoundingClientRect();
      const css = getComputedStyle(element);
      return {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
        left: parseFloat(css.borderLeftWidth),
        right: parseFloat(css.borderRightWidth),
        top: parseFloat(css.borderTopWidth),
        bottom: parseFloat(css.borderBottomWidth),
      };
    });
    // Derive the drawn-image rectangle independently from the element's border box and
    // viewBox aspect ratio, including any centered letterboxing from the mobile CSS size.
    const contentWidth = mapping.width - mapping.left - mapping.right;
    const contentHeight = mapping.height - mapping.top - mapping.bottom;
    const scale = Math.min(contentWidth / trace.image.width, contentHeight / trace.image.height);
    const imageX = mapping.x + mapping.left + (contentWidth - trace.image.width * scale) / 2;
    const imageY = mapping.y + mapping.top + (contentHeight - trace.image.height * scale) / 2;
    const targetPoints = [
      [trace.image.width / 4, trace.image.height / 2],
      [(trace.image.width * 3) / 4, trace.image.height / 2],
    ];
    for (const [index, [x, y]] of targetPoints.entries()) {
      await page.touchscreen.tap(imageX + x * scale, imageY + y * scale);
      const actualX = Number(
        await page
          .getByRole('spinbutton', { name: `Endpoint ${index + 1} X`, exact: true })
          .inputValue(),
      );
      const actualY = Number(
        await page
          .getByRole('spinbutton', { name: `Endpoint ${index + 1} Y`, exact: true })
          .inputValue(),
      );
      expect(actualX).toBeCloseTo(x, 2);
      expect(actualY).toBeCloseTo(y, 2);
    }
    await page
      .getByRole('spinbutton', { name: 'Known feature length (mm)', exact: true })
      .fill('25.4');
    await expect(
      page.getByRole('button', { name: 'Apply reference scale', exact: true }),
    ).toBeEnabled();
    await page.getByRole('button', { name: 'Apply reference scale', exact: true }).click();
    const saved = await saveRecipe(page, testInfo, 'touch-calibration.json');
    expect(saved.recipe.reference_calibration?.reference_points).toEqual(targetPoints);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
    const accessibility = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(accessibility.violations).toEqual([]);
  });
});
