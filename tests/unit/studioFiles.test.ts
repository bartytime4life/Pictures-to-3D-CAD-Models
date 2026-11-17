import assert from 'node:assert/strict';
import test from 'node:test';
import { EMPTY_NOTEBOOK, GUIDES, parseNotebook } from '../../frontend/src/knowledge.ts';
import {
  STUDIO_JSON_MAX_BYTES,
  readStudioJson,
  studioJsonBlob,
} from '../../frontend/src/studioFiles.ts';

test('maximum Unicode and escaped notebooks round-trip through the actual export/import format', async () => {
  for (const character of ['界', '\u0000', '\ud800']) {
    const notebook = parseNotebook({
      ...EMPTY_NOTEBOOK,
      pins: GUIDES.map((guide) => guide.id),
      notes: Object.fromEntries(GUIDES.map((guide) => [guide.id, character.repeat(10_000)])),
    });
    const exported = studioJsonBlob(notebook);
    assert.ok(exported.size > 256_000, 'the previous file cap would reject this valid notebook');
    assert.ok(exported.size <= STUDIO_JSON_MAX_BYTES);
    const imported = parseNotebook(await readStudioJson(new File([exported], 'notebook.json')));
    assert.deepEqual(imported, notebook);
  }
});

test('JSON file import still rejects empty, oversized and invalid documents', async () => {
  for (const content of ['', ' '.repeat(STUDIO_JSON_MAX_BYTES + 1)])
    await assert.rejects(readStudioJson(new File([content], 'invalid.json')), /1 MiB/);
  await assert.rejects(readStudioJson(new File(['{broken'], 'invalid.json')), /read as JSON/);
});
