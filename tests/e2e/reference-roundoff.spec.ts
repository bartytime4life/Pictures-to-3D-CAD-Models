import { expect, test } from '@playwright/test';
import { calibrationError, referenceWidth, scaleSensitivity } from '../../frontend/src/calibration';
import type { Point, ReferenceCalibration } from '../../frontend/src/types';

function calibration(knownLength: number, endpoint: Point): ReferenceCalibration {
  return {
    known_length_mm: knownLength,
    reference_points: [[0, 0], endpoint],
    image_size: { width: 1400, height: 1400 },
  };
}

test('reference unit roundoff at either supported width limit stays at that limit', () => {
  for (const { knownLength, outlineWidth, span, limit } of [
    { knownLength: 6.5, outlineWidth: 3, span: 195, limit: 0.1 },
    { knownLength: 420, outlineWidth: 500, span: 105, limit: 2000 },
  ]) {
    const original = calibration(knownLength, [span, 0]);
    expect(calibrationError(original)).toBeNull();
    expect((outlineWidth * knownLength) / span).toBe(limit);
    const inches = String(knownLength / 25.4);
    const converted = { ...original, known_length_mm: Number(inches) * 25.4 };
    const rawWidth = (outlineWidth * converted.known_length_mm) / span;
    // These fixed cases reproduce residual IEEE-754 error even without display rounding.
    if (limit === 0.1) expect(rawWidth).toBeLessThan(limit);
    else expect(rawWidth).toBeGreaterThan(limit);
    expect(referenceWidth(original, outlineWidth)).toBe(limit);
    expect(referenceWidth(converted, outlineWidth)).toBe(limit);
  }
});

test('boundary normalization covers varied spans and repeated full-precision unit changes', () => {
  for (const limit of [0.1, 2000]) {
    for (const outlineWidth of [0.00001, 3, 11, 100, 500, 1379, 1400]) {
      for (const endpoint of [
        [1, 0],
        [7, 0],
        [21, 0],
        [105, 0],
        [195, 0],
        [1400, 0],
        [100.3, 94.2],
        [979.25, 1380.5],
      ] satisfies Point[]) {
        const span = Math.hypot(...endpoint);
        const original = calibration((limit * span) / outlineWidth, endpoint);
        expect(calibrationError(original)).toBeNull();
        expect(referenceWidth(original, outlineWidth)).toBe(limit);
        let draft = String(original.known_length_mm);
        let previousFactor = 1;
        for (const factor of [25.4, 1, 25.4, 1, 25.4, 1]) {
          draft = String((Number(draft) * previousFactor) / factor);
          expect(
            referenceWidth({ ...original, known_length_mm: Number(draft) * factor }, outlineWidth),
          ).toBe(limit);
          previousFactor = factor;
        }
      }
    }
  }
});

test('a real out-of-range width stays outside instead of receiving a physical allowance', () => {
  for (const { limit, direction } of [
    { limit: 0.1, direction: -1 },
    { limit: 2000, direction: 1 },
  ]) {
    // 128 epsilon lies beyond the numerical guard; 1e-10 is thousands of guards away.
    for (const relativeDistance of [128 * Number.EPSILON, 1e-10]) {
      const target = limit * (1 + direction * relativeDistance);
      const reference = calibration(target, [500, 0]);
      expect(calibrationError(reference)).toBeNull();
      const width = referenceWidth(reference, 500);
      expect(width).not.toBe(limit);
      if (direction < 0) expect(width).toBeLessThan(limit);
      else expect(width).toBeGreaterThan(limit);
    }
  }
});

test('normalization preserves invalid results and leaves endpoint sensitivity as a scenario', () => {
  const reference = calibration(420, [105, 0]);
  expect(referenceWidth({ ...reference, known_length_mm: Infinity }, 500)).toBe(Infinity);
  expect(referenceWidth({ ...reference, known_length_mm: NaN }, 500)).toBeNaN();
  const converted = {
    ...reference,
    known_length_mm: Number(String(reference.known_length_mm / 25.4)) * 25.4,
  };
  const scenario = scaleSensitivity(converted, 500, 1);
  expect(scenario).not.toBeNull();
  expect(scenario!.current).toBe((500 * converted.known_length_mm) / 105);
  expect(scenario!.high).toBeGreaterThan(2000);
  expect(scenario!.low).toBeLessThan(2000);
});
