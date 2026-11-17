import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseShapeDraft, shapeDraftIssue, shapeTemplate } from '../../frontend/src/shapes.ts';

test('starter designs roundtrip as editable shape documents', () => {
  for (const id of ['plate', 'washer', 'tab', 'blank']) {
    const draft = shapeTemplate(id);
    assert.equal(shapeDraftIssue(draft), '');
    assert.deepEqual(
      parseShapeDraft(
        JSON.parse(JSON.stringify({ format: 'pictures-to-cad-shapes', version: 1, design: draft })),
      ),
      draft,
    );
  }
});
test('invalid edits block building without discarding the draft', () => {
  const draft = shapeTemplate('plate');
  assert.match(shapeDraftIssue({ ...draft, thickness_mm: 0 }), /Thickness/);
  assert.match(
    shapeDraftIssue({
      ...draft,
      shapes: draft.shapes.map((shape) => ({ ...shape, operation: 'cut' })),
    }),
    /material/,
  );
  const base = { ...draft.shapes[0], corner_mm: 50 };
  assert.match(shapeDraftIssue({ ...draft, shapes: [base] }), /radius/);
  assert.match(
    shapeDraftIssue({ ...draft, shapes: [{ ...base, corner_mm: 0, x_mm: Infinity }] }),
    /positions/,
  );
});
test('shape import rejects corrupt files and duplicate IDs', () => {
  assert.throws(() => parseShapeDraft(null));
  assert.throws(() =>
    parseShapeDraft({
      format: 'pictures-to-cad-shapes',
      version: 1,
      design: { name: 'x', thickness_mm: 4, shapes: [null] },
    }),
  );
  const draft = shapeTemplate('blank');
  assert.throws(
    () =>
      parseShapeDraft({
        format: 'pictures-to-cad-shapes',
        version: 1,
        design: { ...draft, shapes: [draft.shapes[0], draft.shapes[0]] },
      }),
    /unique/,
  );
});
