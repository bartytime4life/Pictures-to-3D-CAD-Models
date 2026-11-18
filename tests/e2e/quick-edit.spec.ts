import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import type { ModelResult } from '../../frontend/src/types';

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

async function ready(page: Page): Promise<ModelResult> {
  const built = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.ok(),
  );
  await page.goto('/#workbench');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60_000,
  });
  await expect(page.getByRole('region', { name: 'Quick model editing' })).toBeVisible();
  return (await built).json();
}

function editor(page: Page) {
  return page.getByRole('region', { name: 'Quick model editing' });
}

async function setTarget(page: Page, dimension: 'width' | 'thickness', value: string) {
  const input = editor(page).getByRole('spinbutton', { name: `Target ${dimension} (mm)` });
  await input.fill(value);
  await input.press('Enter');
}

async function updatePreview(page: Page): Promise<ModelResult> {
  const response = page.waitForResponse(
    (result) => result.url().endsWith('/api/build') && result.ok(),
  );
  await page
    .getByRole('region', { name: 'Next step', exact: true })
    .getByRole('button', { name: 'Update preview', exact: true })
    .click();
  const model = await (await response).json();
  await expect(page.locator('.local-status')).toHaveText('Solid ready');
  return model;
}

test('target dimensions preserve measurements and undo after building requires fresh exports', async ({
  page,
}) => {
  const original = await ready(page);
  await setTarget(page, 'width', '120');
  await setTarget(page, 'thickness', '6');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await expect(page.getByRole('spinbutton', { name: 'Thickness', exact: true })).toHaveValue(
    '4.00',
  );
  const scaled = await updatePreview(page);
  expect(scaled.dimensions.width).toBeCloseTo(120, 4);
  expect(scaled.dimensions.height).toBeCloseTo(original.dimensions.height * 1.5, 3);
  expect(scaled.dimensions.thickness).toBeCloseTo(6, 4);
  await expect
    .poll(async () => (await page.request.get(`/api/download/${original.id}/step`)).status())
    .toBe(404);

  await editor(page).getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(editor(page).getByRole('spinbutton', { name: 'Target thickness (mm)' })).toHaveValue(
    '4',
  );
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '120',
  );
  await expect(page.locator('.local-status')).toHaveText('Rebuild needed');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toHaveCount(0);
  await expect(page.getByRole('dialog')).toHaveCount(0);

  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(
    '**/api/build',
    async (route) => {
      await gate;
      await route.continue();
    },
    { times: 1 },
  );
  const nextBuild = page.waitForResponse(
    (response) => response.url().endsWith('/api/build') && response.ok(),
  );
  await page.getByRole('button', { name: 'Update model', exact: true }).click();
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
  await expect(editor(page).getByRole('button', { name: 'Redo', exact: true })).toBeDisabled();
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toBeDisabled();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  release();
  const rebuilt = await (await nextBuild).json();
  expect(rebuilt.id).not.toBe(scaled.id);
  expect(rebuilt.dimensions.width).toBeCloseTo(120, 4);
  expect(rebuilt.dimensions.thickness).toBeCloseTo(4, 4);
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 60_000 });
  await expect
    .poll(async () => (await page.request.get(`/api/download/${scaled.id}/step`)).status())
    .toBe(404);
  expect((await page.request.get(`/api/download/${rebuilt.id}/step`)).status()).toBe(200);
});

test('redo restores the undone design and a new edit discards its abandoned branch', async ({
  page,
}) => {
  await ready(page);
  await editor(page).getByRole('button', { name: '125%', exact: true }).click();
  await editor(page).getByRole('button', { name: '150%', exact: true }).click();
  await editor(page).getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '100',
  );
  await editor(page).getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '120',
  );
  await editor(page).getByRole('button', { name: 'Undo', exact: true }).click();
  await setTarget(page, 'thickness', '6');
  await expect(editor(page).getByRole('button', { name: 'Redo', exact: true })).toBeDisabled();
  const model = await updatePreview(page);
  expect(model.design).toMatchObject({ scale_percent: 125, thickness_percent: 150 });
  expect(model.dimensions.width).toBeCloseTo(100, 4);
  expect(model.dimensions.thickness).toBeCloseTo(6, 4);
});

test('reference edits and successful project imports clear design history', async ({ page }) => {
  await ready(page);
  await editor(page).getByRole('button', { name: '125%', exact: true }).click();
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeEnabled();
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('90');
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
  await expect(editor(page).getByRole('button', { name: 'Redo', exact: true })).toBeDisabled();
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '112.5',
  );

  await editor(page).getByRole('button', { name: '150%', exact: true }).click();
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeEnabled();
  await page.getByLabel('Choose photo or project').setInputFiles({
    name: 'quick-edit-import.cad-project.json',
    mimeType: 'application/json',
    buffer: Buffer.from(
      JSON.stringify({
        format: 'pictures-to-cad',
        version: 1,
        name: 'New measured plate',
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
      }),
    ),
  });
  await expect(page.locator('.notice')).toHaveText('Project restored and rebuilt.', {
    timeout: 60_000,
  });
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '50',
  );
  await expect(editor(page).getByRole('spinbutton', { name: 'Target thickness (mm)' })).toHaveValue(
    '3',
  );
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
  await expect(editor(page).getByRole('button', { name: 'Redo', exact: true })).toBeDisabled();
});

test('typing an advanced numeric edit is one undo step without restoring partial numbers', async ({
  page,
}) => {
  await ready(page);
  await editor(page)
    .getByRole('button', { name: 'All design & print settings', exact: true })
    .click();
  const scale = page.getByRole('spinbutton', { name: 'XY scale (%)', exact: true });
  await expect(scale).toHaveValue('100');
  await scale.fill('');
  await scale.pressSequentially('125');
  await scale.press('Tab');
  await expect(scale).toHaveValue('125');
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '100',
  );
  await editor(page).getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(scale).toHaveValue('100');
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '80',
  );
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
  await editor(page).getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(scale).toHaveValue('125');
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '100',
  );
});

test('pasting the unchanged value then incrementing starts history and clears an old redo branch', async ({
  page,
}) => {
  await ready(page);
  await editor(page).getByRole('button', { name: '125%', exact: true }).click();
  await editor(page).getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(editor(page).getByRole('button', { name: 'Redo', exact: true })).toBeEnabled();
  await editor(page)
    .getByRole('button', { name: 'All design & print settings', exact: true })
    .click();
  const scale = page.getByRole('spinbutton', { name: 'XY scale (%)', exact: true });
  await scale.fill('');
  // fill emits one input event, like replacing a selection with pasted text.
  await scale.fill('100');
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
  await expect(editor(page).getByRole('button', { name: 'Redo', exact: true })).toBeEnabled();
  await scale.press('ArrowUp');
  await scale.press('Tab');
  await expect(scale).toHaveValue('101');
  await expect(editor(page).getByRole('button', { name: 'Redo', exact: true })).toBeDisabled();
  await editor(page).getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(scale).toHaveValue('100');
  await editor(page).getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(scale).toHaveValue('101');
});

test('correcting an oversized design after a reference change establishes a valid history baseline', async ({
  page,
}) => {
  await ready(page);
  await editor(page)
    .getByRole('button', { name: 'All design & print settings', exact: true })
    .click();
  const scale = page.getByRole('spinbutton', { name: 'XY scale (%)', exact: true });
  await scale.fill('400');
  await scale.press('Tab');
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('1000');
  await expect(page.getByRole('region', { name: 'Next step', exact: true })).toContainText(
    'Requested size must stay within',
  );
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
  await scale.fill('100');
  await scale.press('Tab');
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '1000',
  );
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
  await scale.fill('125');
  await scale.press('Tab');
  await editor(page).getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(scale).toHaveValue('100');
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
});

test('invalid target drafts stay local and a direct update click commits a valid draft first', async ({
  page,
}) => {
  await ready(page);
  const target = editor(page).getByRole('spinbutton', { name: 'Target width (mm)' });
  await target.fill('');
  await target.press('Tab');
  await expect(target).toHaveAttribute('aria-invalid', 'true');
  await expect(editor(page).getByRole('alert')).toContainText('Enter a positive target width');
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await target.fill('400');
  await target.press('Enter');
  await expect(editor(page).getByRole('alert')).toContainText('between 10% and 400%');
  await target.focus();
  await target.press('Escape');
  await expect(target).toHaveValue('80');
  await expect(target).toHaveAttribute('aria-invalid', 'false');
  await expect(editor(page).getByRole('alert')).toHaveCount(0);

  // Change one setting first so the update action is already visible, then
  // click it directly while a second valid target remains focused.
  await editor(page).getByRole('button', { name: '125%', exact: true }).click();
  await target.fill('120');
  const built = await updatePreview(page);
  expect(built.dimensions.width).toBeCloseTo(120, 4);
  expect(built.design?.scale_percent).toBeCloseTo(150, 4);
});

test('quick editing fits a narrow screen and its controls are accessible', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  await editor(page).scrollIntoViewIfNeeded();
  const bounds = await editor(page).boundingBox();
  expect(bounds).not.toBeNull();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(391);
  await expect(
    editor(page).getByRole('button', { name: 'Restore measured size', exact: true }),
  ).toBeVisible();
  await setTarget(page, 'width', '100');
  await expect(editor(page).getByRole('button', { name: 'Undo', exact: true })).toBeEnabled();
  await editor(page).getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(editor(page).getByRole('spinbutton', { name: 'Target width (mm)' })).toHaveValue(
    '80',
  );
  const accessibility = await new AxeBuilder({ page }).include('.quick-edit').analyze();
  expect(accessibility.violations).toEqual([]);
});
