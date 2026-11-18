import { test, expect } from '@playwright/test';

// The studios share one page. Each stays mounted after it is first opened, so moving between
// tabs keeps every studio's work, and each tab keeps its own title and scroll position.
const models = new Set<string>();

test.afterEach(async ({ request }) => {
  for (const id of models) await request.delete(`/api/models/${id}`);
  models.clear();
});

test('switching studios keeps each studio’s work, title and scroll position', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  let builds = 0;
  page.on('response', async (response) => {
    const url = response.url();
    if (!response.ok() || !(url.endsWith('/api/build') || url.endsWith('/api/relief'))) return;
    if (url.endsWith('/api/build')) builds += 1;
    const model = await response.json().catch(() => null);
    if (model?.id) models.add(model.id);
  });
  const tabs = page.getByRole('navigation', { name: 'Studios', exact: true });

  await page.goto('/#workbench');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  await page.getByRole('button', { name: 'Rename project' }).click();
  const name = page.getByRole('textbox', { name: 'Project name' });
  await name.fill('Kept plate');
  await name.press('Enter');
  const buildsBefore = builds;
  // Leave part-way down the workbench the way the library's "Open in" buttons do, by hash.
  await page.evaluate(() => window.scrollTo(0, 420));
  await page.evaluate(() => {
    window.location.hash = '#relief';
  });
  await expect(page).toHaveTitle('Pictures to CAD — Relief & lithophane studio');
  // A studio opened for the first time starts at its top.
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  await page.getByRole('button', { name: 'Try the moon sample' }).click();
  await expect(page.getByRole('heading', { name: 'Your relief' })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue('Moon relief');

  await tabs.getByRole('link', { name: 'Flat-part workbench' }).click();
  await expect(page).toHaveTitle('Pictures to CAD — Photo to profile workbench');
  // The renamed project and its built model are still here, with nothing rebuilt.
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue('Kept plate');
  await expect(page.getByText('3 through holes detected')).toBeVisible();
  expect(builds).toBe(buildsBefore);
  // Returning puts the workbench back where it was scrolled (within the few pixels the
  // panels settle by as they reappear), not at the top.
  expect(Math.abs((await page.evaluate(() => window.scrollY)) - 420)).toBeLessThan(40);
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeVisible();

  // The browser's Back button returns to the relief studio, also as it was left.
  await page.goBack();
  await expect(page).toHaveURL(/#relief$/);
  await expect(page.getByRole('heading', { name: 'Your relief' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue('Moon relief');
  await page.evaluate(() => {
    window.location.hash = '#knowledge';
  });
  await expect(page).toHaveTitle('Pictures to CAD — Knowledge base');
  // Only the showing studio is in the accessibility tree.
  await expect(page.getByRole('main')).toHaveCount(1);
  expect(errors).toEqual([]);
});
