import assert from 'node:assert/strict';
import test from 'node:test';
import {
  LAB_DEFAULTS,
  experimentFromHash,
  fitScenario,
  layerBands,
  layerScenario,
  parseLabScenario,
  scaleScenario,
} from '../../frontend/src/science.ts';
import {
  EMPTY_NOTEBOOK,
  GUIDES,
  parseNotebook,
  searchGuides,
} from '../../frontend/src/knowledge.ts';

test('a 100 pixel reference representing 25 mm scales a 320 pixel part to 80 mm', () => {
  const result = scaleScenario({
    knownMm: 25,
    referencePx: 100,
    outlinePx: 320,
    endpointShiftPx: 1,
  });
  assert.equal(result.mmPerPixel, 0.25);
  assert.equal(result.widthMm, 80);
  assert.ok(result.lowMm < 80 && result.highMm > 80);
  assert.ok(result.highMm - 80 > 80 - result.lowMm, 'inverse span sensitivity is asymmetric');
});

test('zero endpoint movement collapses the scenario range exactly', () => {
  const result = scaleScenario({ ...LAB_DEFAULTS.scale, endpointShiftPx: 0 });
  assert.equal(result.lowMm, result.widthMm);
  assert.equal(result.highMm, result.widthMm);
});

test('a longer reference reduces the same pixel-shift effect at the same scale', () => {
  const small = scaleScenario({
    knownMm: 25,
    referencePx: 100,
    outlinePx: 320,
    endpointShiftPx: 1,
  });
  const large = scaleScenario({
    knownMm: 50,
    referencePx: 200,
    outlinePx: 320,
    endpointShiftPx: 1,
  });
  assert.equal(small.widthMm, large.widthMm);
  assert.ok(large.highMm - large.lowMm < small.highMm - small.lowMm);
});

test('endpoint collapse and invalid numeric values cannot produce a scale result', () => {
  assert.throws(
    () => scaleScenario({ ...LAB_DEFAULTS.scale, referencePx: 2, endpointShiftPx: 1 }),
    /exceed twice/,
  );
  for (const knownMm of [0, -1, NaN, Infinity, 2001])
    assert.throws(() => scaleScenario({ ...LAB_DEFAULTS.scale, knownMm }));
});

test('layer stack counts first layer separately and rounds up remaining coverage', () => {
  assert.deepEqual(layerScenario({ heightMm: 1, firstLayerMm: 0.3, layerMm: 0.2, nozzleMm: 0.4 }), {
    count: 5,
    stackMm: 1.1,
    excessMm: 1.1 - 1,
    nozzleRatio: 0.5,
    profileReview: false,
  });
  assert.equal(layerScenario(LAB_DEFAULTS.layers).count, 20);
});

test('floating point integer contact does not invent an extra layer', () => {
  const result = layerScenario({ heightMm: 0.9, firstLayerMm: 0.2, layerMm: 0.1, nozzleMm: 0.4 });
  assert.equal(result.count, 8);
  assert.ok(Math.abs(result.stackMm - 0.9) < 1e-12);
  assert.equal(
    layerScenario({ heightMm: 0.90001, firstLayerMm: 0.2, layerMm: 0.1, nozzleMm: 0.4 }).count,
    9,
  );
});

test('a target thinner than the first layer remains one layer and reports excess', () => {
  const result = layerScenario({ ...LAB_DEFAULTS.layers, heightMm: 0.1, firstLayerMm: 0.2 });
  assert.equal(result.count, 1);
  assert.equal(result.excessMm, 0.1);
  assert.equal(layerScenario({ ...LAB_DEFAULTS.layers, firstLayerMm: 0.32 }).profileReview, true);
});

test('one and two layer diagrams remain above the bed and inside the viewBox', () => {
  for (const count of [1, 2, 20, 26, 200_000]) {
    const bands = layerBands(count);
    assert.equal(bands.length, Math.min(count, 26));
    assert.equal(bands.filter((band) => band.first).length, 1);
    for (const band of bands) {
      assert.ok(band.y >= 0, 'band starts inside the viewBox');
      assert.ok(band.height > 0, 'band has visible height');
      assert.ok(band.y + band.height <= 185, 'band ends above the bed');
    }
    for (let index = 1; index < bands.length; index += 1)
      assert.ok(bands[index].y + bands[index].height < bands[index - 1].y, 'bands do not overlap');
  }
});

test('science deep links select only explicit, supported experiments', () => {
  for (const experiment of ['scale', 'layers', 'fit'])
    assert.equal(experimentFromHash(`#science?experiment=${experiment}`), experiment);
  for (const hash of [
    '#science',
    '#science?experiment=',
    '#science?experiment=unknown',
    '#knowledge?experiment=fit',
  ])
    assert.equal(experimentFromHash(hash), null);
  assert.equal(
    GUIDES.find((guide) => guide.id === 'measurement')?.action.href,
    '#science?experiment=scale',
  );
  assert.equal(GUIDES.find((guide) => guide.id === 'fit')?.action.href, '#science?experiment=fit');
});

test('fit compensation corrects observed additive hole bias with diametral clearance', () => {
  const result = fitScenario({
    cadHoleMm: 10,
    measuredHoleMm: 9.75,
    shaftMm: 10,
    clearanceMm: 0.2,
  });
  assert.equal(result.biasMm, -0.25);
  assert.equal(result.targetHoleMm, 10.2);
  assert.equal(result.nextCadHoleMm, 10.45);
  assert.equal(result.radialClearanceMm, 0.1);
});

test('interference remains signed and nonpositive target diameters are rejected', () => {
  const result = fitScenario({ ...LAB_DEFAULTS.fit, clearanceMm: -0.2 });
  assert.equal(result.radialClearanceMm, -0.1);
  assert.throws(
    () => fitScenario({ ...LAB_DEFAULTS.fit, shaftMm: 0.1, clearanceMm: -0.2 }),
    /positive/,
  );
});

test('scenario import validates every experiment and copies only supported fields', () => {
  const source = structuredClone(LAB_DEFAULTS);
  assert.deepEqual(parseLabScenario({ ...source, unrelated: 'discard' }), source);
  for (const invalid of [
    null,
    {},
    { ...source, version: 2 },
    { ...source, active: 'unknown' },
    { ...source, scale: { ...source.scale, knownMm: '24.26' } },
    { ...source, fit: { ...source.fit, shaftMm: -1 } },
  ])
    assert.throws(() => parseLabScenario(invalid));
  const result = parseLabScenario(source);
  result.scale.knownMm = 30;
  assert.equal(source.scale.knownMm, 24.26);
});

test('knowledge search combines words, category and pinned IDs', () => {
  assert.ok(searchGuides('  KNOWN object ').some((guide) => guide.id === 'measurement'));
  assert.deepEqual(searchGuides('known object', 'Printing'), []);
  assert.deepEqual(
    searchGuides('', 'All guides', ['fit']).map((guide) => guide.id),
    ['fit'],
  );
  assert.equal(searchGuides('something-not-in-any-guide').length, 0);
  assert.equal(searchGuides('').length, GUIDES.length);
});

test('notebook imports preserve text literally, deduplicate pins and ignore unrelated fields', () => {
  const notebook = parseNotebook({
    ...EMPTY_NOTEBOOK,
    pins: ['fit', 'fit'],
    notes: { fit: '<script>not executable</script>\n10.2 mm' },
    other: 'discard',
  });
  assert.deepEqual(notebook.pins, ['fit']);
  assert.equal(notebook.notes.fit, '<script>not executable</script>\n10.2 mm');
  assert.equal('other' in notebook, false);
});

test('notebook imports reject unknown guides, oversized notes and malformed records', () => {
  for (const value of [
    null,
    {},
    { ...EMPTY_NOTEBOOK, pins: ['unknown'] },
    { ...EMPTY_NOTEBOOK, notes: { fit: 'x'.repeat(10_001) } },
    { ...EMPTY_NOTEBOOK, notes: [] },
    { ...EMPTY_NOTEBOOK, notes: { fit: 5 } },
  ])
    assert.throws(() => parseNotebook(value));
});
