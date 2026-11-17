import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  analyzeImage,
  compareImages,
  regionBounds,
  FULL_IMAGE,
  SOBEL_MAXIMUM,
} from '../../frontend/src/imageAnalysis.ts';

const image = (width: number, height: number, sample: (x: number, y: number) => number[]) => ({
  width,
  height,
  data: Uint8ClampedArray.from(
    Array.from({ length: width * height }, (_, i) =>
      sample(i % width, Math.floor(i / width)),
    ).flat(),
  ),
});
const gray = (value: number) => [value, value, value, 255];

test('uniform regions retain exact histogram totals, percentiles and measured zero edges', () => {
  for (const level of [0, 128, 255]) {
    const result = analyzeImage(image(7, 6, () => gray(level)));
    assert.equal(result.mean, level);
    assert.equal(result.low, level);
    assert.equal(result.high, level);
    assert.equal(result.edgeStrength, 0);
    assert.equal(result.edgeSamples, 20);
    assert.equal(
      result.histogram.reduce((a, b) => a + b),
      42,
    );
    assert.equal(result.shadows, level === 0 ? 100 : 0);
    assert.equal(result.highlights, level === 255 ? 100 : 0);
  }
});

test('all 512 binary patches prove the reachable Sobel bound with an independent kernel oracle', () => {
  const kx = [-1, 0, 1, -2, 0, 2, -1, 0, 1],
    ky = [-1, -2, -1, 0, 0, 0, 1, 2, 1];
  let maximum = 0;
  for (let bits = 0; bits < 512; bits++) {
    const pixels = Array.from({ length: 9 }, (_, i) => ((bits >> i) & 1) * 255);
    const gx = pixels.reduce((sum, v, i) => sum + v * kx[i], 0),
      gy = pixels.reduce((sum, v, i) => sum + v * ky[i], 0);
    maximum = Math.max(maximum, gx * gx + gy * gy);
    const result = analyzeImage(image(3, 3, (x, y) => gray(pixels[y * 3 + x])));
    assert.equal(result.edgeSamples, 1);
    assert.ok(Math.abs(result.edgeStrength! - (Math.hypot(gx, gy) / SOBEL_MAXIMUM) * 100) < 1e-12);
    assert.ok(result.edgeStrength! >= 0 && result.edgeStrength! <= 100);
  }
  assert.equal(maximum, 20 * 255 * 255);
});

test('one- and two-pixel regions report missing edge support instead of a false zero', () => {
  for (const width of [1, 2, 7])
    for (const height of [1, 2, 8]) {
      if (width >= 3 && height >= 3) continue;
      const result = analyzeImage(image(width, height, () => gray(128)));
      assert.equal(result.edgeStrength, null);
      assert.equal(result.edgeSamples, 0);
      assert.equal(result.mean, 128);
    }
});

test('region metrics never borrow neighbouring pixels outside the crop', () => {
  const crop = image(4, 5, (x, y) => gray((x * 41 + y * 63) % 256));
  for (const outside of [0, 255]) {
    const source = image(8, 8, (x, y) =>
      x >= 2 && x < 6 && y >= 1 && y < 6
        ? gray(((x - 2) * 41 + (y - 1) * 63) % 256)
        : gray(outside),
    );
    const actual = analyzeImage(source, { x: 0.25, y: 0.125, width: 0.5, height: 0.625 });
    const expected = analyzeImage(crop);
    assert.deepEqual({ ...actual, bounds: expected.bounds }, expected);
  }
});

test('white alpha backing matches the visible sample and comparison', () => {
  const transparent = image(4, 4, () => [0, 0, 0, 0]),
    white = image(4, 4, () => gray(255));
  assert.deepEqual(analyzeImage(transparent), analyzeImage(white));
  assert.equal(compareImages(transparent, white)?.changedPercent, 0);
  assert.equal(analyzeImage(image(4, 4, () => [0, 0, 0, 128])).mean, 127);
});

test('comparison requires identical sampled dimensions and uses the selected region', () => {
  const a = image(8, 8, () => gray(0)),
    b = image(8, 8, (x) => gray(x < 4 ? 23 : 24));
  assert.equal(compareImages(a, b)?.changedPercent, 50);
  assert.equal(compareImages(a, b, { x: 0, y: 0, width: 0.5, height: 1 })?.changedPercent, 0);
  assert.equal(compareImages(a, a, FULL_IMAGE, 0)?.changedPercent, 0);
  assert.equal(
    compareImages(
      a,
      image(4, 4, () => gray(0)),
    ),
    null,
  );
});

test('fractional bounds round outward, and invalid data or regions fail explicitly', () => {
  assert.deepEqual(regionBounds({ x: 0.11, y: 0.21, width: 0.31, height: 0.41 }, 10, 10), {
    left: 1,
    top: 2,
    right: 5,
    bottom: 7,
  });
  for (const region of [
    { ...FULL_IMAGE, x: NaN },
    { ...FULL_IMAGE, width: 0 },
    { ...FULL_IMAGE, x: 0.5 },
  ])
    assert.throws(() => regionBounds(region, 10, 10));
  assert.throws(() => analyzeImage({ width: 2, height: 2, data: new Uint8ClampedArray(3) }));
  assert.throws(() => regionBounds(FULL_IMAGE, 721, 10));
});
