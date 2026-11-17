import { designError } from './design.ts';
import type { DesignSettings } from './types';

export type SourceSize = { width: number; height: number; thickness: number };
export type QuickEditDimension = 'width' | 'thickness';

export function formatTargetSize(value: number): string {
  return Number.isFinite(value) ? String(Number(value.toFixed(4))) : '';
}

/** Convert a committed target dimension to a scale, preserving the source measurement. */
export function targetSizeChange(
  design: DesignSettings,
  source: SourceSize | null,
  dimension: QuickEditDimension,
  draft: string,
): { design: DesignSettings; error: '' } | { design: null; error: string } {
  if (!source || Object.values(source).some((value) => !Number.isFinite(value) || value <= 0))
    return { design: null, error: 'Set your reference width and thickness first.' };
  const target = Number(draft);
  if (!draft.trim() || !Number.isFinite(target) || target <= 0)
    return { design: null, error: `Enter a positive target ${dimension} in millimeters.` };
  const key = dimension === 'width' ? 'scale_percent' : 'thickness_percent';
  const next = { ...design, [key]: (target / source[dimension]) * 100 };
  const error = designError(next, source);
  return error ? { design: null, error } : { design: next, error: '' };
}
