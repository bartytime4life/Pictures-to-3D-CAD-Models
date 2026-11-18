import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const jobs = new Set<string>();
test.beforeEach(async ({ page }) => {
  page.on('response', async (response) => {
    if (/\/api\/(build|relief)$/.test(response.url()) && response.ok()) {
      const result = await response.json().catch(() => null);
      if (result?.id) jobs.add(result.id);
    }
  });
});
test.afterEach(async ({ request }) => {
  for (const id of jobs) await request.delete(`/api/models/${id}`);
  jobs.clear();
});

async function studio(page: Page, hash: string) {
  await page
    .getByRole('navigation', { name: 'Studios', exact: true })
    .locator(`a[href="#${hash}"]`)
    .click();
  await expect(page).toHaveURL(new RegExp(`#${hash}$`));
  await expect(page.locator(`[data-studio="${hash}"]`)).toBeVisible();
}

test('studio navigation preserves unfinished model edits and requires a fresh build', async ({
  page,
}) => {
  await page.goto('/#workbench');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  const width = page.getByLabel('Target width (mm)', { exact: true });
  await width.fill('100');
  await width.press('Enter');
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
  await studio(page, 'knowledge');
  await expect(page.getByRole('heading', { name: 'Knowledge base', exact: true })).toBeVisible();
  await studio(page, 'science');
  await expect(page.getByRole('heading', { name: 'Science lab', exact: true })).toBeVisible();
  await studio(page, 'workbench');
  await expect(width).toHaveValue('100');
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toHaveCount(0);
  const building = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.ok(),
  );
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  const model = await (await building).json();
  expect(model.dimensions.width).toBeCloseTo(100, 7);
  await expect(page.getByRole('dialog')).toBeVisible();
});

test('knowledge and science routes do not eagerly build an unseen sample model', async ({
  page,
}) => {
  const builds: string[] = [];
  page.on('request', (request) => {
    if (/\/api\/(trace|build|relief)$/.test(request.url())) builds.push(request.url());
  });
  await page.goto('/#knowledge');
  await expect(page.getByRole('heading', { name: 'Knowledge base', exact: true })).toBeVisible();
  await studio(page, 'science');
  await expect(page.getByRole('heading', { name: 'Science lab', exact: true })).toBeVisible();
  expect(builds).toEqual([]);
  await expect(page.locator('[data-studio="workbench"]')).toHaveCount(0);
});

test('command search supports keyboard navigation, Escape, and one active dialog', async ({
  page,
}) => {
  await page.goto('/#knowledge');
  await page.getByRole('button', { name: 'Search commands and help', exact: true }).focus();
  await page.keyboard.press('Control+k');
  const dialog = page.getByRole('dialog', { name: 'Where do you want to go?', exact: true });
  await expect(dialog).toBeVisible();
  const search = page.getByRole('combobox', { name: 'Search commands', exact: true });
  await expect(search).toBeFocused();
  await search.fill('Science lab');
  await search.press('Enter');
  await expect(page).toHaveURL(/#science$/);
  await expect(page.getByRole('heading', { name: 'Science lab', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Search commands and help', exact: true }).focus();
  await page.keyboard.press('Control+k');
  await expect(dialog).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(1);
  const accessibility = await new AxeBuilder({ page }).include('.command-dialog[open]').analyze();
  expect(accessibility.violations).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: 'Search commands and help', exact: true }),
  ).toBeFocused();
});

test('source and CAD inspection tools preserve model dimensions and reset predictably', async ({
  page,
}) => {
  await page.goto('/#workbench');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  const source = page.getByRole('region', { name: /^Source inspection/ });
  await page.getByRole('button', { name: 'Zoom source in', exact: true }).click();
  await expect(source).toHaveAttribute('data-source-zoom', '1.25');
  await source.focus();
  await source.press('+');
  await expect(source).toHaveAttribute('data-source-zoom', '1.56');
  await page.getByRole('button', { name: 'Show wireframe', exact: true }).click();
  await page.getByRole('button', { name: 'Show grid', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Show wireframe', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect(page.getByRole('button', { name: 'Show grid', exact: true })).toHaveAttribute(
    'aria-pressed',
    'false',
  );
  await studio(page, 'science');
  await studio(page, 'workbench');
  await expect(source).toHaveAttribute('data-source-zoom', '1.56');
  await expect(page.getByRole('button', { name: 'Show wireframe', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await page.getByRole('button', { name: 'Fit source image', exact: true }).click();
  await page.getByRole('button', { name: 'Reset CAD display', exact: true }).click();
  await expect(source).toHaveAttribute('data-source-zoom', '1.00');
  await expect(page.getByRole('button', { name: 'Show wireframe', exact: true })).toHaveAttribute(
    'aria-pressed',
    'false',
  );
  await expect(page.getByLabel('Target width (mm)', { exact: true })).toHaveValue('80');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
});
