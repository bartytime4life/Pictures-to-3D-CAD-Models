import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  acknowledgeProjectWrites,
  beginProjectWrite,
  clearProjectDraft,
  clearSavedProjectDraft,
  finishProjectWrite,
  patchProjectDraft,
  projectDetailsUpdate,
  projectDetailsWrite,
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

test('reverting metadata to its old baseline survives an older successful save', () => {
  const original = { ...project(1), notes: 'Original note.' };
  const submitted = patchProjectDraft(new Map(), original, { notes: 'Submitted note.' }, today);
  const begun = beginProjectWrite(new Map(), original, 1);
  const reverted = patchProjectDraft(
    submitted,
    original,
    { notes: 'Original note.' },
    today,
    begun.writes,
  );
  assert.equal(reverted.size, 1, 'the explicit revert must not disappear during the write');
  const completed = clearSavedProjectDraft(reverted, submitted, original.id, 'details');
  const writes = finishProjectWrite(begun.writes, begun.write);
  const stored = { ...original, notes: 'Submitted note.' };
  const refreshed = acknowledgeProjectWrites(completed, writes, writes, [stored], today);
  assert.equal(readProjectDraft(stored, refreshed.drafts, today).notes, 'Original note.');
  assert.deepEqual(
    projectDetailsUpdate(stored, readProjectDraft(stored, refreshed.drafts, today)),
    { notes: 'Original note.' },
  );
  assert.equal(refreshed.writes.size, 0);
});

test('print completion preserves a newer metadata-status revert and clears no-op print fields', () => {
  const original = project(1);
  const submitted = patchProjectDraft(
    new Map(),
    original,
    { outcome: 'Failed', attemptNotes: 'Warped edge.' },
    today,
  );
  const begun = beginProjectWrite(new Map(), original, 1);
  const edited = patchProjectDraft(submitted, original, { status: 'Queued' }, today, begun.writes);
  const reverted = patchProjectDraft(
    edited,
    original,
    { status: 'Unprinted', attemptNotes: '' },
    today,
    begun.writes,
  );
  const completed = clearSavedProjectDraft(reverted, submitted, original.id, 'attempt');
  const writes = finishProjectWrite(begun.writes, begun.write);
  const stored: LibraryProject = {
    ...original,
    status: 'Failed',
    attempts: [{ date: today, outcome: 'Failed', notes: 'Warped edge.' }],
  };
  const refreshed = acknowledgeProjectWrites(completed, writes, writes, [stored], today);
  const draft = readProjectDraft(stored, refreshed.drafts, today);
  assert.equal(draft.status, 'Unprinted');
  assert.equal(draft.outcome, 'Printed');
  assert.equal(draft.attemptNotes, '');
  assert.deepEqual(projectDetailsUpdate(stored, draft), { status: 'Unprinted' });
  assert.deepEqual(Object.keys(refreshed.drafts.get(original.id)!.fields), ['status']);
});

test('failed writes release true no-op reverts only after a confirmed fresh read', () => {
  const original = { ...project(1), notes: 'Original note.' };
  const submitted = patchProjectDraft(new Map(), original, { notes: 'Submitted note.' }, today);
  const begun = beginProjectWrite(new Map(), original, 1);
  const reverted = patchProjectDraft(
    submitted,
    original,
    { notes: 'Original note.', attemptNotes: 'Keep this new print note.' },
    today,
    begun.writes,
  );
  const writes = finishProjectWrite(begun.writes, begun.write);
  assert.equal(reverted.get(original.id)!.fields.notes, 'Original note.');
  const stale = acknowledgeProjectWrites(reverted, writes, begun.writes, [original], today);
  assert.equal(stale.drafts, reverted, 'a read begun during a write cannot release protection');
  const refreshed = acknowledgeProjectWrites(reverted, writes, writes, [original], today);
  assert.equal(refreshed.drafts.get(original.id)!.fields.notes, undefined);
  assert.equal(
    readProjectDraft(original, refreshed.drafts, today).attemptNotes,
    'Keep this new print note.',
  );
  assert.equal(refreshed.writes.size, 0);
});

test('reopened edits remain protected between write completion and refresh', () => {
  const original = project(1);
  const begun = beginProjectWrite(new Map(), original, 1);
  const settled = finishProjectWrite(begun.writes, begun.write);
  const edited = patchProjectDraft(new Map(), original, { notes: '' }, today, settled);
  assert.equal(edited.size, 1, 'the loaded old baseline is not yet authoritative');
  const stored = { ...original, notes: 'The earlier write completed.' };
  const refreshed = acknowledgeProjectWrites(edited, settled, settled, [stored], today);
  assert.equal(readProjectDraft(stored, refreshed.drafts, today).notes, '');
});

test('overlapping writes and reads cannot prune a newer explicit baseline edit', () => {
  const original = { ...project(1), notes: 'Original note.' };
  const submittedA = patchProjectDraft(new Map(), original, { notes: 'A' }, today);
  const first = beginProjectWrite(new Map(), original, 1);
  const submittedB = patchProjectDraft(submittedA, original, { notes: 'B' }, today, first.writes);
  const second = beginProjectWrite(first.writes, original, 2);
  const reverted = patchProjectDraft(
    submittedB,
    original,
    { notes: 'Original note.' },
    today,
    second.writes,
  );
  const afterA = clearSavedProjectDraft(reverted, submittedA, original.id, 'details');
  const onePending = finishProjectWrite(second.writes, first.write);
  assert.deepEqual(onePending.get(original.id)!.active, [2]);
  const earlyRead = acknowledgeProjectWrites(
    afterA,
    onePending,
    onePending,
    [{ ...original, notes: 'A' }],
    today,
  );
  assert.equal(earlyRead.writes, onePending);
  const afterB = clearSavedProjectDraft(afterA, submittedB, original.id, 'details');
  const settled = finishProjectWrite(onePending, second.write);
  const stale = acknowledgeProjectWrites(
    afterB,
    settled,
    onePending,
    [{ ...original, notes: 'A' }],
    today,
  );
  assert.equal(stale.writes, settled);
  const stored = { ...original, notes: 'B' };
  const refreshed = acknowledgeProjectWrites(afterB, settled, settled, [stored], today);
  assert.equal(readProjectDraft(stored, refreshed.drafts, today).notes, 'Original note.');
  assert.equal(refreshed.writes.size, 0);
  assert.equal(
    finishProjectWrite(settled, first.write),
    settled,
    'duplicate completion is harmless',
  );
});

test('a new write invalidates a read that began after the previous write settled', () => {
  const original = project(1);
  const first = beginProjectWrite(new Map(), original, 1);
  const observed = finishProjectWrite(first.writes, first.write);
  const second = beginProjectWrite(observed, original, 2);
  const drafts = patchProjectDraft(new Map(), original, { notes: '' }, today, second.writes);
  const stale = acknowledgeProjectWrites(drafts, second.writes, observed, [original], today);
  assert.equal(stale.drafts, drafts);
  assert.equal(stale.writes, second.writes);
  const replacement = { ...original, savedAt: 5000 };
  assert.equal(
    patchProjectDraft(new Map(), replacement, { notes: '' }, today, second.writes).size,
    0,
    'another snapshot must not inherit pending-write protection',
  );
  const replacedDraft = patchProjectDraft(
    new Map(),
    replacement,
    { notes: 'Replacement draft.' },
    today,
  );
  const acknowledgedOld = acknowledgeProjectWrites(
    replacedDraft,
    observed,
    observed,
    [original],
    today,
  );
  assert.equal(
    readProjectDraft(replacement, acknowledgedOld.drafts, today).notes,
    'Replacement draft.',
    'an old-snapshot read cannot prune another snapshot’s text',
  );
});

test('saving a reverted stale baseline sends the explicit metadata values to storage', () => {
  const original = { ...project(1), notes: 'Original note.', tags: ['original'] };
  const submitted = patchProjectDraft(
    new Map(),
    original,
    { notes: 'Submitted note.', tags: 'new', status: 'Queued' },
    today,
  );
  const first = beginProjectWrite(new Map(), original, 1);
  const reverted = patchProjectDraft(
    submitted,
    original,
    { notes: 'Original note.', tags: 'original', status: 'Unprinted' },
    today,
    first.writes,
  );
  assert.deepEqual(
    projectDetailsUpdate(original, readProjectDraft(original, reverted, today)),
    {},
    'the rendered baseline alone cannot express this newer write intent',
  );
  assert.equal(
    projectDraftChanged(original, reverted, today, first.writes),
    true,
    'an explicit pending revert still needs a visible unsaved indicator',
  );
  const payload = projectDetailsWrite(original, reverted, today, first.writes);
  assert.deepEqual(payload, { notes: 'Original note.', tags: ['original'], status: 'Unprinted' });
  const second = beginProjectWrite(first.writes, original, 2);
  const afterFirst = clearSavedProjectDraft(reverted, submitted, original.id, 'details');
  const onePending = finishProjectWrite(second.writes, first.write);
  const afterSecond = clearSavedProjectDraft(afterFirst, reverted, original.id, 'details');
  const settled = finishProjectWrite(onePending, second.write);
  const stored = { ...original, ...payload };
  const refreshed = acknowledgeProjectWrites(afterSecond, settled, settled, [stored], today);
  assert.equal(refreshed.drafts.size, 0);
  assert.equal(readProjectDraft(stored, refreshed.drafts, today).notes, 'Original note.');
  assert.deepEqual(projectDetailsWrite(original, new Map(), today, new Map()), {});
});

test('older A completions cannot erase newer A-B-A edits in either form', () => {
  for (const section of ['details', 'attempt'] as const) {
    const original = project(1);
    const field = section === 'details' ? 'notes' : 'attemptNotes';
    const submittedA = patchProjectDraft(new Map(), original, { [field]: 'A' }, today);
    const first = beginProjectWrite(new Map(), original, 1);
    const submittedB = patchProjectDraft(
      submittedA,
      original,
      { [field]: 'B' },
      today,
      first.writes,
    );
    const second = beginProjectWrite(first.writes, original, 2);
    const newestA = patchProjectDraft(submittedB, original, { [field]: 'A' }, today, second.writes);
    const afterA = clearSavedProjectDraft(newestA, submittedA, original.id, section);
    assert.equal(
      readProjectDraft(original, afterA, today)[field],
      'A',
      `${section}: equal text from a newer edit is still unsaved`,
    );
    const pendingB = finishProjectWrite(second.writes, first.write);
    const afterB = clearSavedProjectDraft(afterA, submittedB, original.id, section);
    const settled = finishProjectWrite(pendingB, second.write);
    const stored: LibraryProject =
      section === 'details'
        ? { ...original, notes: 'B' }
        : {
            ...original,
            status: 'Printed',
            attempts: [{ date: today, outcome: 'Printed', notes: 'B' }],
          };
    const refreshed = acknowledgeProjectWrites(afterB, settled, settled, [stored], today);
    assert.equal(
      readProjectDraft(stored, refreshed.drafts, today)[field],
      'A',
      `${section}: the newer A survives B reaching storage`,
    );
    assert.equal(projectDraftChanged(stored, refreshed.drafts, today), true);
  }
});
