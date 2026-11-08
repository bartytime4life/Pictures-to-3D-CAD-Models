export type Point = [number, number];
export type Profile = { outer: Point[]; holes: Point[][] };
export type Detail = 'coarse' | 'standard' | 'fine';
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
  mesh: { vertices: number[]; triangles: number[] };
  downloads: { step: string; stl: string; dxf: string; project: string };
  warnings: string[];
};
export type ProjectRecipe = {
  format: 'pictures-to-cad';
  version: 1;
  name: string;
  profile: Profile;
  width_mm: number;
  thickness_mm: number;
};
