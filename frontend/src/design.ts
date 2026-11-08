import type { AssistantProposal, DesignSettings } from './types';

export const DEFAULT_DESIGN: DesignSettings = {
  scale_percent: 100,
  thickness_percent: 100,
  color: '#9ca3af',
  material: 'pla',
  detail_mode: 'original',
  nozzle_mm: 0.4,
  output_mode: 'single',
  split_columns: 2,
  split_rows: 1,
  printer_id: 'custom',
  bed_width_mm: 220,
  bed_depth_mm: 220,
  bed_height_mm: 250,
  bed_margin_mm: 5,
};

export const DESIGN_KEYS = Object.keys(DEFAULT_DESIGN) as (keyof DesignSettings)[];
export const DESIGN_LABELS: Record<keyof DesignSettings, string> = {
  scale_percent: 'XY scale',
  thickness_percent: 'Thickness scale',
  color: 'Model color',
  material: 'Material',
  detail_mode: 'Geometry detail',
  nozzle_mm: 'Nozzle diameter',
  output_mode: 'Output',
  split_columns: 'Columns',
  split_rows: 'Rows',
  printer_id: 'Printer model',
  bed_width_mm: 'Bed width',
  bed_depth_mm: 'Bed depth',
  bed_height_mm: 'Build height',
  bed_margin_mm: 'Bed margin',
};

export function formatDesignValue(
  key: keyof DesignSettings,
  value: DesignSettings[keyof DesignSettings],
) {
  if (key === 'scale_percent' || key === 'thickness_percent') return `${value}%`;
  if (key.endsWith('_mm')) return `${value} mm`;
  if (key === 'material') return String(value).toUpperCase();
  if (key === 'output_mode') return value === 'single' ? 'Single part' : 'Split into parts';
  if (key === 'printer_id' && value === 'custom') return 'Custom printer';
  if (key === 'detail_mode')
    return { original: 'Original outline', draft: 'Draft', balanced: 'Balanced', fine: 'Fine' }[
      value as DesignSettings['detail_mode']
    ];
  return String(value);
}

export function designError(
  value: DesignSettings,
  sourceSize?: { width: number; height: number; thickness: number } | null,
): string {
  const range = (key: keyof DesignSettings, min: number, max: number) =>
    typeof value[key] === 'number' &&
    Number.isFinite(value[key]) &&
    Number(value[key]) >= min &&
    Number(value[key]) <= max;
  if (!range('scale_percent', 10, 400) || !range('thickness_percent', 10, 400))
    return 'Set both scale values between 10% and 400%.';
  if (!/^#[0-9a-fA-F]{6}$/.test(value.color)) return 'Choose a valid model color.';
  if (!['pla', 'petg', 'abs', 'asa', 'tpu', 'nylon'].includes(value.material))
    return 'Choose a supported material.';
  if (!['original', 'draft', 'balanced', 'fine'].includes(value.detail_mode))
    return 'Choose a geometry detail setting.';
  if (!range('nozzle_mm', 0.1, 8)) return 'Set the nozzle diameter between 0.1 and 8 mm.';
  if (!['single', 'split'].includes(value.output_mode)) return 'Choose single or split output.';
  if (
    !range('split_columns', 1, 4) ||
    !range('split_rows', 1, 4) ||
    !Number.isInteger(value.split_columns) ||
    !Number.isInteger(value.split_rows)
  )
    return 'Use whole numbers from 1 to 4 for split columns and rows.';
  if (value.split_columns * value.split_rows > 8)
    return 'Choose a split grid with at most 8 cells.';
  if (typeof value.printer_id !== 'string' || !value.printer_id || value.printer_id.length > 150)
    return 'Choose a printer or use Custom.';
  if (
    !range('bed_width_mm', 20, 5000) ||
    !range('bed_depth_mm', 20, 5000) ||
    !range('bed_height_mm', 20, 5000)
  )
    return 'Set each printer dimension between 20 and 5000 mm.';
  if (!range('bed_margin_mm', 0, 30)) return 'Set the bed margin between 0 and 30 mm.';
  if (value.bed_margin_mm * 2 >= Math.min(value.bed_width_mm, value.bed_depth_mm))
    return 'The bed margin must leave usable width and depth.';
  if (sourceSize) {
    const w = (sourceSize.width * value.scale_percent) / 100;
    const h = (sourceSize.height * value.scale_percent) / 100;
    const t = (sourceSize.thickness * value.thickness_percent) / 100;
    if (w < 0.1 || w > 2000 || h < 0.1 || h > 2000 || t < 0.1 || t > 500)
      return 'Requested size must stay within 0.1–2000 mm width and height, and 0.1–500 mm thickness.';
  }
  return '';
}

export function parseDesign(value: unknown): DesignSettings {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('This project is missing its design and print settings.');
  const raw = value as Record<string, unknown>;
  if (Object.keys(raw).some((key) => !DESIGN_KEYS.includes(key as keyof DesignSettings)))
    throw new Error('This project contains unsupported design settings.');
  const design = { ...DEFAULT_DESIGN, ...raw } as DesignSettings;
  const error = designError(design);
  if (error) throw new Error(`Invalid project settings. ${error}`);
  return design;
}

export function designFromProposal(
  current: DesignSettings,
  proposal: AssistantProposal,
): DesignSettings {
  const updates = Object.fromEntries(
    DESIGN_KEYS.filter((key) => proposal[key] !== undefined).map((key) => [key, proposal[key]]),
  );
  return { ...current, ...updates };
}
