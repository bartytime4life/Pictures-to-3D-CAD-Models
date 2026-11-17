import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('desktop studio selectors include their visible content and both full pages pass axe', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/#science');
  for (const [title, visibleName] of [
    ['Pixel scale', /01\s+Pixel scale\s+Length from a known reference/],
    ['Layer stack', /02\s+Layer stack\s+Height in discrete steps/],
    ['Measured fit', /03\s+Measured fit\s+Learn from a test coupon/],
  ] as const) {
    const button = page.getByRole('button', { name: new RegExp(title) });
    await expect(button).toHaveAccessibleName(visibleName);
    await button.click();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
  await page.getByRole('link', { name: 'Knowledge', exact: true }).click();
  await expect(
    page.getByRole('button', { name: /Capture a traceable flat part/ }),
  ).toHaveAccessibleName(
    /Getting started\s+Capture a traceable flat part\s+Give the outline, reference and through holes a clear view\./,
  );
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});
