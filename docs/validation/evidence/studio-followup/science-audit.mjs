// Independent arithmetic spot checks; this is not physical or slicer validation.
// Run: node --experimental-strip-types docs/validation/evidence/studio-followup/science-audit.mjs
import assert from 'node:assert/strict';
import {
  scaleScenario,
  layerScenario,
  fitScenario,
  parseLabScenario,
  LAB_DEFAULTS,
  layerBands,
} from '../../../../frontend/src/science.ts';
const near = (a, b) =>
  assert.ok(Math.abs(a - b) <= Math.max(1e-12, Math.abs(b) * 1e-12), `${a} != ${b}`);
const scales = [
  [
    { knownMm: 25, referencePx: 100, outlinePx: 400, endpointShiftPx: 1 },
    [0.25, 100, 5000 / 51, 5000 / 49],
  ],
  [
    { knownMm: 0.001, referencePx: 1000000, outlinePx: 1, endpointShiftPx: 0 },
    [1e-9, 1e-9, 1e-9, 1e-9],
  ],
  [
    { knownMm: 2000, referencePx: 2001, outlinePx: 1000000, endpointShiftPx: 1000 },
    [2000 / 2001, 2000000000 / 2001, 2000000000 / 4001, 2000000000],
  ],
];
for (const [input, expected] of scales) {
  const actual = scaleScenario(input);
  Object.values(actual).forEach((value, index) => near(value, expected[index]));
}
const layerExamples = [
  [0.9, 0.2, 0.1, 8, 0.9],
  [0.90001, 0.2, 0.1, 9, 1],
  [0.1, 0.2, 0.2, 1, 0.2],
  [2000, 0.01, 0.01, 200000, 2000],
  [2000, 2, 2, 1000, 2000],
  [0.01, 2, 0.01, 1, 2],
];
for (const [heightMm, firstLayerMm, layerMm, count, stack] of layerExamples) {
  const actual = layerScenario({ heightMm, firstLayerMm, layerMm, nozzleMm: 0.4 });
  assert.equal(actual.count, count);
  near(actual.stackMm, stack);
}
let state = 1711;
const rand = (max) => {
  state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
  return (state % max) + 1;
};
for (let trial = 0; trial < 10000; trial++) {
  // Independent integer arithmetic in hundredths of a millimeter, with exact ceiling division.
  const height = BigInt(rand(200000)),
    first = BigInt(rand(200)),
    regular = BigInt(rand(200));
  const positive = height > first ? height - first : 0n;
  const expectedCount = 1n + (positive + regular - 1n) / regular;
  const actual = layerScenario({
    heightMm: Number(height) / 100,
    firstLayerMm: Number(first) / 100,
    layerMm: Number(regular) / 100,
    nozzleMm: 0.4,
  });
  assert.equal(actual.count, Number(expectedCount));
  near(actual.stackMm, Number(first + (expectedCount - 1n) * regular) / 100);
}
const fits = [
  [
    { cadHoleMm: 10, measuredHoleMm: 9.75, shaftMm: 10, clearanceMm: 0.2 },
    [-0.25, 10.2, 10.45, 0.1],
  ],
  [{ cadHoleMm: 20, measuredHoleMm: 20.4, shaftMm: 19, clearanceMm: 0.6 }, [0.4, 19.6, 19.2, 0.3]],
  [{ cadHoleMm: 10, measuredHoleMm: 9.8, shaftMm: 10, clearanceMm: -0.2 }, [-0.2, 9.8, 10, -0.1]],
];
for (const [input, expected] of fits) {
  Object.values(fitScenario(input)).forEach((value, index) => near(value, expected[index]));
}
for (const count of [1, 2, 20, 26, 200000])
  for (const band of layerBands(count)) {
    assert.ok(band.y >= 0 && band.height > 0 && band.y + band.height <= 185);
  }
for (const input of [
  null,
  {},
  { ...LAB_DEFAULTS, scale: { ...LAB_DEFAULTS.scale, knownMm: Infinity } },
  { ...LAB_DEFAULTS, layers: { ...LAB_DEFAULTS.layers, firstLayerMm: 0 } },
  { ...LAB_DEFAULTS, fit: { ...LAB_DEFAULTS.fit, shaftMm: 0.1, clearanceMm: -0.2 } },
])
  assert.throws(() => parseLabScenario(input));
assert.deepEqual(parseLabScenario(JSON.parse(JSON.stringify(LAB_DEFAULTS))), LAB_DEFAULTS);
console.log(
  JSON.stringify({
    scaleCases: scales.length,
    layerExamples: layerExamples.length,
    exactLayerGridCases: 10000,
    fitCases: fits.length,
    diagramCounts: [1, 2, 20, 26, 200000],
    result: 'all passed',
  }),
);
