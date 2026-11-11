import type { HeightCheckSettings } from './types';

/** User-supplied absolute bounds, never inferred from pixel size or instrument resolution. */
export function heightCheckSettingsError(value: HeightCheckSettings): string | null {
  if (
    !value ||
    typeof value !== 'object' ||
    !Number.isFinite(value.allowance_mm) ||
    value.allowance_mm <= 0 ||
    value.allowance_mm > 2000 ||
    !Number.isFinite(value.measurement_bound_mm) ||
    value.measurement_bound_mm < 0 ||
    value.measurement_bound_mm > 2000
  )
    return 'Enter an allowed deviation above 0 and up to 2000 mm, and a measurement error bound from 0 to 2000 mm.';
  return null;
}

export function heightCheckDraft(allowance: string, bound: string, factor: number) {
  if (!allowance.trim() && !bound.trim()) return { value: null, error: null };
  if (!allowance.trim() || !bound.trim())
    return {
      value: null,
      error: 'Enter both decision inputs, or clear both to leave the check undecided.',
    };
  const value = {
    allowance_mm: Number(allowance) * factor,
    measurement_bound_mm: Number(bound) * factor,
  };
  const error = heightCheckSettingsError(value);
  return { value: error ? null : value, error };
}

/** Compare a deterministic source-profile height with an independently bounded measurement. */
export function assessHeight(estimate: number, measured: number, settings: HeightCheckSettings) {
  if (
    heightCheckSettingsError(settings) ||
    !Number.isFinite(estimate) ||
    !Number.isFinite(measured) ||
    estimate <= 0 ||
    measured < 0.1 ||
    measured > 2000
  )
    return null;
  const difference = estimate - measured;
  const bound = settings.measurement_bound_mm;
  const nearest = Math.max(0, Math.abs(difference) - bound);
  const farthest = Math.abs(difference) + bound;
  // Keep numerical contact with a limit undecided. This is floating-point protection,
  // not an extra physical uncertainty or an allowance for manufacturing error.
  const guard = 64 * Number.EPSILON * Math.max(1, estimate, measured, settings.allowance_mm, bound);
  const status =
    farthest < settings.allowance_mm - guard
      ? 'within'
      : nearest > settings.allowance_mm + guard
        ? 'outside'
        : 'inconclusive';
  return { status, low: difference - bound, high: difference + bound } as const;
}
