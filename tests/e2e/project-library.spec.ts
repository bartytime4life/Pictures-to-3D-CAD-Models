import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';

type HeldLibraryOpen = Window & {
  holdNextLibraryOpen?: boolean;
  libraryOpenHeld?: boolean;
  releaseLibraryOpen?: () => void;
};

test('project snapshots preserve their recipe and print history across reloads', async ({
  page,
}) => {
  await page.goto('/#workbench');
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

test('unsaved project and print forms survive selection, filtering and modal close independently', async ({
  page,
}) => {
  await page.goto('/#workbench');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  const openLibrary = page.getByRole('button', { name: 'Project library', exact: true });
  const library = page.getByRole('dialog', { name: 'Project library', exact: true });
  await openLibrary.click();
  await library.getByRole('button', { name: 'Save current snapshot', exact: true }).click();
  await page.keyboard.press('Escape');
  await page.getByLabel('Thickness', { exact: true }).fill('6');
  await openLibrary.click();
  await library.getByRole('button', { name: 'Save current snapshot', exact: true }).click();
  const snapshots = library.getByRole('list', { name: 'Saved projects' });
  await snapshots.getByRole('button', { name: /4 mm thick/ }).click();
  await library
    .getByRole('textbox', { name: 'Project notes', exact: true })
    .fill('Keep this project draft');
  await library
    .getByRole('textbox', { name: 'Print notes', exact: true })
    .fill('Keep this print draft');
  await snapshots.getByRole('button', { name: /6 mm thick/ }).click();
  await expect(library.getByRole('textbox', { name: 'Project notes', exact: true })).toHaveValue(
    '',
  );
  await snapshots.getByRole('button', { name: /4 mm thick/ }).click();
  await library.getByLabel('Search projects', { exact: true }).fill('no match here');
  await expect(library.getByText('No projects match your filters.')).toBeVisible();
  await library.getByLabel('Search projects', { exact: true }).fill('');
  await expect(library.getByRole('textbox', { name: 'Project notes', exact: true })).toHaveValue(
    'Keep this project draft',
  );
  await page.keyboard.press('Escape');
  await openLibrary.click();
  await snapshots.getByRole('button', { name: /4 mm thick/ }).click();
  await expect(library.getByRole('textbox', { name: 'Print notes', exact: true })).toHaveValue(
    'Keep this print draft',
  );
  await library.getByRole('button', { name: 'Save details', exact: true }).click();
  await expect(library.getByRole('textbox', { name: 'Print notes', exact: true })).toHaveValue(
    'Keep this print draft',
  );
  await library
    .getByRole('textbox', { name: 'Project notes', exact: true })
    .fill('New unsaved project draft');
  await library.getByRole('button', { name: 'Record print attempt', exact: true }).click();
  await expect(library.getByRole('list', { name: 'Recorded print attempts' })).toContainText(
    'Keep this print draft',
  );
  await expect(library.getByRole('textbox', { name: 'Project notes', exact: true })).toHaveValue(
    'New unsaved project draft',
  );
  await expect(library.getByRole('textbox', { name: 'Print notes', exact: true })).toHaveValue('');
});

test('a reopened baseline revert survives a save that completes after the newer edit', async ({
  page,
}) => {
  // Delay one database-open notification before the save creates its transaction.
  // The reopened modal can read the old snapshot while this older save is pending.
  await page.addInitScript(() => {
    const original = IDBFactory.prototype.open;
    IDBFactory.prototype.open = function (name: string, version?: number) {
      const request =
        version === undefined ? original.call(this, name) : original.call(this, name, version);
      request.addEventListener(
        'success',
        (event) => {
          const harness = window as HeldLibraryOpen;
          if (name !== 'pictures-to-cad-project-library' || !harness.holdNextLibraryOpen) return;
          harness.holdNextLibraryOpen = false;
          harness.libraryOpenHeld = true;
          event.stopImmediatePropagation();
          harness.releaseLibraryOpen = () => {
            harness.libraryOpenHeld = false;
            request.dispatchEvent(new Event('success'));
          };
        },
        { capture: true },
      );
      return request;
    };
  });
  await page.goto('/#workbench');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  const openLibrary = page.getByRole('button', { name: 'Project library', exact: true });
  const library = page.getByRole('dialog', { name: 'Project library', exact: true });
  const notes = library.getByRole('textbox', { name: 'Project notes', exact: true });
  const save = library.getByRole('button', { name: 'Save details', exact: true });
  await openLibrary.click();
  await library.getByRole('button', { name: 'Save current snapshot', exact: true }).click();
  await notes.fill('Older submitted note');
  await page.evaluate(() => ((window as HeldLibraryOpen).holdNextLibraryOpen = true));
  await save.click();
  await expect
    .poll(() => page.evaluate(() => (window as HeldLibraryOpen).libraryOpenHeld))
    .toBe(true);
  try {
    await page.keyboard.press('Escape');
    await openLibrary.click();
    await expect(notes).toHaveValue('Older submitted note');
    await notes.fill('');
    await expect(library.getByText(/^Unsaved edits stay in this tab/)).toBeVisible();
  } finally {
    await page.evaluate(() => (window as HeldLibraryOpen).releaseLibraryOpen?.());
  }

  // Observe the real stored result before checking that the newer empty edit survives refresh.
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          new Promise<string>((resolve, reject) => {
            const request = indexedDB.open('pictures-to-cad-project-library', 1);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
              const db = request.result;
              const transaction = db.transaction('projects', 'readonly');
              const all = transaction.objectStore('projects').getAll();
              transaction.oncomplete = () => {
                db.close();
                resolve(all.result[0]?.notes);
              };
              transaction.onabort = () => {
                db.close();
                reject(transaction.error);
              };
            };
          }),
      ),
    )
    .toBe('Older submitted note');
  await expect(notes).toHaveValue('');
  await expect(library.getByText(/^Unsaved edits stay in this tab/)).toBeVisible();
  await save.click();
  await expect(library.getByRole('status')).toHaveText('Project details saved.');
  await page.reload();
  await openLibrary.click();
  await expect(notes).toHaveValue('');
});
