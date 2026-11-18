import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseRuntimeStatus } from '../../frontend/src/runtimeStatus.ts';
import type { RuntimeCheck } from '../../frontend/src/runtimeStatus.ts';

const core: RuntimeCheck = {
  id: 'packages',
  label: 'CAD and image packages',
  status: 'ready',
  required: true,
  detail: 'Required packages were found. No CAD build was run.',
};
const optional: RuntimeCheck = {
  id: 'ollama',
  label: 'Local AI (optional)',
  status: 'limited',
  required: false,
  detail: 'Photo tracing and CAD work without AI.',
  action: { label: 'Check local AI', command: './scripts/ollama.sh check' },
};

test('runtime metadata preserves core readiness when optional AI needs setup', () => {
  const report = { ready: true, checks: [core, optional] };
  assert.deepEqual(parseRuntimeStatus(report), report);
  const missing = { ...core, status: 'missing' };
  assert.deepEqual(parseRuntimeStatus({ ready: false, checks: [missing, optional] }), {
    ready: false,
    checks: [missing, optional],
  });
});

test('malformed 200 setup responses fail before a React child can be rendered', () => {
  const malformed = [
    null,
    [],
    {},
    { ready: true, checks: [] },
    { ready: true, checks: [null] },
    { ready: true, checks: [{ ...core, label: { message: 'Wrong shape' } }] },
    { ready: true, checks: [{ ...core, detail: ['Wrong shape'] }] },
    { ready: true, checks: [{ ...core, required: 'true' }] },
    { ready: true, checks: [{ ...core, status: 'unknown' }] },
    { ready: true, checks: [{ ...core, status: ['ready'] }] },
    { ready: true, checks: [{ ...core, id: '' }] },
    { ready: true, checks: [core, core] },
  ];
  for (const report of malformed)
    assert.throws(() => parseRuntimeStatus(report), /setup response was incomplete/);
});

test('runtime setup actions require readable labels and commands', () => {
  for (const action of [null, 'setup', {}, { label: 'Setup', command: {} }, { command: 'setup' }])
    assert.throws(
      () => parseRuntimeStatus({ ready: true, checks: [core, { ...optional, action }] }),
      /setup response was incomplete/,
    );
});

test('runtime headlines cannot contradict missing core checks or omit the core entirely', () => {
  for (const report of [
    { ready: true, checks: [{ ...core, status: 'missing' }] },
    { ready: false, checks: [core] },
    { ready: true, checks: [optional] },
  ])
    assert.throws(() => parseRuntimeStatus(report), /setup response was incomplete/);
});

test('runtime reports reject unbounded lists and text while ignoring unrelated metadata', () => {
  assert.throws(
    () =>
      parseRuntimeStatus({
        ready: true,
        checks: Array.from({ length: 33 }, (_, id) => ({ ...core, id: String(id) })),
      }),
    /setup response was incomplete/,
  );
  assert.throws(
    () => parseRuntimeStatus({ ready: true, checks: [{ ...core, detail: 'x'.repeat(4001) }] }),
    /setup response was incomplete/,
  );
  assert.deepEqual(parseRuntimeStatus({ ready: true, checks: [core], extra: {} }), {
    ready: true,
    checks: [core],
  });
});
