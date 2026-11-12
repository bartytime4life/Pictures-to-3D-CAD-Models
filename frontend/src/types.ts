export type Point = [number, number];
export type ReferenceCalibration = {
  known_length_mm: number;
  reference_points: [Point, Point];
  image_size: { width: number; height: number };
};
export type HeightCheckSettings = {
  allowance_mm: number;
  measurement_bound_mm: number;
};
export type Segment =
  | { kind: 'line'; start: Point; end: Point }
  | { kind: 'arc'; start: Point; mid: Point; end: Point }
  | { kind: 'circle'; center: Point; radius: number };
export type SheetKind = 'a4' | 'letter' | 'custom';
export type SheetChoice = { kind: 'none' | SheetKind; width: string; height: string };
/** How a reference-sheet trace was scaled and corrected; evidence, not geometry. */
export type TraceReference = {
  kind: SheetKind;
  sheet_mm: [number, number];
  mm_per_px: number;
  lens_k1: number;
  edge_blur_mm: number;
  thickness_mm?: number;
  camera_height_mm?: number;
  focal_source?: 'sheet' | 'exif' | 'holes' | 'assumed';
  notes: string[];
};
export type Profile = {
  outer: Point[];
  holes: Point[][];
  primitives?: { outer: Segment[]; holes: Segment[][] };
  reference?: TraceReference;
};
export type Detail = 'coarse' | 'standard' | 'fine';
export type SlicerId = 'bambu' | 'prusa';
export type ExportKind =
  'step' | 'stl' | 'dxf' | 'svg' | 'pdf' | 'scad' | 'parts' | '3mf' | SlicerId;
export type SlicerProgram = {
  id: SlicerId;
  name: string;
  target_version: string;
  release_url: string;
  source_url: string;
  detected: boolean;
  launch_available: boolean;
  launch_reason: string;
  version_status: 'not_checked';
  bridge_enabled: boolean;
};
export type SlicerDiscovery = {
  programs: SlicerProgram[];
  local_bridge_enabled: boolean;
};
export type SlicerLaunch = {
  status: 'launch_requested';
  program_id: SlicerId;
  name: string;
  detail: string;
  handoff_id: string;
};
export type Material = 'pla' | 'petg' | 'abs' | 'asa' | 'tpu' | 'nylon';
export type DesignSettings = {
  scale_percent: number;
  thickness_percent: number;
  color: string;
  material: Material;
  detail_mode: 'original' | 'draft' | 'balanced' | 'fine';
  nozzle_mm: number;
  output_mode: 'single' | 'split';
  split_columns: number;
  split_rows: number;
  printer_id: string;
  bed_width_mm: number;
  bed_depth_mm: number;
  bed_height_mm: number;
  bed_margin_mm: number;
};
export type BedFit = {
  status: 'fits' | 'too_large' | 'unknown';
  rotated_90?: boolean;
  basis?: 'outline' | 'bounding_box' | 'curve_envelope';
  enclosure_directions?: number;
  rotation_deg?: number;
  footprint_mm?: { width: number; depth: number };
  reason: string;
};
export type ModelPart = {
  id: string;
  name: string;
  dimensions: { width: number; height: number; thickness: number };
  volume_mm3: number;
  bed_fit: BedFit;
  mesh?: { vertices: number[]; triangles: number[] };
  assembly_offset_mm?: [number, number, number];
};
export type SplitPlan = {
  grids_considered: number;
  grids_failed: number;
  reason: string;
} & (
  | { status: 'no_fit' }
  | {
      status: 'suggested';
      columns: number;
      rows: number;
      piece_count: number;
      pieces: { dimensions: ModelPart['dimensions']; area_mm2: number; bed_fit: BedFit }[];
    }
);
export type AssistantProposal = {
  threshold?: number;
  inverted?: boolean;
  detail?: Detail;
} & Partial<DesignSettings>;
export type AssistantContext = {
  threshold: number;
  inverted: boolean;
  detail: Detail;
  width_mm: number | null;
  thickness_mm: number | null;
  hole_count: number | null;
  has_image: boolean;
  has_model: boolean;
  warnings: string[];
  design: DesignSettings;
  geometry?: {
    width_mm: number;
    height_mm: number;
    thickness_mm: number;
    parts: { width_mm: number; height_mm: number; thickness_mm: number }[];
  };
};
export type AssistantStatus = {
  running: boolean;
  models: {
    name: string;
    size_bytes: number;
    parameter_size: string;
    quantization: string;
  }[];
  recommended_model: string | null;
  detail: string;
};
export type AssistantReply = {
  model: string;
  answer: string;
  proposal: AssistantProposal | null;
  warnings: string[];
  elapsed_seconds: number;
};
export type TraceResult = {
  image: { width: number; height: number; data_url: string };
  profile: Profile;
  bounds: { x: number; y: number; width: number; height: number };
  threshold: number;
  warnings: string[];
};
export type ModelResult = {
  id: string;
  revision: string;
  dimensions: { width: number; height: number; thickness: number };
  volume_mm3: number;
  hole_count: number;
  geometry?: { kind: 'fitted'; lines: number; arcs: number; circles: number } | { kind: 'polygon' };
  design?: DesignSettings;
  parts?: ModelPart[];
  print_fit?: BedFit;
  split_plan?: SplitPlan;
  mesh: { vertices: number[]; triangles: number[] };
  downloads: {
    step: string;
    stl: string;
    dxf: string;
    svg?: string;
    pdf?: string;
    scad: string;
    project: string;
    parts?: string;
    '3mf'?: string;
    bambu?: string;
    prusa?: string;
  };
  warnings: string[];
};
export type ProjectRecipe = {
  format: 'pictures-to-cad';
  version: 1 | 2 | 3;
  name: string;
  profile: Profile;
  width_mm: number;
  thickness_mm: number;
  design?: DesignSettings;
  reference_calibration?: ReferenceCalibration;
  measured_height_mm?: number;
  height_check?: HeightCheckSettings;
};
