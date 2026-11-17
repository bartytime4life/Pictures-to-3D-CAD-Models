import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';
import { mkdir, readFile, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';

// These scenarios use the real library of the server under test. A developer's own
// library must not be disturbed, so they run only when it is empty and afterwards
// remove exactly what they added (never "clear library").
const ADDED = ['library-plate.png', 'library-plate-again.png', 'library-moon.png'];

async function idle(request: APIRequestContext) {
  await expect
    .poll(async () => (await (await request.get('/api/library')).json()).job.running, {
      timeout: 120_000,
    })
    .toBe(false);
}

async function emptyLibrary(request: APIRequestContext) {
  const state = await (await request.get('/api/library')).json();
  return state.summary.photos === 0 && state.summary.folders.length === 0 && !state.job.running;
}

async function removeAdded(request: APIRequestContext) {
  await idle(request);
  const state = await (await request.get('/api/library')).json();
  for (const folder of state.summary.folders) {
    if (!String(folder.path).includes('library-e2e-')) continue;
    await request.delete(`/api/library/folders/${folder.id}`);
    await idle(request);
  }
  for (const view of ['all', 'failed']) {
    const page = await (await request.get(`/api/library/photos?limit=500&view=${view}`)).json();
    for (const photo of page.photos) {
      if (!ADDED.includes(photo.name)) continue;
      await request.delete(`/api/library/photos/${photo.id}`);
      await idle(request);
    }
  }
}

async function headerFits(page: Page) {
  for (const width of [1920, 1366, 1280, 1251, 1100, 1001, 800, 375, 320]) {
    await page.setViewportSize({ width, height: 900 });
    const layout = await page.evaluate(() => {
      const bar = document.querySelector('.topbar')!;
      const unlabeled = [...bar.querySelectorAll('nav a')].filter(
        (item) =>
          ![...item.querySelectorAll('span')].some(
            (span) => span.getBoundingClientRect().width > 0 && span.textContent!.trim(),
          ),
      ).length;
      return {
        barOverflow: bar.scrollWidth - bar.clientWidth,
        pageOverflow: document.documentElement.scrollWidth - window.innerWidth,
        unlabeled,
      };
    });
    expect(layout, `library at ${width}px`).toEqual({
      barOverflow: 0,
      pageOverflow: 0,
      unlabeled: 0,
    });
  }
  await page.setViewportSize({ width: 1488, height: 1058 });
}

test.afterEach(async ({ request }) => {
  await removeAdded(request);
});

test('photos are added, measured, checked for copies and opened in the workbench', async ({
  page,
  request,
}) => {
  test.skip(!(await emptyLibrary(request)), 'The photo library of this server is not empty.');
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.goto('/');
  await page
    .getByRole('navigation', { name: 'Studios' })
    .getByRole('link', { name: 'Photo library' })
    .click();
  await expect(page).toHaveURL(/#library$/);
  await expect(
    page.getByRole('navigation', { name: 'Studios' }).getByRole('link', { name: 'Photo library' }),
  ).toHaveAttribute('aria-current', 'page');
  await expect(
    page.getByRole('heading', { name: 'Crunch a whole folder of photos' }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: 'Rescan' })).toBeDisabled();
  await headerFits(page);

  const plate = await readFile('frontend/public/sample.png');
  const moon = await readFile('frontend/public/relief-sample.png');
  await page.getByLabel('Add photos', { exact: true }).setInputFiles([
    { name: ADDED[0], mimeType: 'image/png', buffer: plate },
    { name: ADDED[1], mimeType: 'image/png', buffer: plate },
    { name: ADDED[2], mimeType: 'image/png', buffer: moon },
    { name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('not a picture') },
  ]);
  // The text file is refused in the browser; the two identical plates are stored once.
  await expect(page.getByRole('alert')).toContainText('1 of 4 files were not added');
  await expect(page.getByRole('status').filter({ hasText: 'Done:' })).toContainText(
    '2 photos read',
    { timeout: 120_000 },
  );
  await page.getByRole('button', { name: 'Dismiss' }).first().click();
  const summary = page.getByRole('region', { name: 'Library summary' });
  await expect(summary.locator('.library-stat').first()).toContainText('2');
  const cells = page.locator('button.library-cell');
  await expect(cells).toHaveCount(2);
  await expect(cells.locator('img').first()).toBeVisible();

  // Sorting and filtering are done by the service, so they hold for any library size.
  await page.getByLabel('Sort by').selectOption('name');
  await expect(cells.first()).toHaveAccessibleName(/library-moon\.png/);
  await page.getByLabel('Filter by file name').fill('PLATE');
  await expect(cells).toHaveCount(1);
  await page.getByLabel('Filter by file name').fill('');
  await expect(cells).toHaveCount(2);

  // The two identical plates arrive together; whichever is stored first keeps its name.
  const plateCell = cells.filter({ hasText: /library-plate/ });
  const plateName = (await plateCell.locator('.library-name').textContent()) ?? '';
  expect(ADDED.slice(0, 2)).toContain(plateName);
  await plateCell.click();
  const detail = page.getByRole('complementary', { name: `Details of ${plateName}` });
  await expect(detail.getByRole('img', { name: `Preview of ${plateName}` })).toBeVisible();
  await expect(detail.locator('.library-facts')).toContainText('1,448 × 1,086 · 1.6 MP');
  await expect(detail.locator('.library-facts')).toContainText(/Edge blur\s*\d\.\d\d px/);
  await expect(detail.getByText('Remove from library')).toBeVisible();

  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);

  // The catalogue downloads as CSV with one row per photo.
  const event = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Export CSV' }).click();
  const csv = await (await event).createReadStream();
  let text = '';
  for await (const chunk of csv) text += chunk;
  expect(text.split('\n')[0]).toContain('id,name,path,source,state');
  expect(text).toContain(plateName);
  expect(text).toContain('library-moon.png');

  // Hand the photo to the flat-part workbench: it is traced there like an uploaded file.
  await detail.getByRole('button', { name: 'Open in Flat part' }).click();
  await expect(page).toHaveURL(/#workbench$/);
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue(
    plateName.replace('.png', ''),
    { timeout: 60_000 },
  );
  await expect(page.getByText(plateName).first()).toBeVisible();
  await expect(page.getByText('3 through holes detected')).toBeVisible();
  // Your own photo carries no dimensions: the workbench asks for the measured width.
  await expect(page.getByText('Set your measured width')).toBeVisible();
  expect(errors).toEqual([]);
});

test('a photo opens in the relief studio, and uploads can be removed', async ({
  page,
  request,
}) => {
  test.skip(!(await emptyLibrary(request)), 'The photo library of this server is not empty.');
  const jobs: string[] = [];
  page.on('response', async (response) => {
    if (response.url().endsWith('/api/relief') && response.ok()) {
      const model = await response.json().catch(() => null);
      if (model?.id) jobs.push(model.id);
    }
  });
  await page.goto('/#library');
  await page.getByLabel('Add photos', { exact: true }).setInputFiles([
    {
      name: ADDED[2],
      mimeType: 'image/png',
      buffer: await readFile('frontend/public/relief-sample.png'),
    },
  ]);
  const cells = page.locator('button.library-cell');
  await expect(cells).toHaveCount(1, { timeout: 120_000 });
  await expect(page.getByRole('status').filter({ hasText: 'Done:' })).toBeVisible({
    timeout: 120_000,
  });
  await cells.first().click();
  const detail = page.getByRole('complementary', { name: /Details of/ });
  await detail.getByRole('button', { name: 'Open in Relief' }).click();
  await expect(page).toHaveURL(/#relief$/);
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue('library-moon');
  await expect(page.getByRole('heading', { name: 'Your relief' })).toBeVisible({ timeout: 60_000 });
  for (const id of jobs) await request.delete(`/api/models/${id}`);

  await page.goto('/#library');
  await cells.first().click();
  await page.getByRole('button', { name: 'Remove from library' }).click();
  await expect(page.getByRole('heading', { name: 'Crunch a whole folder of photos' })).toBeVisible({
    timeout: 60_000,
  });
});

test('without folder access or the vision model the library says what still works', async ({
  page,
}) => {
  await page.route('**/api/library', (route) =>
    route.fulfill({
      json: {
        summary: {
          photos: 0,
          ready: 0,
          pending: 0,
          failed: 0,
          bytes: 0,
          groups: 0,
          spare: 0,
          best: 0,
          described: 0,
          uploads: 0,
          folders: [],
        },
        vision: {
          available: false,
          reason: 'No verified DINOv3 weight file is installed.',
          model: null,
          license: 'DINOv3 License (Meta)',
          installed: [],
          standin: false,
          runtime: null,
        },
        job: { running: false },
        folders_allowed: false,
      },
    }),
  );
  await page.goto('/#library');
  await expect(
    page.getByRole('heading', { name: 'Crunch a whole folder of photos' }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: /Add a folder/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Add photos' }).first()).toBeVisible();
  const status = page.getByTestId('vision-status');
  await expect(status).toContainText('Vision model off');
  await status.locator('summary').click();
  await expect(status).toContainText('exact copies');
  await expect(status).toContainText('vision-model.sh install');
  await expect(status).toContainText('No verified DINOv3 weight file is installed.');
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
});

test('a crunch shows its stage, rate and time left, and can be cancelled', async ({ page }) => {
  let cancelled = false;
  await page.route('**/api/library/cancel', (route) => {
    cancelled = true;
    return route.fulfill({ json: { job: { running: false } } });
  });
  await page.route('**/api/library/photos**', (route) =>
    route.fulfill({ json: { total: 0, offset: 0, photos: [] } }),
  );
  await page.route('**/api/library', (route) =>
    route.fulfill({
      json: {
        summary: {
          photos: 5991,
          ready: 1240,
          pending: 4751,
          failed: 0,
          bytes: 9.4e9,
          groups: 0,
          spare: 0,
          best: 0,
          described: 0,
          uploads: 0,
          folders: [{ id: 1, path: '/home/me/Pictures', photos: 5991 }],
        },
        vision: {
          available: true,
          reason: '',
          model: 'DINOv3 ViT-B/16',
          license: 'DINOv3 License (Meta)',
          installed: ['DINOv3 ViT-B/16'],
          standin: false,
          runtime: null,
        },
        job: cancelled
          ? { running: false, stage: 'cancelled', error: null, summary: null }
          : { running: true, stage: 'read', done: 1240, total: 5991, rate: 212.4, eta_seconds: 22 },
        folders_allowed: true,
      },
    }),
  );
  await page.goto('/#library');
  const crunch = page.getByTestId('crunch');
  await expect(crunch).toContainText('1,240 of 5,991 photos');
  await expect(crunch).toContainText('212 per second');
  await expect(crunch).toContainText('about 22 s left');
  await expect(crunch.getByRole('listitem').filter({ hasText: 'Read' })).toHaveAttribute(
    'aria-current',
    'step',
  );
  await expect(crunch.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '21');
  await expect(page.getByRole('button', { name: 'Add folder' })).toBeDisabled();
  await expect(page.getByRole('region', { name: 'Library summary' })).toContainText('9.40 GB');
  await crunch.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByText('Cancelled. Crunch again to finish the rest.')).toBeVisible();
  await expect(crunch).toHaveCount(0);
});

test('installed vision model groups rendered parts and finds similar photos', async ({
  page,
  request,
}, testInfo) => {
  const state = await (await request.get('/api/library')).json();
  test.skip(
    !state.vision.available || state.vision.standin,
    'Optional vision model not installed (./scripts/vision-model.sh)',
  );
  test.skip(!state.folders_allowed, 'This server does not allow folders.');
  test.skip(!(await emptyLibrary(request)), 'The photo library of this server is not empty.');
  test.setTimeout(240_000);
  // Rendered parts with known identity (scripts/vision_scenes.py): four parts, six shots each.
  const folder = path.resolve(testInfo.outputPath('library-e2e-parts'));
  await mkdir(folder, { recursive: true });
  const python = existsSync('.venv/bin/python') ? '.venv/bin/python' : 'python3';
  execFileSync(python, [
    '-c',
    [
      'import sys, pathlib',
      'sys.path.insert(0, "scripts")',
      'import vision_scenes',
      'out = pathlib.Path(sys.argv[1])',
      'for name, data, _ in vision_scenes.dataset(6, 77, ["flange", "gusset", "cross", "gear"]):',
      '    (out / name).write_bytes(data)',
    ].join('\n'),
    folder,
  ]);
  try {
    await page.goto('/#library');
    await page.getByRole('button', { name: 'Add a folder on this computer' }).click();
    const dialog = page.getByRole('dialog', { name: 'Add a folder' });
    await dialog.getByLabel('Folder path').fill(folder);
    await dialog.getByRole('button', { name: 'Go', exact: true }).click();
    await expect(dialog).toContainText('24 pictures directly in');
    await dialog.getByRole('button', { name: 'Add this folder' }).click();
    await expect(page.getByTestId('crunch')).toBeVisible();
    await expect(page.getByRole('status').filter({ hasText: 'Done:' })).toContainText(
      '24 described',
      { timeout: 180_000 },
    );
    await expect(page.getByTestId('vision-status')).toContainText(/DINOv3 ViT-\S+ · /);
    const groups = (await (await request.get('/api/library/groups')).json()).groups;
    // Each part's six shots end up in one group; the four parts stay apart.
    expect(groups.map((group: { size: number }) => group.size).sort()).toEqual([6, 6, 6, 6]);

    await page.getByLabel('Sort by').selectOption('name');
    const cells = page.locator('button.library-cell');
    await expect(cells).toHaveCount(24);
    await cells.filter({ hasText: 'gear-00' }).click();
    const detail = page.getByRole('complementary', { name: /Details of gear-00/ });
    await expect(detail.getByTestId('subject-overlay')).toBeVisible();
    await expect(detail.locator('.library-facts')).toContainText('on the subject');
    await expect(detail.locator('.library-facts')).toContainText(/One of 6|Best shot of 6/);
    // The grid fits its columns to the space the detail panel leaves.
    const fits = () =>
      page.evaluate(() => {
        const grid = document.querySelector('.library-grid-inner')!.getBoundingClientRect();
        return [...document.querySelectorAll('.library-cell')].every(
          (cell) => cell.getBoundingClientRect().right <= grid.right + 1,
        );
      });
    await expect.poll(fits).toBe(true);
    // For the documentation picture only: show an example path, not this machine's
    // temporary test folder.
    await detail.locator('.library-path').evaluate((cell) => {
      cell.firstChild!.textContent = '/home/you/Pictures/parts/gear-00-desk.jpg ';
    });
    await mkdir('docs/images', { recursive: true });
    await page.screenshot({ path: 'docs/images/library.png' });

    await detail.getByRole('button', { name: 'Find similar' }).click();
    await expect(page.getByTestId('filter')).toContainText('photos most like');
    // The five nearest are the other five shots of the gear.
    for (let index = 0; index < 5; index++)
      await expect(cells.nth(index)).toHaveAccessibleName(/^gear-/);
    await page.getByRole('button', { name: /Back to/ }).click();

    await page.getByRole('tab', { name: /Groups/ }).click();
    await expect(page.locator('.library-group')).toHaveCount(4);
    await page.locator('.library-group').first().click();
    await expect(page.getByTestId('filter')).toContainText('One group: 6 photos');
    await expect(cells).toHaveCount(6);
    await page.getByRole('tab', { name: /Best shots/ }).click();
    await expect(cells).toHaveCount(4);
    const accessibility = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(accessibility.violations).toEqual([]);
  } finally {
    await removeAdded(request);
    await rm(folder, { recursive: true, force: true });
  }
});
