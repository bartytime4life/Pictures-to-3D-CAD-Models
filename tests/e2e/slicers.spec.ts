import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';

// Geometry and downloads use the real CAD backend. Native application discovery and
// launch replies are fixtures: no installed slicer or printer is started by these tests.
const jobs = new Set<string>();
const programs = [
  {
    id: 'bambu',
    name: 'Bambu Studio',
    target_version: '2.9.1',
    release_url: 'https://github.com/bambulab/BambuStudio/releases/tag/v02.09.01.70',
    source_url: 'https://github.com/bambulab/BambuStudio',
    detected: false,
    launch_available: false,
    launch_reason: 'Local opening is disabled. Download the handoff ZIP to open it yourself.',
    version_status: 'not_checked',
    bridge_enabled: false,
  },
  {
    id: 'prusa',
    name: 'PrusaSlicer',
    target_version: '2.9.7',
    release_url: 'https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.9.7',
    source_url: 'https://github.com/prusa3d/PrusaSlicer',
    detected: false,
    launch_available: false,
    launch_reason: 'Local opening is disabled. Download the handoff ZIP to open it yourself.',
    version_status: 'not_checked',
    bridge_enabled: false,
  },
];

test.beforeEach(async ({ page }) => {
  await page.route('**/api/slicers', (route) =>
    route.fulfill({ json: { programs, local_bridge_enabled: false } }),
  );
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
  const built = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.ok(),
  );
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  return (await built).json();
}

function inspectArchive(file: string, handoff = false) {
  return JSON.parse(
    execFileSync(
      '.venv/bin/python',
      [
        '-c',
        `import hashlib,json,sys,zipfile,xml.etree.ElementTree as ET
with zipfile.ZipFile(sys.argv[1]) as archive:
    manifest=json.loads(archive.read('manifest.json')) if sys.argv[2]=='yes' else None
    if manifest:
        mesh=archive.read('model.3mf')
        import io
        inner=zipfile.ZipFile(io.BytesIO(mesh))
    else:
        inner=archive
    root=ET.fromstring(inner.read('3D/3dmodel.model'))
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    objects=root.findall('m:resources/m:object',ns)
    vertices=[o.findall('m:mesh/m:vertices/m:vertex',ns) for o in objects]
    result={'unit':root.attrib['unit'],'objects':len(objects),'items':len(root.findall('m:build/m:item',ns)),
            'triangles':[len(o.findall('m:mesh/m:triangles/m:triangle',ns)) for o in objects],
            'dimensions':[[max(float(v.attrib[a]) for v in vs)-min(float(v.attrib[a]) for v in vs) for a in ('x','y','z')] for vs in vertices],
            'files':archive.namelist(),'manifest':manifest}
    if manifest:
        result['hashes_match']=all(hashlib.sha256(archive.read(name)).hexdigest()==facts['sha256'] and len(archive.read(name))==facts['size_bytes'] for name,facts in manifest['files'].items())
        result['recipe']=json.loads(archive.read('project.json'))
        result['notes']=archive.read('README.md').decode()
    print(json.dumps(result))`,
        file,
        handoff ? 'yes' : 'no',
      ],
      { encoding: 'utf8' },
    ),
  );
}

test('real 3MF and targeted handoffs preserve units, split objects and planning settings', async ({
  page,
}, testInfo) => {
  await ready(page);
  await page.getByRole('button', { name: /^Design & print/ }).click();
  await page.getByRole('combobox', { name: 'Material', exact: true }).selectOption('petg');
  await page.getByLabel('Nozzle diameter (mm)', { exact: true }).fill('0.6');
  await page.getByRole('combobox', { name: 'Output', exact: true }).selectOption('split');
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  const handoff = page.getByRole('region', { name: 'Prepare in your slicer', exact: true });
  await expect(handoff).toContainText('2 separate built objects');
  await expect(handoff).toContainText('PETG · 0.6 mm nozzle');
  const fileEvent = page.waitForEvent('download');
  await page.locator('.export-row').filter({ hasText: '3MF' }).click();
  const download = await fileEvent;
  expect(download.suggestedFilename()).toMatch(/\.3mf$/);
  const meshPath = testInfo.outputPath('mesh.3mf');
  await download.saveAs(meshPath);
  const mesh = inspectArchive(meshPath);
  expect(mesh.unit).toBe('millimeter');
  expect(mesh.objects).toBe(2);
  expect(mesh.items).toBe(2);
  expect(mesh.triangles.every((value: number) => value > 0)).toBe(true);
  expect(mesh.dimensions.every((size: number[]) => Math.abs(size[2] - 4) < 0.001)).toBe(true);
  for (const [name, id, version] of [
    ['Bambu Studio', 'bambu', '2.9.1'],
    ['PrusaSlicer', 'prusa', '2.9.7'],
  ]) {
    await handoff.getByRole('radio', { name: new RegExp(name) }).check();
    const zipEvent = page.waitForEvent('download');
    await handoff
      .getByRole('button', { name: `Download ${name} handoff ZIP`, exact: true })
      .click();
    const zip = await zipEvent;
    expect(zip.suggestedFilename()).toMatch(/\.zip$/);
    const zipPath = testInfo.outputPath(`${id}.zip`);
    await zip.saveAs(zipPath);
    const result = inspectArchive(zipPath, true);
    expect(result.unit).toBe('millimeter');
    expect(result.objects).toBe(2);
    expect(result.hashes_match).toBe(true);
    expect(result.files).toEqual(
      expect.arrayContaining([
        'model.3mf',
        'model.stl',
        'project.json',
        'manifest.json',
        'README.md',
        'part-01.3mf',
        'part-01.stl',
      ]),
    );
    expect(result.manifest).toMatchObject({
      format: 'pictures-to-cad-slicer-handoff',
      version: 1,
      units: 'mm',
      slicer: { id, target_version: version },
      design: { material: 'petg', nozzle_mm: 0.6, output_mode: 'split' },
      native_slicer_profile: false,
      slicing_verified: false,
      printing_verified: false,
    });
    expect(result.recipe.design).toMatchObject({ material: 'petg', nozzle_mm: 0.6 });
    expect(result.notes).toContain(name);
    await expect(handoff).toContainText('PETG · 0.6 mm nozzle');
  }
  await handoff.screenshot({ path: testInfo.outputPath('slicer-handoff.png') });
});

test('opening the export dialog never launches; a configured launch requires an explicit click', async ({
  page,
}) => {
  await page.route('**/api/slicers', (route) =>
    route.fulfill({
      json: {
        programs: programs.map((program) => ({
          ...program,
          detected: true,
          bridge_enabled: true,
          launch_available: program.id === 'prusa',
          launch_reason: 'Local opening is enabled for this application.',
        })),
        local_bridge_enabled: true,
      },
    }),
  );
  const launches: { url: string; method: string; body: unknown }[] = [];
  await page.route('**/api/models/*/slicer/*', async (route) => {
    launches.push({
      url: route.request().url(),
      method: route.request().method(),
      body: route.request().postDataJSON(),
    });
    await route.fulfill({
      json: {
        status: 'launch_requested',
        program_id: 'prusa',
        name: 'PrusaSlicer',
        detail: 'Launch requested.',
        handoff_id: 'test-only',
      },
    });
  });
  const model = await ready(page);
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  const handoff = page.getByRole('region', { name: 'Prepare in your slicer', exact: true });
  await expect(handoff).toContainText('Bambu Studio found · installed version not checked');
  await expect(
    handoff.getByRole('button', { name: 'Open in Bambu Studio', exact: true }),
  ).toHaveCount(0);
  await handoff.getByRole('radio', { name: /PrusaSlicer/ }).check();
  await expect(
    handoff.getByRole('button', { name: 'Open in PrusaSlicer', exact: true }),
  ).toBeEnabled();
  expect(launches).toEqual([]);
  await handoff.getByRole('button', { name: 'Open in PrusaSlicer', exact: true }).click();
  await expect(handoff).toContainText('launch requested. Check the application to confirm import.');
  expect(launches).toEqual([
    {
      url: expect.stringContaining(`/api/models/${model.id}/slicer/prusa`),
      method: 'POST',
      body: {},
    },
  ]);
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  await page.getByLabel('Thickness', { exact: true }).fill('6');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toHaveCount(0);
  await expect(
    page.getByRole('region', { name: 'Prepare in your slicer', exact: true }),
  ).toHaveCount(0);
  expect(launches).toHaveLength(1);
});

test('download remains available after discovery failure and a failed launch is recoverable', async ({
  page,
}) => {
  let discoveryCalls = 0;
  await page.route('**/api/slicers', (route) => {
    discoveryCalls += 1;
    return discoveryCalls === 1
      ? route.fulfill({ status: 503, json: { detail: 'Temporarily unavailable.' } })
      : route.fulfill({
          json: {
            programs: programs.map((program) => ({
              ...program,
              detected: true,
              bridge_enabled: true,
              launch_available: true,
            })),
            local_bridge_enabled: true,
          },
        });
  });
  await page.route('**/api/models/*/slicer/bambu', (route) =>
    route.fulfill({
      status: 409,
      json: {
        detail: 'The configured application is unavailable. Download the handoff ZIP instead.',
      },
    }),
  );
  await ready(page);
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  const handoff = page.getByRole('region', { name: 'Prepare in your slicer', exact: true });
  await expect(handoff).toContainText(
    'Could not check this computer. Your handoff downloads are available.',
  );
  await expect(
    handoff.getByRole('button', { name: 'Download Bambu Studio handoff ZIP', exact: true }),
  ).toBeEnabled();
  await handoff.getByRole('button', { name: 'Check again', exact: true }).click();
  await handoff.getByRole('button', { name: 'Open in Bambu Studio', exact: true }).click();
  await expect(handoff.getByRole('alert')).toHaveText(
    'The configured application is unavailable. Download the handoff ZIP instead.',
  );
  await expect(
    handoff.getByRole('button', { name: 'Open in Bambu Studio', exact: true }),
  ).toBeEnabled();
  const downloadEvent = page.waitForEvent('download');
  await handoff
    .getByRole('button', { name: 'Download Bambu Studio handoff ZIP', exact: true })
    .click();
  expect((await downloadEvent).suggestedFilename()).toMatch(/bambu-studio\.zip$/);
});

test('a model edited during download cannot deliver stale slicer geometry', async ({ page }) => {
  const model = await ready(page);
  let release!: () => void;
  let requestArrived!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  const arrived = new Promise<void>((resolve) => {
    requestArrived = resolve;
  });
  await page.route(`**/api/download/${model.id}/bambu`, async (route) => {
    const response = await route.fetch();
    requestArrived();
    await held;
    await route.fulfill({ response });
  });
  const downloads: string[] = [];
  page.on('download', (download) => downloads.push(download.suggestedFilename()));
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  await page
    .getByRole('button', { name: 'Download Bambu Studio handoff ZIP', exact: true })
    .click();
  await arrived;
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();
  await page.getByLabel('Thickness', { exact: true }).fill('7');
  release();
  await expect(page.getByRole('alert')).toContainText('The model changed during download.');
  expect(downloads).toEqual([]);
});

test('mobile slicer selection survives reopening and the dialog remains accessible', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  const handoff = page.getByRole('region', { name: 'Prepare in your slicer', exact: true });
  await handoff.getByRole('radio', { name: /PrusaSlicer/ }).check();
  await expect(handoff.getByRole('link', { name: /PrusaSlicer 2.9.7 release/ })).toHaveAttribute(
    'href',
    programs[1].release_url,
  );
  await expect(handoff).toContainText('No print preset is embedded.');
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await handoff.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('slicer-mobile.png') });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeFocused();
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  await expect(handoff.getByRole('radio', { name: /PrusaSlicer/ })).toBeChecked();
  const downloadEvent = page.waitForEvent('download');
  await handoff
    .getByRole('button', { name: 'Download PrusaSlicer handoff ZIP', exact: true })
    .click();
  const download = await downloadEvent;
  const output = testInfo.outputPath('mobile-prusa.zip');
  await download.saveAs(output);
  expect((await readFile(output)).length).toBeGreaterThan(1000);
});
