import type { Point, ReferenceCalibration } from './types';

/** Uniform scale only: endpoints and outline share the orientation-adjusted working image. */
export function referenceWidth(calibration: ReferenceCalibration, outlineWidth: number): number {
  const [a, b] = calibration.reference_points;
  return (outlineWidth * calibration.known_length_mm) / Math.hypot(b[0] - a[0], b[1] - a[1]);
}

export function calibrationError(value: ReferenceCalibration): string | null {
  const frame = value?.image_size;
  if (
    !frame ||
    ![frame.width, frame.height].every((n) => Number.isInteger(n) && n > 0 && n <= 1400)
  )
    return 'The reference needs a valid working-image size.';
  if (!Number.isFinite(value.known_length_mm) || value.known_length_mm <= 0)
    return 'Enter a positive, finite known feature length.';
  const points = value.reference_points;
  if (
    !Array.isArray(points) ||
    points.length !== 2 ||
    !points.every(
      (p): p is Point =>
        Array.isArray(p) &&
        p.length === 2 &&
        p.every((n) => typeof n === 'number' && Number.isFinite(n)) &&
        p[0] >= 0 &&
        p[0] <= frame.width &&
        p[1] >= 0 &&
        p[1] <= frame.height,
    )
  )
    return 'Place both endpoints inside the working image.';
  const [a, b] = points;
  if (Math.hypot(b[0] - a[0], b[1] - a[1]) < 1)
    return 'Separate the endpoints by at least one working-image pixel.';
  return null;
}

export function measuredHeightError(value: string, factor: number): string | null {
  if (!value.trim()) return null;
  const mm = Number(value) * factor;
  return Number.isFinite(mm) && mm >= 0.1 && mm <= 2000
    ? null
    : 'Enter a measured height from 0.1 to 2000 mm, or leave it blank.';
}
