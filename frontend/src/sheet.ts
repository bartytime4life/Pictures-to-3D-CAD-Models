import type { Profile, Segment, SheetChoice, TraceReference } from './types';

export const NO_SHEET: SheetChoice = { kind: 'none', width: '', height: '' };

export function sheetLabel(kind: TraceReference['kind'] | 'none'): string {
  return kind === 'a4'
    ? 'A4 sheet'
    : kind === 'letter'
      ? 'US Letter sheet'
      : kind === 'custom'
        ? 'custom sheet'
        : 'no reference';
}

/** A custom sheet needs both measured sides, each 10–2000 mm. */
export function sheetChoiceError(choice: SheetChoice): string | null {
  if (choice.kind !== 'custom') return null;
  const sides = [choice.width, choice.height].map(Number);
  return sides.every((v) => Number.isFinite(v) && v >= 10 && v <= 2000)
    ? null
    : 'Enter the custom sheet’s measured width and height (10–2000 mm each).';
}

/** Trace form fields for the chosen sheet. Thickness is sent only with a sheet. */
export function appendSheetFields(
  body: FormData,
  choice: SheetChoice,
  thicknessMm: number | null,
  snap: boolean,
  fallback: boolean,
) {
  body.append('reference', choice.kind);
  if (choice.kind === 'none') return;
  if (choice.kind === 'custom') {
    body.append('sheet_width_mm', String(Number(choice.width)));
    body.append('sheet_height_mm', String(Number(choice.height)));
  }
  if (thicknessMm !== null && Number.isFinite(thicknessMm) && thicknessMm > 0)
    body.append('thickness_mm', String(thicknessMm));
  body.append('snap', String(snap));
  body.append('fallback', String(fallback));
}

/** The outside width implied by the sheet scale, for a profile traced on a sheet. */
export function sheetWidthMm(profile: Profile): number | null {
  if (!profile.reference) return null;
  const xs = profile.outer.map((p) => p[0]);
  return (Math.max(...xs) - Math.min(...xs)) * profile.reference.mm_per_px;
}

export function fitCounts(profile: Profile) {
  const counts = { line: 0, arc: 0, circle: 0 };
  if (!profile.primitives) return null;
  const rings: Segment[][] = [profile.primitives.outer, ...profile.primitives.holes];
  for (const ring of rings) for (const segment of ring) counts[segment.kind]++;
  return counts;
}

/** Light structural check of imported fitted geometry; the service validates it fully. */
export function primitivesShapeError(profile: Profile): string | null {
  const primitives = profile.primitives as unknown;
  if (primitives === undefined) return null;
  const finite = (v: unknown) => typeof v === 'number' && Number.isFinite(v);
  const point = (p: unknown) => Array.isArray(p) && p.length === 2 && p.every(finite);
  const segment = (s: unknown) => {
    const value = s as Record<string, unknown> | null;
    if (!value || typeof value !== 'object') return false;
    if (value.kind === 'line') return point(value.start) && point(value.end);
    if (value.kind === 'arc') return point(value.start) && point(value.mid) && point(value.end);
    if (value.kind === 'circle') return point(value.center) && finite(value.radius);
    return false;
  };
  const ring = (r: unknown) => Array.isArray(r) && r.length >= 1 && r.every(segment);
  const value = primitives as { outer?: unknown; holes?: unknown };
  if (
    !value ||
    typeof value !== 'object' ||
    !ring(value.outer) ||
    !Array.isArray(value.holes) ||
    value.holes.length !== profile.holes.length ||
    !value.holes.every(ring)
  )
    return 'This project contains invalid fitted geometry.';
  return null;
}
