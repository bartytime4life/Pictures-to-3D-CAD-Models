import assert from 'node:assert/strict';
import test from 'node:test';
import { DEFAULT_DESIGN } from '../../frontend/src/design.ts';
import {
  createDesignHistory,
  DESIGN_HISTORY_LIMIT,
  recordDesignChange,
  redoDesignChange,
  undoDesignChange,
} from '../../frontend/src/designHistory.ts';
import { targetSizeChange } from '../../frontend/src/quickEditValues.ts';

test('undo and redo restore settings in order without saving model resources', () => {
  const first = { ...DEFAULT_DESIGN };
  const second = { ...first, scale_percent: 125 };
  const third = { ...second, thickness_percent: 150, color: '#abcdef' };
  const history = recordDesignChange(
    recordDesignChange(createDesignHistory(), first, second),
    second,
    third,
  );
  const undo = undoDesignChange(history, third)!;
  assert.deepEqual(undo.design, second);
  const twice = undoDesignChange(undo.history, undo.design)!;
  assert.deepEqual(twice.design, first);
  assert.equal(undoDesignChange(twice.history, twice.design), null);
  const redo = redoDesignChange(twice.history, twice.design)!;
  assert.deepEqual(redo.design, second);
  assert.deepEqual(redoDesignChange(redo.history, redo.design)!.design, third);
  assert.deepEqual(Object.keys(history), ['past', 'future']);
});

test('a new edit after undo drops the abandoned redo branch', () => {
  const first = { ...DEFAULT_DESIGN };
  const second = { ...first, scale_percent: 125 };
  const history = recordDesignChange(createDesignHistory(), first, second);
  const undo = undoDesignChange(history, second)!;
  const alternate = { ...first, thickness_percent: 200 };
  const branched = recordDesignChange(undo.history, first, alternate);
  assert.equal(redoDesignChange(branched, alternate), null);
  assert.deepEqual(undoDesignChange(branched, alternate)!.design, first);
});

test('a no-op edit preserves redo and does not consume a history entry', () => {
  const first = { ...DEFAULT_DESIGN };
  const second = { ...first, scale_percent: 125 };
  const undo = undoDesignChange(recordDesignChange(createDesignHistory(), first, second), second)!;
  assert.equal(recordDesignChange(undo.history, first, { ...first }), undo.history);
});

test('history is bounded and snapshots cannot be changed by mutating current settings', () => {
  let history = createDesignHistory();
  let current = { ...DEFAULT_DESIGN };
  for (let index = 1; index <= 40; index++) {
    const next = { ...current, scale_percent: 100 + index };
    history = recordDesignChange(history, current, next);
    current = next;
  }
  assert.equal(history.past.length, DESIGN_HISTORY_LIMIT);
  assert.equal(history.past[0].scale_percent, 110);
  const undo = undoDesignChange(history, current)!;
  current.color = '#000000';
  undo.design.scale_percent = 200;
  assert.equal(undo.history.future[0].color, DEFAULT_DESIGN.color);
  assert.equal(history.past.at(-1)!.scale_percent, 139);
});

test('starting a new project clears both directions of history', () => {
  const fresh = createDesignHistory();
  assert.equal(undoDesignChange(fresh, DEFAULT_DESIGN), null);
  assert.equal(redoDesignChange(fresh, DEFAULT_DESIGN), null);
});

const source = { width: 80, height: 40, thickness: 4 };

test('target width scales linked XY without changing the reference or other settings', () => {
  const design = { ...DEFAULT_DESIGN, thickness_percent: 150, material: 'petg' as const };
  const result = targetSizeChange(design, source, 'width', '120');
  assert.equal(result.error, '');
  assert.deepEqual(result.design, { ...design, scale_percent: 150 });
  assert.equal((source.height * result.design!.scale_percent) / 100, 60);
  assert.deepEqual(source, { width: 80, height: 40, thickness: 4 });
});

test('target thickness leaves XY and source measurement unchanged', () => {
  const result = targetSizeChange(DEFAULT_DESIGN, source, 'thickness', '6');
  assert.deepEqual(result.design, { ...DEFAULT_DESIGN, thickness_percent: 150 });
  assert.equal(source.thickness, 4);
});

test('blank, non-finite, and nonpositive drafts never commit settings', () => {
  for (const draft of ['', ' ', 'NaN', 'Infinity', '-1', '0', '1e309', 'broken']) {
    const result = targetSizeChange(DEFAULT_DESIGN, source, 'width', draft);
    assert.equal(result.design, null, draft);
    assert.match(result.error, /positive target width/);
  }
});

test('target changes respect scale and final height bounds', () => {
  for (const draft of ['7.99', '320.01']) {
    assert.equal(targetSizeChange(DEFAULT_DESIGN, source, 'width', draft).design, null);
  }
  const tall = { width: 80, height: 1500, thickness: 4 };
  const result = targetSizeChange(DEFAULT_DESIGN, tall, 'width', '160');
  assert.equal(result.design, null);
  assert.match(result.error, /Requested size/);
});

test('missing or invalid source measurements cannot yield a scale', () => {
  for (const invalid of [null, { ...source, width: 0 }, { ...source, height: NaN }]) {
    const result = targetSizeChange(DEFAULT_DESIGN, invalid, 'width', '120');
    assert.equal(result.design, null);
    assert.match(result.error, /reference width and thickness/);
  }
});
