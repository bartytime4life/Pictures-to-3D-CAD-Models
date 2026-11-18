import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  clearProjectDraft,
  clearSavedProjectDraft,
  patchProjectDraft,
  projectDetailsUpdate,
  projectDraftChanged,
  PROJECT_DRAFT_LIMIT,
  readProjectDraft,
} from '../../frontend/src/projectDrafts.ts';
import type { ProjectDraftMap } from '../../frontend/src/projectDrafts.ts';
import type { LibraryProject } from '../../frontend/src/projectLibrary.ts';

const today = '2026-11-18';
function project(id: number): LibraryProject {
  return {
    id,
    savedAt: 1000 + id,
    status: 'Unprinted',
    tags: [],
    notes: '',
    attempts: [],
    recipe: {
      format: 'pictures-to-cad',
      version: 3,
      name: `Part ${id}`,
      width_mm: 80,
      thickness_mm: 4,
      profile: {
        outer: [
          [0, 0],
          [80, 0],
          [80, 50],
        ],
        holes: [],
      },
    },
  };
}

test('independent project drafts survive hiding and revisiting a selected project', () => {
  const first = project(1),
    second = project(2);
  const initial = new Map();
  const once = patchProjectDraft(
    initial,
    first,
    { notes: 'Check the lower mounting hole.' },
    today,
  );
  const twice = patchProjectDraft(once, second, { tags: 'gift', attemptNotes: 'Try PETG.' }, today);
  assert.equal(readProjectDraft(first, twice, today).notes, 'Check the lower mounting hole.');
  assert.equal(readProjectDraft(first, twice, today).tags, '');
  assert.equal(readProjectDraft(second, twice, today).notes, '');
  assert.equal(readProjectDraft(second, twice, today).attemptNotes, 'Try PETG.');
  assert.equal(initial.size, 0);
  assert.equal(once.size, 1);
  assert.equal(twice.size, 2);
});

test('metadata and print writes clear only their own draft fields', () => {
  const first = project(1),
    second = project(2);
  const both = patchProjectDraft(
    new Map(),
    first,
    {
      notes: 'Keep this note.',
      status: 'Queued',
      date: '2026-11-17',
      outcome: 'Failed',
      attemptNotes: 'Warped edge.',
    },
    today,
  );
  const drafts = patchProjectDraft(both, second, { notes: 'Other project.' }, today);
  const detailsSaved = clearProjectDraft(drafts, first.id, 'details');
  assert.equal(readProjectDraft(first, detailsSaved, today).notes, '');
  assert.equal(readProjectDraft(first, detailsSaved, today).attemptNotes, 'Warped edge.');
  const attemptSaved = clearProjectDraft(drafts, first.id, 'attempt');
  assert.equal(readProjectDraft(first, attemptSaved, today).notes, 'Keep this note.');
  assert.equal(readProjectDraft(first, attemptSaved, today).attemptNotes, '');
  assert.equal(readProjectDraft(second, attemptSaved, today).notes, 'Other project.');
  assert.equal(clearProjectDraft(drafts, first.id, 'all').has(first.id), false);
  assert.equal(drafts.has(first.id), true);
});

test('a late successful save preserves edits made after its submission', () => {
  const first = project(1);
  const submitted = patchProjectDraft(
    new Map(),
    first,
    { notes: 'Submitted note.', tags: 'measured' },
    today,
  );
  const newer = patchProjectDraft(
    submitted,
    first,
    { notes: 'Newer unsaved note.', attemptNotes: 'Print after measuring.' },
    today,
  );
  const saved = clearSavedProjectDraft(newer, submitted, first.id, 'details');
  const loaded = readProjectDraft(
    { ...first, notes: 'Submitted note.', tags: ['measured'] },
    saved,
    today,
  );
  assert.equal(loaded.notes, 'Newer unsaved note.');
  assert.equal(loaded.tags, 'measured');
  assert.equal(loaded.attemptNotes, 'Print after measuring.');
  assert.equal(readProjectDraft(first, submitted, today).notes, 'Submitted note.');
});

test('a save started without a draft cannot erase a newer draft', () => {
  const first = project(1);
  const submitted = new Map();
  const newer = patchProjectDraft(
    submitted,
    first,
    { attemptNotes: 'Typed after reopening.' },
    today,
  );
  assert.equal(clearSavedProjectDraft(newer, submitted, first.id, 'attempt'), newer);
});

test('a reused ID or changed snapshot never receives another snapshot’s unsaved text', () => {
  const first = project(1);
  const drafts = patchProjectDraft(
    new Map(),
    first,
    { notes: 'Belongs only to the first snapshot.' },
    today,
  );
  assert.equal(readProjectDraft({ ...first, savedAt: 5000 }, drafts, today).notes, '');
  const replacement = { ...first, recipe: { ...first.recipe, width_mm: 95 } };
  assert.equal(readProjectDraft(replacement, drafts, today).notes, '');
  assert.equal(projectDraftChanged(replacement, drafts, today), false);
  const replaced = patchProjectDraft(drafts, replacement, { notes: 'Replacement note.' }, today);
  assert.equal(clearSavedProjectDraft(replaced, drafts, first.id, 'details'), replaced);
});

test('reverting a field releases its draft and bounded cache never evicts other text', () => {
  const first = project(1);
  const edited = patchProjectDraft(new Map(), first, { notes: 'Temporary.' }, today);
  assert.equal(patchProjectDraft(edited, first, { notes: '' }, today).size, 0);
  let full: ProjectDraftMap = new Map();
  for (let id = 1; id <= PROJECT_DRAFT_LIMIT; id++)
    full = patchProjectDraft(full, project(id), { notes: `Note ${id}` }, today);
  assert.throws(
    () => patchProjectDraft(full, project(PROJECT_DRAFT_LIMIT + 1), { notes: 'No room.' }, today),
    /Save some before editing/,
  );
  assert.equal(full.size, PROJECT_DRAFT_LIMIT);
  assert.equal(readProjectDraft(first, full, today).notes, 'Note 1');
  assert.equal(
    readProjectDraft(
      first,
      patchProjectDraft(full, first, { notes: 'Still editable.' }, today),
      today,
    ).notes,
    'Still editable.',
  );
});

test('saving normalizes tags and notes while retaining existing update semantics', () => {
  const first = project(1);
  const drafts = patchProjectDraft(
    new Map(),
    first,
    { status: 'Queued', tags: ' PETG, petg,  measured, ', notes: ' Check fit. ' },
    today,
  );
  assert.deepEqual(projectDetailsUpdate(first, readProjectDraft(first, drafts, today)), {
    status: 'Queued',
    tags: ['PETG', 'measured'],
    notes: 'Check fit.',
  });
  assert.equal(projectDraftChanged(first, drafts, today), true);
  assert.equal(projectDraftChanged(first, new Map(), today), false);
});
