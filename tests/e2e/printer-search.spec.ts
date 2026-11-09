import { expect, test } from '@playwright/test';

for (const viewport of [
  { width: 1488, height: 1058 },
  { width: 390, height: 844 },
]) {
  test(`printer search explains empty results and recovers without changing the selected printer at ${viewport.width}px`, async ({
    page,
    request,
  }) => {
    await page.setViewportSize(viewport);
    const initialBuild = page.waitForResponse(
      (response) => response.url().endsWith('/api/build') && response.ok(),
    );
    await page.goto('/');
    const model = await (await initialBuild).json();
    try {
      await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
      await page.getByRole('button', { name: /^Design & print/ }).click();
      const search = page.getByRole('searchbox', { name: 'Search printers', exact: true });
      const printers = page.getByRole('combobox', { name: 'Printer model', exact: true });
      const searchStatus = page.locator('#printer-search-status');

      await expect(searchStatus).toHaveAttribute('role', 'status');
      await expect(searchStatus).toContainText('in the catalog');
      await search.fill('Prusa MK4S');
      const option = printers
        .locator('option')
        .filter({ hasText: /Prusa.*MK4S/i })
        .first();
      await expect(option).toHaveCount(1);
      const printerId = await option.getAttribute('value');
      await printers.selectOption(printerId!);
      const bedWidth = await page.getByLabel('Bed width (mm)', { exact: true }).inputValue();

      await search.fill('no-such-printer-model');
      await expect(searchStatus).toContainText('0 matching models');
      await expect(
        page.getByText('No printers match “no-such-printer-model”.', { exact: true }),
      ).toBeVisible();
      await expect(page.getByText(/Try a shorter brand or model name/)).toBeVisible();
      await expect(
        page.getByText(/Your current selection, .*MK4S.*is still selected/),
      ).toBeVisible();
      await expect(printers).toHaveValue(printerId!);

      const clear = page.getByRole('button', { name: 'Clear printer search', exact: true });
      const bounds = await clear.boundingBox();
      expect(bounds?.width).toBeGreaterThanOrEqual(44);
      expect(bounds?.height).toBeGreaterThanOrEqual(44);
      await clear.focus();
      await page.keyboard.press('Enter');
      await expect(search).toHaveValue('');
      await expect(search).toBeFocused();
      await expect(clear).toBeHidden();
      await expect(page.getByText(/No printers match/)).toBeHidden();
      await expect(printers).toHaveValue(printerId!);
      await expect(page.getByLabel('Bed width (mm)', { exact: true })).toHaveValue(bedWidth);
      expect(await printers.locator('option').count()).toBeGreaterThan(2);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      ).toBe(true);
    } finally {
      await request.delete(`/api/models/${model.id}`);
    }
  });
}
