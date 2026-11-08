import { test, expect, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';

// CAD construction and exports use the running backend. Only assistant answers
// are fixtures, so these tests verify user control rather than model quality.
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
  const initialBuild = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.ok(),
  );
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  await expect(page.getByText('3D preview is unavailable')).toBeHidden();
  await expect(page.locator('canvas[data-model-ready="true"]')).toBeVisible();
  return (await initialBuild).json();
}

async function openDesign(page: Page) {
  await page.getByRole('button', { name: /^Design & print/ }).click();
}

async function saveRecipe(page: Page, testInfo: TestInfo, fileName: string) {
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const download = await downloadEvent;
  const file = testInfo.outputPath(fileName);
  await download.saveAs(file);
  return { file, recipe: JSON.parse(await readFile(file, 'utf8')) };
}

async function rebuild(page: Page) {
  const responseEvent = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  const response = await responseEvent;
  expect(response.ok()).toBe(true);
  const model = await response.json();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText('3D preview is unavailable')).toBeHidden();
  await expect(page.locator('canvas[data-model-ready="true"]')).toBeVisible();
  return model;
}

function inspectPartsZip(file: string) {
  // Use Python's standard ZIP reader, then independently inspect the binary STL
  // geometry rather than accepting a ZIP filename as evidence of real parts.
  return JSON.parse(
    execFileSync(
      '.venv/bin/python',
      [
        '-c',
        `import json, struct, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    manifest = json.loads(archive.read('manifest.json'))
    checks = []
    for part in manifest['parts']:
        stl = archive.read(part['files']['stl'])
        triangles = struct.unpack_from('<I', stl, 80)[0]
        assert triangles > 0 and len(stl) == 84 + 50 * triangles
        vertices = []
        for index in range(triangles):
            record = struct.unpack_from('<12fH', stl, 84 + index * 50)
            vertices.extend(record[offset:offset+3] for offset in (3, 6, 9))
        minimum = [min(vertex[axis] for vertex in vertices) for axis in range(3)]
        size = [max(vertex[axis] for vertex in vertices)-minimum[axis] for axis in range(3)]
        step = archive.read(part['files']['step'])
        checks.append({'id': part['id'], 'triangles': triangles, 'minimum': minimum,
                       'size': size, 'valid_step': b'ISO-10303-21' in step})
    print(json.dumps({'manifest': manifest, 'checks': checks, 'files': archive.namelist()}))`,
        file,
      ],
      { encoding: 'utf8' },
    ),
  );
}

test('scaled design preserves source measurements and exports real printable parts', async ({
  page,
}, testInfo) => {
  const initial = await ready(page);
  await openDesign(page);
  await page.getByLabel('XY scale (%)', { exact: true }).fill('200');
  await page.getByLabel('Thickness scale (%)', { exact: true }).fill('150');
  await page.getByRole('combobox', { name: 'Material', exact: true }).selectOption('petg');
  await page.getByRole('button', { name: 'Ocean color', exact: true }).click();
  await page.getByLabel('Bed width (mm)', { exact: true }).fill('100');
  await page.getByLabel('Bed depth (mm)', { exact: true }).fill('100');
  await page.getByRole('combobox', { name: 'Output', exact: true }).selectOption('split');
  await expect(page.getByLabel('Columns', { exact: true })).toHaveValue('2');
  await expect(page.getByLabel('Rows', { exact: true })).toHaveValue('1');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('4.00');

  const model = await rebuild(page);
  expect(model.dimensions.width).toBeCloseTo(160, 4);
  expect(model.dimensions.height).toBeCloseTo(initial.dimensions.height * 2, 3);
  expect(model.dimensions.thickness).toBeCloseTo(6, 4);
  expect(model.volume_mm3).toBeCloseTo(initial.volume_mm3 * 6, 1);
  expect(model.parts).toHaveLength(2);
  expect(
    model.parts.every((part: { bed_fit: { status: string } }) => part.bed_fit.status === 'fits'),
  ).toBe(true);
  const downloadEvent = page.waitForEvent('download');
  await page.locator('.export-row').filter({ hasText: 'Parts ZIP' }).click();
  const download = await downloadEvent;
  const file = testInfo.outputPath(download.suggestedFilename());
  await download.saveAs(file);
  expect((await readFile(file)).length).toBeGreaterThan(1000);
  const { manifest, checks, files } = inspectPartsZip(file);
  expect(manifest).toMatchObject({
    format: 'pictures-to-cad-parts',
    version: 1,
    units: 'mm',
    design: { scale_percent: 200, thickness_percent: 150, material: 'petg', color: '#0284c7' },
  });
  expect(manifest.assembly_dimensions.width).toBeCloseTo(160, 4);
  expect(manifest.assembly_dimensions.thickness).toBeCloseTo(6, 4);
  expect(manifest.parts).toHaveLength(2);
  expect(checks).toHaveLength(2);
  expect(files).toContain('manifest.json');
  for (const check of checks) {
    expect(check.valid_step).toBe(true);
    expect(check.triangles).toBeGreaterThan(0);
    expect(check.minimum[0]).toBeCloseTo(0, 3);
    expect(check.minimum[1]).toBeCloseTo(0, 3);
    expect(check.minimum[2]).toBeCloseTo(0, 3);
    expect(check.size[0]).toBeLessThanOrEqual(90.001);
    expect(check.size[1]).toBeLessThanOrEqual(90.001);
    expect(check.size[2]).toBeCloseTo(6, 3);
  }
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  const geometryRequests: string[] = [];
  page.on('request', (request) => {
    if (/\/api\/(build|trace)$/.test(request.url())) geometryRequests.push(request.url());
  });
  const inspection = page.getByRole('group', { name: 'Piece inspection', exact: true });
  await inspection.getByRole('button', { name: 'Separate pieces', exact: true }).click();
  const renderedModel = page.locator('canvas[data-model-ready="true"]');
  await expect(renderedModel).toHaveAttribute('data-inspection-view', 'separated');
  await expect(page.getByText('Separated for inspection', { exact: true })).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath('separated-pieces-inspection.png'),
    fullPage: true,
  });
  await inspection.getByRole('button', { name: 'Assembled', exact: true }).click();
  await expect(renderedModel).toHaveAttribute('data-inspection-view', 'assembled');
  const contextLossSupported = await renderedModel.evaluate((canvas: HTMLCanvasElement) => {
    const gl = canvas.getContext('webgl2');
    const extension = gl?.getExtension('WEBGL_lose_context');
    extension?.loseContext();
    return !!extension;
  });
  expect(contextLossSupported).toBe(true);
  await expect(page.getByText('3D preview is unavailable')).toBeVisible();
  await page.getByRole('button', { name: 'Retry preview', exact: true }).click();
  await expect(renderedModel).toBeVisible();
  await expect(renderedModel).toHaveAttribute('data-inspection-view', 'assembled');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('4.00');
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  const repeatDownloadEvent = page.waitForEvent('download');
  await page.locator('.export-row').filter({ hasText: 'Parts ZIP' }).click();
  const repeatedFile = testInfo.outputPath('parts-after-inspection.zip');
  await (await repeatDownloadEvent).saveAs(repeatedFile);
  expect((await readFile(repeatedFile)).equals(await readFile(file))).toBe(true);
  expect(geometryRequests).toEqual([]);
});

test('version 2 recipes restore appearance and design; version 1 recipes keep original dimensions', async ({
  page,
}, testInfo) => {
  await ready(page);
  await openDesign(page);
  await page.getByLabel('XY scale (%)', { exact: true }).fill('125');
  await page.getByLabel('Thickness scale (%)', { exact: true }).fill('75');
  await page.getByRole('button', { name: 'Coral color', exact: true }).click();
  await page.getByRole('combobox', { name: 'Material', exact: true }).selectOption('petg');
  await page.getByLabel('Nozzle diameter (mm)', { exact: true }).fill('0.6');
  await page.getByRole('combobox', { name: 'Geometry detail', exact: true }).selectOption('fine');
  await page.getByLabel('Bed width (mm)', { exact: true }).fill('180');
  const { file, recipe } = await saveRecipe(page, testInfo, 'scaled-project.json');
  expect(recipe.version).toBe(2);
  expect(recipe.width_mm).toBe(80);
  expect(recipe.thickness_mm).toBe(4);
  expect(recipe.design).toMatchObject({
    scale_percent: 125,
    thickness_percent: 75,
    color: '#ef6b5b',
    material: 'petg',
    nozzle_mm: 0.6,
    detail_mode: 'fine',
    bed_width_mm: 180,
  });
  await page.getByLabel('XY scale (%)', { exact: true }).fill('100');
  await page.getByRole('button', { name: 'White color', exact: true }).click();
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'oversized-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(
      JSON.stringify({
        ...recipe,
        width_mm: 1000,
        design: { ...recipe.design, scale_percent: 400 },
      }),
    ),
  });
  await expect(page.getByRole('alert')).toContainText('2000');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await expect(page.getByLabel('XY scale (%)', { exact: true })).toHaveValue('100');
  await expect(page.getByLabel('Model color', { exact: true })).toHaveValue('#e5e7eb');
  const restoredResponse = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.ok(),
  );
  await page.getByLabel('Choose photo or project').setInputFiles(file);
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  const restored = await (await restoredResponse).json();
  expect(restored.dimensions.width).toBeCloseTo(100, 4);
  expect(restored.dimensions.thickness).toBeCloseTo(3, 4);
  await expect(page.getByLabel('XY scale (%)', { exact: true })).toHaveValue('125');
  await expect(page.getByLabel('Thickness scale (%)', { exact: true })).toHaveValue('75');
  await expect(page.getByLabel('Model color', { exact: true })).toHaveValue('#ef6b5b');
  await expect(page.getByRole('combobox', { name: 'Material', exact: true })).toHaveValue('petg');
  await expect(page.getByLabel('Nozzle diameter (mm)', { exact: true })).toHaveValue('0.6');
  await expect(page.getByRole('combobox', { name: 'Geometry detail', exact: true })).toHaveValue(
    'fine',
  );
  await expect(page.getByLabel('Bed width (mm)', { exact: true })).toHaveValue('180');

  const catalog = await (await page.request.get('/api/printers')).json();
  const printer = catalog.printers.find((item: { name: string }) => /Prusa.*MK4S/i.test(item.name));
  expect(printer).toBeTruthy();
  const normalizedResponse = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.ok(),
  );
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'printer-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(
      JSON.stringify({
        ...recipe,
        design: {
          ...recipe.design,
          printer_id: printer.id,
          nozzle_mm: 0.4,
          bed_width_mm: 90,
          bed_depth_mm: 90,
          bed_height_mm: 90,
        },
      }),
    ),
  });
  const normalized = await (await normalizedResponse).json();
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  expect(normalized.design.bed_width_mm).toBe(250);
  await expect(page.getByLabel('Bed width (mm)', { exact: true })).toHaveValue('250');
  await expect(page.getByLabel('Bed depth (mm)', { exact: true })).toHaveValue('210');
  await expect(page.getByLabel('Build height (mm)', { exact: true })).toHaveValue('220');
  const normalizedRecipe = await saveRecipe(page, testInfo, 'normalized-printer-project.json');
  expect(normalizedRecipe.recipe.design.bed_width_mm).toBe(250);

  const legacy = {
    format: 'pictures-to-cad',
    version: 1,
    name: 'Legacy plate',
    profile: recipe.profile,
    width_mm: 80,
    thickness_mm: 4,
  };
  const legacyResponse = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.ok(),
  );
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'legacy-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(legacy)),
  });
  const legacyModel = await (await legacyResponse).json();
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  expect(legacyModel.dimensions.width).toBeCloseTo(80, 4);
  expect(legacyModel.dimensions.thickness).toBeCloseTo(4, 4);
  await expect(page.getByLabel('XY scale (%)', { exact: true })).toHaveValue('100');
  await expect(page.getByLabel('Thickness scale (%)', { exact: true })).toHaveValue('100');
  await expect(page.getByLabel('Model color', { exact: true })).toHaveValue('#9ca3af');
  await expect(page.getByRole('combobox', { name: 'Material', exact: true })).toHaveValue('pla');
  await expect(page.getByRole('combobox', { name: 'Output', exact: true })).toHaveValue('single');
});

test('AI design proposals wait for review, undo a built result, and expire after manual changes', async ({
  page,
}, testInfo) => {
  await page.route('**/api/assistant/status', (route) =>
    route.fulfill({
      json: {
        running: true,
        models: [
          {
            name: 'qwen3:1.7b',
            size_bytes: 1400000000,
            parameter_size: '1.7B',
            quantization: 'Q4_K_M',
          },
        ],
        recommended_model: 'qwen3:1.7b',
        detail: 'Ollama is ready.',
      },
    }),
  );
  const proposal = {
    scale_percent: 150,
    thickness_percent: 125,
    color: '#55bb88',
    material: 'petg',
    detail_mode: 'fine',
    nozzle_mm: 0.6,
    output_mode: 'split',
    split_columns: 2,
    split_rows: 1,
    bed_width_mm: 120,
    bed_depth_mm: 120,
  };
  await page.route('**/api/assistant/chat', (route) =>
    route.fulfill({
      json: {
        model: 'qwen3:1.7b',
        answer: 'Review this enlarged PETG design and two-part print plan before applying it.',
        proposal,
        warnings: ['Review the cuts and use your slicer to choose manufacturing settings.'],
        elapsed_seconds: 0.25,
      },
    }),
  );
  const initial = await ready(page);
  await page
    .locator('canvas[data-model-ready="true"]')
    .screenshot({ path: testInfo.outputPath('before-ai.png') });
  await openDesign(page);
  let builds = 0;
  page.on('request', (request) => {
    if (request.url().endsWith('/api/build')) builds += 1;
  });
  await page.getByRole('button', { name: /^Local AI assistant/ }).click();
  const assistant = page.getByRole('region', { name: 'Local AI assistant', exact: true });
  await assistant
    .getByRole('textbox')
    .fill('Suggest a larger green PETG design and split print plan.');
  await assistant.getByRole('button', { name: 'Ask local AI', exact: true }).click();
  await expect(assistant.getByRole('heading', { name: 'Review proposed changes' })).toBeVisible();
  await expect(assistant.getByRole('table')).toContainText('150%');
  await expect(assistant.getByRole('table')).toContainText('PETG');
  await expect(page.getByLabel('XY scale (%)', { exact: true })).toHaveValue('100');
  await expect(page.getByRole('combobox', { name: 'Material', exact: true })).toHaveValue('pla');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  expect(builds).toBe(0);

  await assistant.getByRole('button', { name: 'Apply suggestion', exact: true }).click();
  await expect(page.getByLabel('XY scale (%)', { exact: true })).toHaveValue('150');
  await expect(page.getByLabel('Thickness scale (%)', { exact: true })).toHaveValue('125');
  await expect(page.getByLabel('Model color', { exact: true })).toHaveValue('#55bb88');
  await expect(page.getByRole('combobox', { name: 'Material', exact: true })).toHaveValue('petg');
  await expect(page.getByRole('combobox', { name: 'Geometry detail', exact: true })).toHaveValue(
    'fine',
  );
  await expect(page.getByLabel('Nozzle diameter (mm)', { exact: true })).toHaveValue('0.6');
  await expect(page.getByRole('combobox', { name: 'Output', exact: true })).toHaveValue('split');
  await expect(page.getByLabel('Bed width (mm)', { exact: true })).toHaveValue('120');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('4.00');
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
  expect(builds).toBe(0);

  const suggested = await rebuild(page);
  expect(suggested.dimensions.width).toBeCloseTo(120, 4);
  expect(suggested.dimensions.thickness).toBeCloseTo(5, 4);
  expect(suggested.parts).toHaveLength(2);
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  await assistant.getByRole('button', { name: 'Undo suggestion', exact: true }).click();
  await expect(page.getByLabel('XY scale (%)', { exact: true })).toHaveValue('100');
  await expect(page.getByLabel('Thickness scale (%)', { exact: true })).toHaveValue('100');
  await expect(page.getByLabel('Model color', { exact: true })).toHaveValue('#9ca3af');
  await expect(page.getByRole('combobox', { name: 'Material', exact: true })).toHaveValue('pla');
  await expect(page.getByRole('combobox', { name: 'Geometry detail', exact: true })).toHaveValue(
    'original',
  );
  await expect(page.getByLabel('Nozzle diameter (mm)', { exact: true })).toHaveValue('0.4');
  await expect(page.getByRole('combobox', { name: 'Output', exact: true })).toHaveValue('single');
  await expect(page.getByLabel('Bed width (mm)', { exact: true })).toHaveValue('220');
  await expect(page.getByLabel('Bed depth (mm)', { exact: true })).toHaveValue('220');
  await expect(page.getByText('3D preview is unavailable')).toBeHidden();
  await expect(page.locator('canvas[data-model-ready="true"]')).toBeVisible();
  await expect(page.locator('.model-viewer')).toHaveAttribute('data-preview-color', '#9ca3af');
  await expect(page.locator('.model-viewer')).toHaveAttribute('data-preview-material', 'pla');
  await expect(page.getByRole('group', { name: 'Piece inspection', exact: true })).toHaveCount(0);
  await expect(page.locator('.dimensions-summary')).toContainText('80.00 mm (W)');
  await expect(page.locator('.dimensions-summary')).toContainText('4.00 mm (T)');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('4.00');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
  await page
    .locator('canvas[data-model-ready="true"]')
    .screenshot({ path: testInfo.outputPath('after-ai-undo.png') });
  expect(builds).toBe(1);
  const rebuilt = await rebuild(page);
  expect(rebuilt.dimensions.width).toBeCloseTo(initial.dimensions.width, 4);
  expect(rebuilt.dimensions.thickness).toBeCloseTo(initial.dimensions.thickness, 4);
  expect(rebuilt.volume_mm3).toBeCloseTo(initial.volume_mm3, 4);
  expect(rebuilt.parts).toHaveLength(1);
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  await assistant.getByRole('button', { name: 'Ask local AI', exact: true }).click();
  await expect(
    assistant.getByRole('button', { name: 'Apply suggestion', exact: true }),
  ).toBeEnabled();
  await page.getByLabel('XY scale (%)', { exact: true }).fill('110');
  await expect(
    assistant.getByRole('button', { name: 'Apply suggestion', exact: true }),
  ).toBeDisabled();
  await expect(
    assistant.getByText('Your project changed after this answer.', { exact: false }),
  ).toBeVisible();
  expect(builds).toBe(2);
});

test('printer search and custom volume checks stay usable on a narrow screen', async ({ page }) => {
  await ready(page);
  await page.setViewportSize({ width: 390, height: 844 });
  const toggle = page.getByRole('button', { name: /^Design & print/ });
  await toggle.focus();
  await page.keyboard.press('Enter');
  const search = page.getByLabel('Search printers', { exact: true });
  const printers = page.getByRole('combobox', { name: 'Printer model', exact: true });
  for (const query of ['Ender3', 'Ender 3']) {
    await search.fill(query);
    await expect(
      printers
        .locator('option')
        .filter({ hasText: /Ender.?3.*V2/i })
        .first(),
    ).toHaveCount(1);
  }
  await search.fill('Bambu A1');
  await expect(
    printers
      .locator('option')
      .filter({ hasText: /Bambu.*A1/i })
      .first(),
  ).toHaveCount(1);
  await search.fill('Prusa');
  const mk4s = printers.locator('option').filter({ hasText: /MK4S/i }).first();
  await expect(mk4s).toHaveCount(1);
  const printerId = await mk4s.getAttribute('value');
  expect(printerId).toBeTruthy();
  await printers.selectOption(printerId!);
  await expect(page.getByLabel('Bed width (mm)', { exact: true })).toHaveValue('250');
  await expect(page.getByLabel('Bed depth (mm)', { exact: true })).toHaveValue('210');
  await expect(page.getByLabel('Build height (mm)', { exact: true })).toHaveValue('220');
  await search.fill('no such printer model');
  await expect(page.getByText('0 matching models', { exact: false })).toBeVisible();
  await expect(printers.locator('option').filter({ hasText: /Custom/i })).toHaveCount(1);
  await page.getByLabel('Bed width (mm)', { exact: true }).fill('30');
  await page.getByLabel('Bed depth (mm)', { exact: true }).fill('30');
  await expect(printers).toHaveValue('custom');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  const model = await rebuild(page);
  expect(model.print_fit.status).toBe('too_large');
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  await expect(page.getByText(/exceeds|too large|does not fit/i).first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
});
