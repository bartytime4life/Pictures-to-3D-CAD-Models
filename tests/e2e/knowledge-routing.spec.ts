import { test, expect } from '@playwright/test';

test('knowledge retains manual search across studios and honors explicit search links', async ({
  page,
}) => {
  await page.goto('/#knowledge?search=known%20object');
  const search = page.getByRole('searchbox', { name: 'Search knowledge base', exact: true });
  await expect(search).toHaveValue('known object');
  await search.fill('through holes');

  await page.getByRole('link', { name: 'Science lab', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Science lab', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Knowledge base', exact: true }).click();
  await expect(search).toHaveValue('through holes');

  await page.evaluate(() => {
    window.location.hash = '#knowledge?topic=Measurement';
  });
  await expect(search).toHaveValue('through holes');
  await page.evaluate(() => {
    window.location.hash = '#knowledge?search=fit';
  });
  await expect(search).toHaveValue('fit');

  // Repeating the launcher's current URL must still replace a later manual draft.
  await search.fill('quarter');
  await page.getByRole('button', { name: 'Search commands and help', exact: true }).click();
  await page.getByRole('combobox', { name: 'Search commands', exact: true }).fill('fit');
  await page.getByRole('option', { name: /^Search knowledge for “fit”/ }).click();
  await expect(search).toHaveValue('fit');

  await page.evaluate(() => {
    window.location.hash = '#knowledge?search=';
  });
  await expect(search).toHaveValue('');
});
