import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// These tests exercise the assistant interface using explicit Ollama-response
// fixtures. Tracing, CAD generation and model invalidation use the real API.
// Live model quality and timing are measured by scripts/benchmark_ollama.py.
const installedStatus = {
  running: true,
  models: [
    { name: 'qwen3:1.7b', size_bytes: 1400000000, parameter_size: '1.7B', quantization: 'Q4_K_M' },
    { name: 'qwen3:4b', size_bytes: 2600000000, parameter_size: '4B', quantization: 'Q4_K_M' },
  ],
  recommended_model: 'qwen3:1.7b',
  detail: 'Ollama is ready.',
};

const advice = {
  model: 'qwen3:1.7b',
  answer: 'Try fine outline detail, then review each opening before rebuilding.',
  proposal: { detail: 'fine' },
  warnings: [],
  elapsed_seconds: 0.25,
};

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
    timeout: 60_000,
  });
}

async function installAssistantFixtures(page: Page) {
  await page.route('**/api/assistant/status', (route) => route.fulfill({ json: installedStatus }));
  await page.route('**/api/assistant/chat', (route) => route.fulfill({ json: advice }));
}

async function openAssistant(page: Page) {
  await page.getByRole('button', { name: /^Local AI assistant/ }).click();
  return page.getByRole('region', { name: 'Local AI assistant', exact: true });
}

test('an unavailable local model leaves the CAD workflow usable', async ({ page }) => {
  await page.route('**/api/assistant/status', (route) =>
    route.fulfill({
      json: {
        running: false,
        models: [],
        recommended_model: null,
        detail: 'Ollama is not running on the CAD service’s machine.',
      },
    }),
  );
  await ready(page);
  const assistant = await openAssistant(page);
  await expect(assistant.getByText('Ollama is not running', { exact: false })).toBeVisible();
  await expect(
    assistant.getByText('All CAD tools work without AI.', { exact: false }),
  ).toBeVisible();
  await assistant.getByRole('textbox', { name: 'What would you like help with?' }).fill('Help me');
  await expect(assistant.getByRole('button', { name: 'Ask local AI', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Review export', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.locator('.export-row').filter({ hasText: 'STEP' })).toBeEnabled();
});

test('model choice shares only disclosed context; trace changes require Apply and support Undo', async ({
  page,
}) => {
  await installAssistantFixtures(page);
  let sent: Record<string, unknown> | undefined;
  await page.route('**/api/assistant/chat', async (route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ json: { ...advice, model: sent?.model } });
  });
  await ready(page);
  let traceRequests = 0;
  let buildRequests = 0;
  page.on('request', (request) => {
    if (request.url().endsWith('/api/trace')) traceRequests += 1;
    if (request.url().endsWith('/api/build')) buildRequests += 1;
  });
  const assistant = await openAssistant(page);
  await assistant.getByLabel('Local model', { exact: true }).selectOption('qwen3:4b');
  await assistant.getByRole('button', { name: 'Improve my trace', exact: true }).click();
  await expect(assistant.getByRole('textbox')).toBeFocused();
  expect(sent).toBeUndefined();
  await assistant.getByRole('button', { name: 'Ask local AI', exact: true }).click();
  await expect(assistant.getByText(advice.answer, { exact: true })).toBeVisible();
  expect(sent).toMatchObject({
    model: 'qwen3:4b',
    context: {
      width_mm: 80,
      thickness_mm: 4,
      hole_count: 3,
      has_image: true,
      has_model: true,
      threshold: -1,
      inverted: false,
      detail: 'standard',
    },
  });
  expect(Object.keys(sent!).sort()).toEqual(['context', 'model', 'question']);
  expect(Object.keys(sent!.context as object).sort()).toEqual([
    'design',
    'detail',
    'geometry',
    'has_image',
    'has_model',
    'hole_count',
    'inverted',
    'thickness_mm',
    'threshold',
    'warnings',
    'width_mm',
  ]);
  expect(sent!.context).toMatchObject({
    design: { scale_percent: 100, thickness_percent: 100, material: 'pla' },
    geometry: { width_mm: 80, thickness_mm: 4 },
  });
  await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('standard');
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  expect(traceRequests).toBe(0);
  expect(buildRequests).toBe(0);

  await assistant.getByRole('button', { name: 'Apply suggestion', exact: true }).click();
  await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('fine');
  await expect(
    assistant.getByRole('button', { name: 'Suggestion applied', exact: true }),
  ).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Update model', exact: true })).toBeEnabled();
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('4.00');
  expect(traceRequests).toBe(1);
  expect(buildRequests).toBe(0);

  // Undo must remain discoverable after a follow-up that offers advice only.
  const exportAdvice = 'Use STEP for editing the solid in another CAD application.';
  await page.route('**/api/assistant/chat', (route) =>
    route.fulfill({ json: { ...advice, answer: exportAdvice, proposal: null } }),
  );
  await assistant.getByRole('button', { name: 'Choose an export', exact: true }).click();
  await assistant.getByRole('button', { name: 'Ask local AI', exact: true }).click();
  await expect(assistant.getByText(exportAdvice, { exact: true })).toBeVisible();
  await assistant.getByRole('button', { name: 'Undo suggestion', exact: true }).click();
  await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('standard');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
  await expect(page.getByLabel('Thickness', { exact: true })).toHaveValue('4.00');
  expect(traceRequests).toBe(1);
  expect(buildRequests).toBe(0);
});

test('project edits while AI is answering prevent applying an outdated suggestion', async ({
  page,
}) => {
  await installAssistantFixtures(page);
  let releaseAnswer: (() => void) | undefined;
  const answerGate = new Promise<void>((resolve) => {
    releaseAnswer = resolve;
  });
  await page.route('**/api/assistant/chat', async (route) => {
    await answerGate;
    await route.fulfill({ json: advice });
  });
  await ready(page);
  const assistant = await openAssistant(page);
  await assistant.getByRole('textbox').fill('What detail setting should I try?');
  const request = page.waitForRequest('**/api/assistant/chat');
  await assistant.getByRole('button', { name: 'Ask local AI', exact: true }).click();
  await request;
  await page.getByRole('spinbutton', { name: 'Reference width', exact: true }).fill('95');
  releaseAnswer!();
  await expect(assistant.getByText(advice.answer, { exact: true })).toBeVisible();
  await expect(
    assistant.getByText('Your project changed after this answer.', { exact: false }),
  ).toBeVisible();
  await expect(
    assistant.getByRole('button', { name: 'Apply suggestion', exact: true }),
  ).toBeDisabled();
  await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('standard');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '95',
  );
});

test('stopping an AI wait keeps CAD usable and discards the late answer', async ({ page }) => {
  await installAssistantFixtures(page);
  let releaseAnswer: (() => void) | undefined;
  let responseHandled: (() => void) | undefined;
  const answerGate = new Promise<void>((resolve) => {
    releaseAnswer = resolve;
  });
  const responseDone = new Promise<void>((resolve) => {
    responseHandled = resolve;
  });
  await page.route('**/api/assistant/chat', async (route) => {
    await answerGate;
    try {
      await route.fulfill({ json: advice });
    } finally {
      responseHandled!();
    }
  });
  await ready(page);
  const assistant = await openAssistant(page);
  await assistant.getByRole('textbox').fill('What detail setting should I try?');
  const request = page.waitForRequest('**/api/assistant/chat');
  await assistant.getByRole('button', { name: 'Ask local AI', exact: true }).click();
  await request;
  await assistant.getByRole('button', { name: 'Stop waiting', exact: true }).click();
  await expect(assistant.getByText('Stopped waiting.', { exact: false })).toBeVisible();
  await expect(assistant.getByRole('textbox')).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Review export', exact: true })).toBeEnabled();
  releaseAnswer!();
  await responseDone;
  await expect(assistant.getByText(advice.answer, { exact: true })).toHaveCount(0);
  await expect(page.getByLabel('Outline detail', { exact: true })).toHaveValue('standard');
  await expect(page.getByRole('spinbutton', { name: 'Reference width', exact: true })).toHaveValue(
    '80.00',
  );
});

test('assistant is keyboard-accessible and its expanded mobile layout passes accessibility checks', async ({
  page,
}) => {
  await installAssistantFixtures(page);
  await ready(page);
  await page.setViewportSize({ width: 390, height: 844 });
  const toggle = page.getByRole('button', { name: /^Local AI assistant/ });
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  const assistant = page.getByRole('region', { name: 'Local AI assistant', exact: true });
  await expect(assistant.getByText('Ollama connected', { exact: true })).toBeVisible();
  await assistant.getByRole('button', { name: 'Improve my trace', exact: true }).click();
  await assistant.getByRole('button', { name: 'Ask local AI', exact: true }).click();
  await expect(assistant.getByText(advice.answer, { exact: true })).toBeVisible();
  await expect(assistant.locator('[aria-label="AI response"]')).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(assistant.getByRole('textbox')).toBeHidden();
});
