import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { workflowState } from '../../frontend/src/workflow';

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
async function ready(page: Page) {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled({
    timeout: 60000,
  });
}

test('workflow guidance separates missing inputs, invalid settings, stale geometry and digital readiness', () => {
  const valid = {
    hasTrace: true,
    hasModel: true,
    current: true,
    validWidth: true,
    validThickness: true,
    designIssue: '',
    busy: null,
  };
  expect(workflowState(valid)).toMatchObject({
    stage: 'export',
    action: 'export',
    footer: 'Solid ready',
  });
  expect(workflowState({ ...valid, current: false })).toMatchObject({
    action: 'build',
    footer: 'Rebuild needed',
  });
  expect(workflowState({ ...valid, current: false, hasModel: false })).toMatchObject({
    action: 'build',
    footer: 'Ready to build',
  });
  expect(workflowState({ ...valid, validWidth: false })).toMatchObject({
    action: 'width',
    footer: 'Awaiting measurements',
  });
  expect(workflowState({ ...valid, validThickness: false })).toMatchObject({ action: 'thickness' });
  expect(workflowState({ ...valid, designIssue: 'Fix the bed margin' })).toMatchObject({
    action: 'design',
    detail: 'Fix the bed margin',
    footer: 'Review settings',
  });
  expect(workflowState({ ...valid, hasTrace: false })).toMatchObject({
    stage: 'photo',
    action: 'photo',
  });
  expect(workflowState({ ...valid, busy: 'Building the CAD solid…' })).toMatchObject({
    action: null,
    stage: null,
    footer: 'Processing',
  });
});

test('guide updates a stale preview without opening export and keeps navigation and status consistent', async ({
  page,
}) => {
  await ready(page);
  const guide = page.getByRole('region', { name: 'Next step', exact: true });
  const nav = page.getByRole('navigation', { name: 'Conversion workflow' });
  await expect(nav.getByRole('button', { name: 'Export', exact: true })).toHaveAttribute(
    'aria-current',
    'step',
  );
  await expect(guide).toContainText('Sample project · demonstration measurements');
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('85');
  await expect(guide).toContainText('Bring your preview up to date');
  await expect(page.locator('.local-status')).toHaveText('Rebuild needed');
  await expect(nav.getByRole('button', { name: 'Scale', exact: true })).toHaveAttribute(
    'aria-current',
    'step',
  );
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route('**/api/build', async (route) => {
    await gate;
    await route.continue();
  });
  await guide.getByRole('button', { name: 'Update preview', exact: true }).click();
  await expect(guide).toContainText('Working on your model');
  await expect(nav.locator('[aria-current="step"]')).toHaveCount(0);
  release();
  await expect(guide).toContainText('Ready to review your model', { timeout: 60000 });
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.locator('.dimensions-summary')).toContainText('85.00 mm');
  await expect(page.locator('.local-status')).toHaveText('Solid ready');
  await expect(guide.getByRole('button', { name: 'Choose an export', exact: true })).toBeFocused();
  await guide.getByRole('button', { name: 'Choose an export', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('region', { name: 'CAD and mesh downloads' })).toBeVisible();
  await expect(dialog.locator('.export-row').filter({ hasText: 'DXF' })).toBeHidden();
  await dialog.getByText('Drawings & source files', { exact: true }).press('Enter');
  await expect(dialog.locator('.export-row').filter({ hasText: 'DXF' })).toBeVisible();
});

test('collapsed invalid design settings have an explanation and a keyboard correction path', async ({
  page,
}) => {
  await ready(page);
  const design = page.getByRole('button', { name: /^Design & print/ });
  await design.click();
  await page.getByRole('spinbutton', { name: 'XY scale (%)', exact: true }).fill('0');
  await design.click();
  const guide = page.getByRole('region', { name: 'Next step', exact: true });
  await expect(guide).toContainText('Set both scale values between 10% and 400%.');
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeDisabled();
  await guide.getByRole('button', { name: 'Fix design settings', exact: true }).press('Enter');
  await expect(design).toHaveAttribute('aria-expanded', 'true');
  await expect(design).toBeFocused();
  await page.getByRole('spinbutton', { name: 'XY scale (%)', exact: true }).fill('125');
  await expect(guide).toContainText('Bring your preview up to date');
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
});

test('recipe-save validation exits export and focuses the notes that need correction', async ({
  page,
}) => {
  await ready(page);
  const height = page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Independent height check' });
  await height.click();
  await page
    .getByRole('spinbutton', { name: 'Measured outside height (mm)', exact: true })
    .fill('34');
  await page
    .getByRole('spinbutton', { name: 'Allowed height deviation (±mm)', exact: true })
    .fill('0.5');
  await height.click();
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  await page.getByRole('button', { name: 'Save editable project recipe', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('alert')).toContainText('Enter both decision inputs');
  const bound = page.getByRole('spinbutton', {
    name: 'Measurement error bound (±mm)',
    exact: true,
  });
  await expect(bound).toBeVisible();
  await expect(bound).toBeFocused();
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  await bound.fill('0.1');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/cad-project.json$/);
});

test('phone guidance jumps directly to a missing measurement and reflows accessibly', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  await page.getByRole('spinbutton', { name: 'Thickness', exact: true }).fill('');
  const guide = page.getByRole('region', { name: 'Next step', exact: true });
  await expect(guide).toContainText('Add the measured thickness');
  await guide.getByRole('button', { name: 'Enter thickness', exact: true }).click();
  await expect(page.getByRole('spinbutton', { name: 'Thickness', exact: true })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  await page.getByRole('spinbutton', { name: 'Thickness', exact: true }).fill('4');
  await guide.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('guided-phone.png') });
});

test('an invalid independent height returns focus to that measurement instead of optional blank bounds', async ({
  page,
}) => {
  await ready(page);
  await page
    .locator('.reference-tool > summary')
    .filter({ hasText: 'Independent height check' })
    .click();
  const height = page.getByRole('spinbutton', {
    name: 'Measured outside height (mm)',
    exact: true,
  });
  await height.fill('-1');
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  await page.getByRole('button', { name: 'Save editable project recipe', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(height).toBeFocused();
  await expect(page.getByRole('alert')).toContainText('Enter a measured height');
});
