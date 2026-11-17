import assert from 'node:assert/strict';
import test from 'node:test';
import { projectPlateMesh, suggestedPlateAngle } from '../../frontend/src/plateInspection.ts';
import type { ModelPart } from '../../frontend/src/types';

const mesh = {
  vertices: [10, 20, 0, 110, 20, 0, 110, 60, 4, 10, 60, 4],
  triangles: [0, 1, 2, 0, 2, 3],
};
const close = (a: number, b: number) => assert.ok(Math.abs(a - b) < 1e-9, `${a} ≠ ${b}`);
test('inspection rotation has the correct footprint at 0, 90 and 45 degrees', () => {
  const zero = projectPlateMesh(mesh, 0);
  close(zero.width, 100);
  close(zero.depth, 40);
  const quarter = projectPlateMesh(mesh, 90);
  close(quarter.width, 40);
  close(quarter.depth, 100);
  const diagonal = projectPlateMesh(mesh, 45);
  close(diagonal.width, 140 / Math.sqrt(2));
  close(diagonal.depth, 140 / Math.sqrt(2));
});
test('translation does not change footprint, and inspection never mutates mesh data', () => {
  const before = JSON.stringify(mesh);
  const moved = {
    ...mesh,
    vertices: mesh.vertices.map(
      (value, index) => value + (index % 3 === 0 ? 1000 : index % 3 === 1 ? -200 : 0),
    ),
  };
  const original = projectPlateMesh(mesh, 31);
  const translated = projectPlateMesh(moved, 31);
  close(original.width, translated.width);
  close(original.depth, translated.depth);
  assert.equal(JSON.stringify(mesh), before);
});
test('missing mesh stays an empty finite projection and suggestion preserves precise witness', () => {
  assert.deepEqual(projectPlateMesh(undefined, 0), {
    points: [],
    width: 0,
    depth: 0,
    centerX: 0,
    centerY: 0,
  });
  assert.equal(suggestedPlateAngle(undefined), 0);
  const part = { bed_fit: { rotation_deg: 23.456789, rotated_90: false } } as ModelPart;
  assert.equal(suggestedPlateAngle(part), 23.456789);
});
