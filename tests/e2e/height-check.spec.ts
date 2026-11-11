import { expect, test, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';
import { DEFAULT_DESIGN } from '../../frontend/src/design';
import { assessHeight, heightCheckDraft } from '../../frontend/src/heightCheck';
import type { ProjectRecipe } from '../../frontend/src/types';

const settings = { allowance_mm: 0.5, measurement_bound_mm: 0.1 };
const fixture: ProjectRecipe = {
  format: 'pictures-to-cad',
  version: 2,
  name: 'Independent engineering check',
  profile: {
    outer: [
      [10, 10],
      [90, 10],
      [90, 60],
      [10, 60],
    ],
    holes: [],
  },
  width_mm: 80,
  thickness_mm: 4,
  design: { ...DEFAULT_DESIGN },
  measured_height_mm: 50.2,
  height_check: settings,
};

test('height decision uses a bounded interval and withholds decisions at either limit', () => {
  for (const [height, bound, expected] of [
    [50.2, 0.1, 'within'],
    [49.8, 0.1, 'within'],
    [50.9, 0.1, 'outside'],
    [49.1, 0.1, 'outside'],
    [50.2, 0.4, 'inconclusive'],
    [50, 1, 'inconclusive'],
    [50.4, 0.1, 'inconclusive'],
    [49.6, 0.1, 'inconclusive'],
    [50.6, 0.1, 'inconclusive'],
    [49.4, 0.1, 'inconclusive'],
    [50, 0, 'within'],
    [50.5, 0, 'inconclusive'],
  ] as const) {
    expect(assessHeight(50, height, { ...settings, measurement_bound_mm: bound })?.status).toBe(
      expected,
    );
  }
  expect(assessHeight(50, 50.2, settings)?.low).toBeCloseTo(-0.3, 10);
  expect(assessHeight(50, 50.2, settings)?.high).toBeCloseTo(-0.1, 10);
});

test('decisions agree with an independent integer-interval oracle', () => {
  // Exact thousandth-mm values, compared as integers. Enumerate the measurement interval
  // on that integer lattice; extrema are included, so strict containment is also checked.
  for (let offset = -100; offset <= 100; offset += 5) {
    for (let bound = 0; bound <= 100; bound += 10) {
      const errors = Array.from({ length: 2 * bound + 1 }, (_, i) => Math.abs(offset - bound + i));
      const expected = errors.every((e) => e < 50)
        ? 'within'
        : errors.every((e) => e > 50)
          ? 'outside'
          : 'inconclusive';
      expect(
        assessHeight(50, (50000 + offset) / 1000, {
          allowance_mm: 0.05,
          measurement_bound_mm: bound / 1000,
        })?.status,
      ).toBe(expected);
    }
  }
});

test('unknown, partial, invalid and extreme decision inputs cannot produce an assessment', () => {
  expect(heightCheckDraft('', '', 1)).toEqual({ value: null, error: null });
  for (const [allowance, bound] of [
    ['1', ''],
    ['', '0'],
    ['0', '0'],
    ['-1', '1'],
    ['1', '-1'],
    ['Infinity', '0'],
    ['0.1', 'NaN'],
    ['2001', '0'],
    ['1', '2001'],
  ]) {
    expect(heightCheckDraft(allowance, bound, 1).value).toBeNull();
    expect(heightCheckDraft(allowance, bound, 1).error).toBeTruthy();
  }
  expect(heightCheckDraft('0.02', '0', 25.4).value).toEqual({
    allowance_mm: 0.508,
    measurement_bound_mm: 0,
  });
  for (const measured of [NaN, Infinity, 0, -1, 2001])
    expect(assessHeight(50, measured, settings)).toBeNull();
  for (const estimate of [NaN, Infinity, 0, -1])
    expect(assessHeight(estimate, 50, settings)).toBeNull();
});

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
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60000,
  });
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'engineering.cad-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(fixture)),
  });
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60000,
  });
  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Independent height check' })
    .press('Enter');
}
async function save(page: Page, testInfo: TestInfo, name: string) {
  const event = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const download = await event;
  const file = testInfo.outputPath(name);
  await download.saveAs(file);
  return { file, recipe: JSON.parse(await readFile(file, 'utf8')) as ProjectRecipe };
}

test('height allowance decisions follow source edits, preserve units and round-trip only the inputs', async ({
  page,
}, testInfo) => {
  await ready(page);
  const result = page.locator('#height-decision-result');
  await expect(result).toContainText('Within entered allowance');
  await expect(result).toContainText('-0.3 to -0.1 mm');
  await page
    .getByRole('spinbutton', { name: 'Measurement error bound (±mm)', exact: true })
    .fill('0.4');
  await expect(result).toContainText('Inconclusive: interval reaches a limit');
  await page
    .getByRole('spinbutton', { name: 'Measurement error bound (±mm)', exact: true })
    .fill('0.1');
  await page
    .getByRole('spinbutton', { name: 'Measured outside height (mm)', exact: true })
    .fill('50.9');
  await expect(result).toContainText('Outside entered allowance');
  await page
    .getByRole('spinbutton', { name: 'Measured outside height (mm)', exact: true })
    .fill('50.2');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  const original = await save(page, testInfo, 'height-check.json');
  expect(original.recipe.height_check).toEqual(settings);
  expect(original.recipe.profile).toEqual(fixture.profile);
  expect(original.recipe.height_check).not.toHaveProperty('status');
  await page.getByRole('button', { name: 'in', exact: true }).click();
  await expect(result).toContainText('Within entered allowance');
  expect(
    Number(
      await page
        .getByRole('spinbutton', { name: 'Allowed height deviation (±in)', exact: true })
        .inputValue(),
    ) * 25.4,
  ).toBeCloseTo(0.5, 10);
  const inches = await save(page, testInfo, 'height-check-inches.json');
  expect(inches.recipe.height_check?.allowance_mm).toBeCloseTo(0.5, 10);
  expect(inches.recipe.height_check?.measurement_bound_mm).toBeCloseTo(0.1, 10);
  await page.getByLabel('Choose photo or project').setInputFiles(original.file);
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60000,
  });
  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Independent height check' })
    .click();
  await expect(result).toContainText('Within entered allowance');
  // A display-unit change must not turn exact boundary contact into acceptance.
  await page
    .getByRole('spinbutton', { name: 'Measured outside height (mm)', exact: true })
    .fill('50.4');
  await expect(result).toContainText('Inconclusive: interval reaches a limit');
  for (let i = 0; i < 3; i++) {
    await page.getByRole('button', { name: 'in', exact: true }).click();
    await expect(result).toContainText('Inconclusive: interval reaches a limit');
    await page.getByRole('button', { name: 'mm', exact: true }).click();
    await expect(result).toContainText('Inconclusive: interval reaches a limit');
  }
  await page
    .getByRole('spinbutton', { name: 'Measured outside height (mm)', exact: true })
    .fill('50.2');
  await expect(result).toContainText('Within entered allowance');
  const beforeDesign = (await result.textContent()) ?? '';
  await page.getByRole('button', { name: /^Design & print/ }).click();
  await page.getByRole('spinbutton', { name: 'XY scale (%)', exact: true }).fill('150');
  await expect(result).toHaveText(beforeDesign);
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('84');
  await expect(result).toContainText('Outside entered allowance');
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('');
  await expect(result).toContainText('Undecided:');
});

test('malformed decision imports preserve the project and undecided notes cannot be saved as complete', async ({
  page,
}, testInfo) => {
  await ready(page);
  let builds = 0;
  page.on('request', (request) => {
    if (request.url().endsWith('/api/build') && request.method() === 'POST') builds++;
  });
  for (const height_check of [
    null,
    {},
    { allowance_mm: 0.5 },
    { ...settings, allowance_mm: '0.5' },
    { ...settings, allowance_mm: 0 },
    { ...settings, measurement_bound_mm: -1 },
  ]) {
    await page.getByLabel('Choose photo or project').setInputFiles({
      name: 'invalid.cad-project.json',
      mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify({ ...fixture, height_check })),
    });
    await expect(page.getByRole('alert')).toContainText('invalid height check');
    await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  }
  expect(builds).toBe(0);
  const retained = await save(page, testInfo, 'height-check-retained.json');
  expect(retained.recipe.height_check).toEqual(settings);
  await page
    .getByRole('spinbutton', { name: 'Measurement error bound (±mm)', exact: true })
    .fill('');
  await expect(page.locator('#height-decision-result')).toContainText('Enter both decision inputs');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Enter both decision inputs');
  await page
    .getByRole('spinbutton', { name: 'Allowed height deviation (±mm)', exact: true })
    .fill('');
  const cleared = await save(page, testInfo, 'height-check-cleared.json');
  expect(cleared.recipe).not.toHaveProperty('height_check');
  expect(cleared.recipe.measured_height_mm).toBe(50.2);
});

test('height decision stays usable at phone width with keyboard labels and no automated accessibility violations', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  const allowance = page.getByRole('spinbutton', {
    name: 'Allowed height deviation (±mm)',
    exact: true,
  });
  await allowance.focus();
  await expect(allowance).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(
    page.getByRole('spinbutton', { name: 'Measurement error bound (±mm)', exact: true }),
  ).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page
    .locator('.height-check')
    .screenshot({ path: testInfo.outputPath('height-check-mobile.png') });
});

test('older recipes and a new sample do not inherit prior decision inputs', async ({
  page,
}, testInfo) => {
  await ready(page);
  const legacy = { ...fixture, height_check: undefined, measured_height_mm: undefined };
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'older.cad-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(legacy)),
  });
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60000,
  });
  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Independent height check' })
    .click();
  for (const label of [
    'Measured outside height (mm)',
    'Allowed height deviation (±mm)',
    'Measurement error bound (±mm)',
  ]) {
    await expect(page.getByRole('spinbutton', { name: label, exact: true })).toHaveValue('');
  }
  await expect(page.locator('#height-decision-result')).toContainText('Undecided:');
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'engineering.cad-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(fixture)),
  });
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60000,
  });
  await page.getByRole('button', { name: 'Photo', exact: true }).click();
  await page.getByRole('button', { name: 'Try the sample part', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60000,
  });
  const fresh = await save(page, testInfo, 'fresh-sample.json');
  expect(fresh.recipe).not.toHaveProperty('height_check');
  expect(fresh.recipe).not.toHaveProperty('measured_height_mm');
});
