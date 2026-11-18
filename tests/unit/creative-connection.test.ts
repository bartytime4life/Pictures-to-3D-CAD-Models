import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readCreativeConnection } from '../../frontend/src/creativeConnection.ts';
import type { CreativeTool } from '../../frontend/src/creative.ts';
import type { AssistantStatus } from '../../frontend/src/types.ts';

const tools: CreativeTool[] = [
  {
    id: 'plan',
    name: 'Plan an experiment',
    description: 'Turn an idea into measured steps.',
    starter: 'Plan a photo relief.',
    requires: ['ollama'],
    output: 'creative-notes-v1',
  },
];
const status: AssistantStatus = {
  running: true,
  models: [{ name: 'local:small', size_bytes: 1000, parameter_size: '1B', quantization: 'Q4' }],
  recommended_model: 'local:small',
  detail: 'Ready.',
};

test('tool descriptions and examples survive an unavailable Ollama status check', async () => {
  const result = await readCreativeConnection(
    new AbortController().signal,
    async <T>(url: string) => {
      if (url === '/api/creative/tools') return { tools } as T;
      throw new TypeError('Failed to fetch');
    },
  );
  assert.deepEqual(result.tools, tools);
  assert.equal(result.toolError, '');
  assert.equal(result.status, null);
  assert.match(result.connectionError, /Start the CAD service and Ollama/);
});

test('a failed tool catalog does not hide verified local-model readiness', async () => {
  const result = await readCreativeConnection(
    new AbortController().signal,
    async <T>(url: string) => {
      if (url === '/api/assistant/status') return status as T;
      throw new Error('The tool catalog is temporarily unavailable.');
    },
  );
  assert.equal(result.tools, null);
  assert.equal(result.toolError, 'The tool catalog is temporarily unavailable.');
  assert.deepEqual(result.status, status);
  assert.equal(result.connectionError, '');
});

test('both services can report actionable failures without rejecting the refresh', async () => {
  const result = await readCreativeConnection(new AbortController().signal, async () => {
    throw new TypeError('Failed to fetch');
  });
  assert.equal(result.tools, null);
  assert.equal(result.status, null);
  assert.match(result.toolError, /Refresh to try again/);
  assert.match(result.connectionError, /refresh/);
  assert.doesNotMatch(result.toolError + result.connectionError, /Failed to fetch/);
});

test('one cancellation signal settles both pending discovery requests', async () => {
  const controller = new AbortController();
  const signals: AbortSignal[] = [];
  const result = readCreativeConnection(
    controller.signal,
    async <T>(_url: string, init?: RequestInit) => {
      assert.ok(init?.signal);
      const signal = init.signal;
      signals.push(signal);
      return new Promise<T>((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), {
          once: true,
        });
      });
    },
  );
  controller.abort();
  const settled = await result;
  assert.deepEqual(signals, [controller.signal, controller.signal]);
  assert.equal(settled.tools, null);
  assert.equal(settled.status, null);
  assert.doesNotMatch(settled.toolError + settled.connectionError, /Aborted/);
});
