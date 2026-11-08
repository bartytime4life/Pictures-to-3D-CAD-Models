export type Point = [number, number];
export type Profile = { outer: Point[]; holes: Point[][] };
export type Detail = 'coarse' | 'standard' | 'fine';
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
  design?: DesignSettings;
  parts?: ModelPart[];
  print_fit?: BedFit;
  mesh: { vertices: number[]; triangles: number[] };
  downloads: { step: string; stl: string; dxf: string; project: string; parts?: string };
  warnings: string[];
};
export type ProjectRecipe = {
  format: 'pictures-to-cad';
  version: 1 | 2;
  name: string;
  profile: Profile;
  width_mm: number;
  thickness_mm: number;
  design?: DesignSettings;
};
