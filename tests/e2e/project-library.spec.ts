import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('project snapshots preserve their recipe and print history across reloads', async ({
  page,
}) => {
  await page.goto('/');
  const reviewExport = page.getByRole('button', { name: 'Review export', exact: true });
  await expect(reviewExport).toBeEnabled({ timeout: 60_000 });
  const openLibrary = page.getByRole('button', { name: 'Project library', exact: true });
  const library = page.getByRole('dialog', { name: 'Project library' });
  const saveSnapshot = library.getByRole('button', { name: 'Save current snapshot' });
  const snapshots = library.getByRole('list', { name: 'Saved projects' });
  const history = library.getByRole('list', { name: 'Recorded print attempts' });

  await openLibrary.click();
  await expect(library.getByText('No saved projects yet.', { exact: false })).toBeVisible();
  await saveSnapshot.click();
  await expect(library.getByRole('status')).toHaveText('Project snapshot saved.');
  await saveSnapshot.click();
  await expect(library.getByRole('status')).toHaveText('This snapshot is already in your library.');
  await expect(snapshots.getByRole('listitem')).toHaveCount(1);

  await library.getByRole('combobox', { name: 'Print status', exact: true }).selectOption('Queued');
  await library.getByLabel('Tags (comma separated)').fill('Fixture, fixture, Workshop');
  await library.getByLabel('Project notes').fill('Check hole spacing with a caliper.');
  await library.getByRole('button', { name: 'Save details' }).click();
  await expect(snapshots).toContainText('Fixture, Workshop');
  await library.getByLabel('Print date').fill('2026-02-03');
  await library.getByRole('combobox', { name: 'Outcome' }).selectOption('Failed');
  await library.getByLabel('Print notes').fill('First layer lifted.');
  await library.getByRole('button', { name: 'Record print attempt' }).click();
  await expect(history).toContainText('First layer lifted.');
  await library.getByLabel('Print date').fill('2026-02-04');
  await library.getByRole('combobox', { name: 'Outcome' }).selectOption('Printed');
  await library.getByLabel('Print notes').fill('Brim held on the second attempt.');
  await library.getByRole('button', { name: 'Record print attempt' }).click();
  await expect(history.getByRole('listitem')).toHaveCount(2);

  await page.keyboard.press('Escape');
  await expect(openLibrary).toBeFocused();
  await page.getByLabel('Thickness', { exact: true }).fill('6');
  await openLibrary.click();
  await saveSnapshot.click();
  await expect(snapshots.getByRole('listitem')).toHaveCount(2);
  await expect(snapshots.getByRole('button', { name: /6 mm thick/ })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect(history).toHaveCount(0);

  await page.reload();
  await expect(reviewExport).toBeEnabled({ timeout: 60_000 });
  await openLibrary.click();
  await library.getByLabel('Search projects').fill('workshop');
  const printFilter = library.getByRole('combobox', { name: 'Filter by print status' });
  await printFilter.selectOption('Failed');
  await expect(library.getByText('No projects match your filters.')).toBeVisible();
  await printFilter.selectOption('Printed');
  await expect(snapshots.getByRole('listitem')).toHaveCount(1);
  await expect(library.getByLabel('Project notes')).toHaveValue(
    'Check hole spacing with a caliper.',
  );
  await expect(history.getByRole('listitem').first()).toContainText('2026-02-04');
  await expect(history.getByRole('listitem').last()).toContainText('2026-02-03');

  const downloaded = page.waitForEvent('download');
  await library.getByRole('button', { name: 'Download recipe' }).click();
  const download = await downloaded;
  expect(download.suggestedFilename()).toBe('Mounting-plate.cad-project.json');
  const recipe = JSON.parse(await readFile((await download.path())!, 'utf-8'));
  expect(recipe).toMatchObject({ format: 'pictures-to-cad', width_mm: 80, thickness_mm: 4 });
  expect(recipe).not.toHaveProperty('attempts');

  await library.getByRole('button', { name: 'Open in workbench' }).click();
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  await expect(reviewExport).toBeEnabled();
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('4.0000');
  await expect(page.getByText('Restored project · outline only')).toBeVisible();

  await openLibrary.click();
  await snapshots.getByRole('button', { name: /6 mm thick/ }).click();
  await library.getByRole('button', { name: 'Remove from library' }).click();
  await library.getByRole('button', { name: 'Remove snapshot' }).click();
  await expect(snapshots.getByRole('listitem')).toHaveCount(1);
  await expect(snapshots).toContainText('4 mm thick');
});
