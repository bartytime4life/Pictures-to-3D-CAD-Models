import { test, expect, type Page } from '@playwright/test';

// Regression checks for error recovery, focus, and state consistency. Each scenario reproduces
// a defect found in review; the CAD service is real except where a route forces a failure.
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
    timeout: 60_000,
  });
}

const gif = { name: 'part.gif', mimeType: 'image/gif', buffer: Buffer.from('GIF89a') };

test('Try again repeats only the failed step, with the inputs on screen', async ({ page }) => {
  await ready(page);
  const thickness = page.getByLabel('Thickness', { exact: true });
  const alert = page.getByRole('alert');
  const tryAgain = alert.getByRole('button', { name: 'Try again', exact: true });

  // An error that retrying cannot fix offers no retry, and does not replay an older step.
  await thickness.fill('6');
  await page.getByLabel('Choose photo or project').setInputFiles(gif);
  await expect(alert).toContainText('Choose a PNG, JPEG or WebP image');
  await expect(tryAgain).toHaveCount(0);
  await expect(thickness).toHaveValue('6');
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();

  // A failed build is retryable; the retry builds what is on screen now.
  await page.route(
    '**/api/build',
    (route) =>
      route.fulfill({ status: 503, json: { detail: 'The CAD service is busy. Try again.' } }),
    { times: 1 },
  );
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  await expect(alert).toContainText('The CAD service is busy.');
  await tryAgain.click();
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.export-summary')).toContainText('6.00 mm');
  await page.getByRole('button', { name: 'Back to model', exact: true }).click();

  // A later non-retryable error does not inherit that build retry.
  await page.route(
    '**/api/build',
    (route) =>
      route.fulfill({ status: 503, json: { detail: 'The CAD service is busy. Try again.' } }),
    { times: 1 },
  );
  await thickness.fill('7');
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  await expect(tryAgain).toBeVisible();
  await page.getByLabel('Choose photo or project').setInputFiles(gif);
  await expect(alert).toContainText('Choose a PNG, JPEG or WebP image');
  await expect(tryAgain).toHaveCount(0);
  await expect(thickness).toHaveValue('7');
});

test('a failed outline retrace leaves the model current and retries that trace', async ({
  page,
}) => {
  await ready(page);
  const detail = page.getByLabel('Outline detail', { exact: true });
  await page.route(
    '**/api/trace',
    (route) => route.fulfill({ status: 429, json: { detail: 'Another photo is being traced.' } }),
    { times: 1 },
  );
  await detail.selectOption('fine');
  const alert = page.getByRole('alert');
  await expect(alert).toContainText('Another photo is being traced.');
  await expect(detail).toHaveValue('standard');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  await expect(page.getByText('Previous model · update to apply your changes')).toHaveCount(0);
  await alert.getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(detail).toHaveValue('fine', { timeout: 60_000 });
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
});

test('focus returns to the control that started busy work', async ({ page }) => {
  await ready(page);
  // Building into the export dialog: Escape returns to the main action, not the page body.
  await page.getByLabel('Thickness', { exact: true }).fill('5');
  await page.getByRole('button', { name: 'Update model', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeFocused();

  // A dialog that closes into busy work returns focus to its opener once the work finishes.
  const adjust = page.getByRole('button', { name: 'Adjust outline', exact: true });
  await adjust.click();
  await page.getByRole('button', { name: 'Apply trace', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  await expect(adjust).toBeFocused();
});

test('switching units converts an out-of-range entry instead of relabelling it', async ({
  page,
}) => {
  await ready(page);
  const width = page.getByRole('spinbutton', { name: 'Reference width', exact: true });
  await page.getByRole('button', { name: 'in', exact: true }).click();
  await width.fill('100');
  await expect(page.getByText('Enter the full measured width (0.1–2000 mm).')).toBeVisible();
  await page.getByRole('button', { name: 'mm', exact: true }).click();
  await expect(width).toHaveValue('2540.0000');
  await expect(page.getByText('Enter the full measured width (0.1–2000 mm).')).toBeVisible();
});

test('a restored project with an untidy name rebuilds, and its outline cannot be hidden', async ({
  page,
}) => {
  await ready(page);
  const recipe = {
    format: 'pictures-to-cad',
    version: 1,
    name: '  Plate\tA\u0001 ',
    profile: {
      outer: [
        [0, 0],
        [100, 0],
        [100, 50],
        [0, 50],
      ],
      holes: [],
    },
    width_mm: 50,
    thickness_mm: 3,
  };
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'untidy.cad-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(recipe)),
  });
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  await expect(page.getByRole('textbox', { name: 'Project name', exact: true })).toHaveValue(
    'PlateA',
  );
  await expect(page.getByRole('button', { name: 'Hide outline', exact: true })).toBeDisabled();
});

test('leaving the page releases its temporary model files', async ({ page, request }) => {
  const built = page.waitForResponse((r) => r.url().endsWith('/api/build') && r.ok());
  await ready(page);
  const model = await (await built).json();
  expect((await request.get(model.downloads.step)).status()).toBe(200);
  await page.goto('about:blank');
  await expect.poll(async () => (await request.get(model.downloads.step)).status()).toBe(404);
});

test('profiles that share one bed are not reported as ambiguous', async ({ page }) => {
  await ready(page);
  await page.getByRole('button', { name: /^Design & print/ }).click();
  await page.getByLabel('Search printers', { exact: true }).fill('Guider4');
  const printers = page.getByRole('combobox', { name: 'Printer model', exact: true });
  const guider = printers
    .locator('option')
    .filter({ hasText: /Guider4/ })
    .first();
  await printers.selectOption((await guider.getAttribute('value'))!);
  await page.getByLabel('Nozzle diameter (mm)', { exact: true }).fill('0.4');
  await page.getByText(/^Profile facts for/).click();
  await expect(page.getByText('2 profiles match this nozzle.', { exact: false })).toBeVisible();
  await expect(page.getByText('build-volume check needs manual review')).toHaveCount(0);
});
