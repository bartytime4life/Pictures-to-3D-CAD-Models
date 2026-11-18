import { test } from 'node:test';
import assert from 'node:assert/strict';
import { workbenchEntry } from '../../frontend/src/workspaceNavigation.ts';

test('only explicit workbench entry actions trigger an operation', () => {
  for (const entry of ['photo', 'projects', 'sample'] as const)
    assert.equal(workbenchEntry(`#workbench?open=${entry}`), entry);
  for (const hash of [
    '',
    '#workbench',
    '#workbench?open=delete',
    '#designer?open=photo',
    '#workbench?project=photo',
  ])
    assert.equal(workbenchEntry(hash), null);
  assert.equal(workbenchEntry('#workbench?other=1&open=photo'), 'photo');
});
