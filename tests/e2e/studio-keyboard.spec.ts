import { test, expect } from '@playwright/test';
import { LAB_DEFAULTS } from '../../frontend/src/science';
import { EMPTY_NOTEBOOK } from '../../frontend/src/knowledge';

for (const source of ['entered', 'restored', 'imported'] as const) {
  test(`endpoint exploration stays reversible above five pixels when ${source}`, async ({
    page,
  }) => {
    const scenario = {
      ...LAB_DEFAULTS,
      scale: { ...LAB_DEFAULTS.scale, endpointShiftPx: 20 },
    };
    if (source === 'restored') {
      await page.addInitScript((saved) => {
        localStorage.setItem('pictures-to-cad.science.v1', JSON.stringify(saved));
      }, scenario);
    }
    await page.goto('/#science');
    const input = page.getByLabel('Shift per endpoint (px)', { exact: true });
    if (source === 'entered') await input.fill('20');
    if (source === 'imported') {
      await page.getByLabel('Import science scenario JSON').setInputFiles({
        name: 'scenario.json',
        mimeType: 'application/json',
        buffer: Buffer.from(JSON.stringify(scenario)),
      });
      await expect(page.getByRole('status').filter({ hasText: 'Scenario imported' })).toBeVisible();
    }
    await expect(input).toHaveValue('20');
    const slider = page.getByRole('slider', { name: 'Explore endpoint movement' });
    await slider.focus();
    await page.keyboard.press('ArrowLeft');
    await expect(input).toHaveValue('19.75');
    await page.keyboard.press('ArrowRight');
    await expect(input).toHaveValue('20');
    await page.keyboard.press('Home');
    await expect(input).toHaveValue('0');
    await page.keyboard.press('End');
    await expect(input).toHaveValue('20');
    await expect(page.getByRole('img', { name: /Endpoint sensitivity/ })).toHaveAccessibleName(
      /65.704.*98.556/,
    );
    await page.getByRole('button', { name: 'Reset experiment', exact: true }).click();
    await expect(input).toHaveValue('1');
    await slider.focus();
    await page.keyboard.press('End');
    await expect(input).toHaveValue('5');
  });
}

for (const studio of ['science', 'knowledge'] as const) {
  test(`${studio} import has one visible keyboard entry point and still opens files`, async ({
    page,
  }) => {
    await page.goto(`/#${studio}`);
    const button = page.getByRole('button', {
      name: studio === 'science' ? 'Import scenarios' : 'Import notebook',
      exact: true,
    });
    const input = page.getByLabel(
      studio === 'science' ? 'Import science scenario JSON' : 'Import knowledge notebook JSON',
    );
    await button.focus();
    await page.keyboard.press('Tab');
    await expect(input).not.toBeFocused();
    await button.focus();
    const choosing = page.waitForEvent('filechooser');
    await page.keyboard.press('Enter');
    await (
      await choosing
    ).setFiles({
      name: `${studio}.json`,
      mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify(studio === 'science' ? LAB_DEFAULTS : EMPTY_NOTEBOOK)),
    });
    if (studio === 'science') {
      await expect(page.getByRole('status').filter({ hasText: 'Scenario imported' })).toBeVisible();
    } else {
      await expect(
        page.getByRole('button', { name: 'Undo notebook import', exact: true }),
      ).toBeVisible();
    }
  });
}
