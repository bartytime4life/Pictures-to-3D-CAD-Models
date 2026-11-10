import { test, expect, type Page } from '@playwright/test';

const jobs = new Set<string>();
const recipe = {
  format: 'pictures-to-cad',
  version: 1,
  name: 'Imported plate',
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

async function importRecipe(page: Page, value: unknown) {
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'import.cad-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(value)),
  });
}

test('a failed project build preserves the current work and retries the import', async ({
  page,
}) => {
  await ready(page);
  const previousId = [...jobs].at(-1)!;
  await page.getByLabel('Thickness', { exact: true }).fill('6');
  await page.route(
    '**/api/build',
    (route) =>
      route.fulfill({
        status: 503,
        json: { detail: 'The CAD service is busy. Try again.' },
      }),
    { times: 1 },
  );
  await importRecipe(page, recipe);
  await expect(page.getByRole('alert')).toContainText('The CAD service is busy.');
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('6');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await expect(page.getByText('Sample · mounting plate', { exact: true })).toBeVisible();
  expect((await page.request.get(`/api/download/${previousId}/step`)).status()).toBe(200);
  await page.getByRole('alert').getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('3.0000');
  await expect(page.getByText('Restored project · outline only')).toBeVisible();
  expect((await page.request.get(`/api/download/${previousId}/step`)).status()).toBe(404);
});

test('a self-intersecting imported outline leaves a current model exportable', async ({ page }) => {
  await ready(page);
  const previousId = [...jobs].at(-1)!;
  await importRecipe(page, {
    ...recipe,
    profile: {
      outer: [
        [0, 0],
        [100, 50],
        [100, 0],
        [0, 50],
      ],
      holes: [],
    },
  });
  await expect(page.getByRole('alert')).toContainText('Outline cannot form a closed solid');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('4.00');
  expect((await page.request.get(`/api/download/${previousId}/step`)).status()).toBe(200);
});
