import type { ModelPart } from './types';

export function suggestedPlateAngle(part?: ModelPart): number {
  return part?.bed_fit.rotation_deg ?? (part?.bed_fit.rotated_90 ? 90 : 0);
}

/** A mesh projection for visual inspection, never an export transform or fit solver. */
export function projectPlateMesh(mesh: ModelPart['mesh'], angle: number) {
  const points: [number, number][] = [];
  const theta = (angle * Math.PI) / 180;
  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity;
  for (let index = 0; index < (mesh?.vertices.length ?? 0); index += 3) {
    const x = mesh!.vertices[index] * Math.cos(theta) - mesh!.vertices[index + 1] * Math.sin(theta);
    const y = mesh!.vertices[index] * Math.sin(theta) + mesh!.vertices[index + 1] * Math.cos(theta);
    points.push([x, y]);
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }
  return {
    points,
    width: points.length ? maxX - minX : 0,
    depth: points.length ? maxY - minY : 0,
    centerX: points.length ? (minX + maxX) / 2 : 0,
    centerY: points.length ? (minY + maxY) / 2 : 0,
  };
}
