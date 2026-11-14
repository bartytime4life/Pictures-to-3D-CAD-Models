// Relief & lithophane request/response shapes and small pure helpers.

export type ReliefMode = 'relief' | 'lithophane';
export type ReliefShape = 'flat' | 'sphere';
export type ReliefMaterial = 'pla' | 'petg' | 'abs' | 'asa' | 'tpu' | 'nylon';

export type ReliefSettings = {
  name: string;
  revision: number;
  mode: ReliefMode;
  source: 'photo' | 'depth';
  width_mm: number;
  min_mm: number;
  max_mm: number;
  invert: boolean;
  gamma: number;
  denoise: 'off' | 'light' | 'strong';
  nozzle_mm: number;
  nozzle_filter: boolean;
  pitch_mm: number | null;
  frame_mm: number;
  half_value_mm: number;
  auto_levels: boolean;
  material: ReliefMaterial;
  color: string;
  shape: ReliefShape;
  sphere_diameter_mm: number;
  opening_mm: number;
  collar_mm: number;
};

export type MeshReport = {
  vertices: number;
  triangles: number;
  edges: number;
  euler_characteristic: number;
  genus: number;
  closed_and_oriented: boolean;
  surface_area_mm2: number;
  volume_mm3: number;
};

export type ReliefResult = {
  id: string;
  kind: ReliefMode;
  shape?: ReliefShape;
  revision: number;
  dimensions: { width: number; height: number; thickness: number; min_thickness: number };
  volume_mm3: number;
  mesh: { vertices: number[]; triangles: number[] };
  preview_image: string;
  downloads: Partial<Record<ReliefDownload, string>>;
  warnings: string[];
  settings: ReliefSettings;
  stats: {
    grid: {
      columns: number;
      rows: number;
      pitch_x_mm: number;
      pitch_y_mm: number;
      image_pixel_mm: number;
    };
    source: { width_px: number; height_px: number; samples: string };
    nozzle_filter: {
      enabled: boolean;
      fwhm_mm: number;
      sigma_mm: number;
      removed_rms_mm: number;
      removed_max_mm: number;
    };
    quantization_step_mm: number;
    slope_deg: { max: number; p95: number };
    mass_g: number;
    density_g_cm3: number;
    mesh: MeshReport;
    volume_cross_check_mm3: number;
    volume_check?: { label: string; value_mm3: number; rel_tol: number };
    sphere?: {
      outer_diameter_mm: number;
      inner_diameter_mm: number;
      opening_mm: number;
      height_mm: number;
      bed_contact_mm2: number;
      overhang_area_mm2: number;
      overhang_fraction: number;
      overhang_degrees: number;
      smooth_volume_mm3: number;
      polyhedral_vs_smooth: number;
    };
    auto_levels_white?: number;
    auto_levels_range?: [number, number];
    wedge_mm?: number[];
    optics?: {
      mu_per_mm: number;
      half_value_mm: number;
      contrast_ratio: number;
      dynamic_range_stops: number;
      darkest_transmission: number;
      clipped_fraction: number;
      tone_error_lstar_mean: number;
      tone_error_lstar_p95: number;
      tone_error_lstar_mean_all: number;
    };
  };
};

export type ReliefDownload = 'stl' | '3mf' | 'heightmap' | 'blender' | 'project' | 'wedge';

export type BlenderStatus = {
  name: string;
  tested_version: string;
  minimum_version: string;
  download_url: string;
  detected: boolean;
  bridge_enabled: boolean;
  launch_available: boolean;
  launch_reason: string;
};

export type CalibrationFit = {
  mu_per_mm: number;
  half_value_mm: number;
  half_value_se_mm: number | null;
  r_squared: number;
  used_points: number;
  excluded_steps: number[];
};

export const MODE_DEFAULTS: Record<ReliefMode, { min: string; max: string; frame: string }> = {
  relief: { min: '1.6', max: '4', frame: '0' },
  lithophane: { min: '0.8', max: '3', frame: '3' },
};

export const WEDGE_STEPS = 8;

/** Thickness of each printed calibration step; mirrors backend wedge_thicknesses. */
export function wedgeThicknesses(min: number, max: number, steps = WEDGE_STEPS) {
  return Array.from({ length: steps }, (_, k) => min + ((max - min) * k) / (steps - 1));
}

/** Beer-Lambert contrast a lithophane can show between its thinnest and thickest walls. */
export function lithophaneRange(min: number, max: number, halfValue: number) {
  const stops = (max - min) / halfValue;
  return { stops, ratio: 2 ** stops };
}

export function fmt(value: number | undefined | null, digits = 2) {
  if (value === undefined || value === null || !Number.isFinite(value)) return '—';
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function filenameFor(kind: ReliefDownload, name: string) {
  const base =
    name
      .trim()
      .replace(/[^\w.-]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'relief';
  return {
    stl: `${base}.stl`,
    '3mf': `${base}.3mf`,
    heightmap: `${base}-heightmap.png`,
    blender: `${base}-blender.zip`,
    project: `${base}-relief.json`,
    wedge: `${base}-calibration-wedge.stl`,
  }[kind];
}
