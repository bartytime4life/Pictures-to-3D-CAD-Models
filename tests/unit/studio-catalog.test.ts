import { test } from 'node:test';
import assert from 'node:assert/strict';
import { STUDIO_CATALOG, searchStudios, studioFromHash } from '../../frontend/src/studioCatalog.ts';
import { notesExport } from '../../frontend/src/creative.ts';

test('studio routes accept deep links and safely fall back for unknown targets', () => {
  for (const studio of STUDIO_CATALOG)
    assert.equal(studioFromHash(`#${studio.id}?search=test`), studio.id);
  assert.equal(studioFromHash('#missing'), 'start');
  assert.equal(studioFromHash('#__proto__'), 'start');
  assert.equal(new Set(STUDIO_CATALOG.map((studio) => studio.id)).size, STUDIO_CATALOG.length);
});

test('tool discovery matches multiple words and narrows by category', () => {
  assert.deepEqual(
    searchStudios('heightmap depth').map((studio) => studio.id),
    ['relief'],
  );
  assert.deepEqual(
    searchStudios('ollama').map((studio) => studio.id),
    ['creative'],
  );
  assert.deepEqual(searchStudios('ollama', 'Make'), []);
  assert.equal(searchStudios('missing workspace').length, 0);
});

test('notes exports preserve the submitted brief alongside the model result', () => {
  const input = {
    model: 'qwen3:1.7b',
    tool: 'plan',
    brief: 'Original brief',
    constraints: 'No dimensions',
  };
  const result = {
    format: 'creative-notes-v1' as const,
    tool: 'plan',
    model: input.model,
    elapsed_seconds: 1,
    warnings: [],
    notes: {
      title: 'Plan',
      summary: 'A test',
      sections: [{ title: 'First', body: 'Measure' }],
      next_steps: ['Measure'],
    },
  };
  const saved = JSON.parse(JSON.stringify(notesExport(input, result)));
  assert.equal(saved.input.brief, 'Original brief');
  assert.equal(saved.result.model, input.model);
  assert.equal(saved.format, 'pictures-to-cad-creative-notes');
});
