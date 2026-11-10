import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
const require = createRequire(import.meta.url);
const C = require('../../assets/js/cad-models.js');
const schema = JSON.parse(fs.readFileSync(new URL('../../assets/data/openscad-models.json', import.meta.url), 'utf8'));
const templates = Object.fromEntries(Object.entries(schema.models).map(([id, model]) => [id, fs.readFileSync(new URL('../../' + model.template, import.meta.url), 'utf8')]));
const plate = () => C.defaults(schema, 'plate');
const coupon = () => C.defaults(schema, 'coupon');

test('schema covers the existing numeric register contract with inferred defaults', () => {
  assert.deepEqual(schema.csv_columns, ['parameter_id', 'value', 'unit', 'evidence_class', 'source_or_rationale', 'decided_on', 'supersedes', 'used_by', 'notes']);
  for (const [id, model] of Object.entries(schema.models)) {
    assert.equal(C.validate(schema, id, C.defaults(schema, id)).length, 0);
    for (const p of model.parameters) {
      assert.equal(p.evidence_class, 'inferred');
      assert.ok(p.source_or_rationale);
      assert.equal(typeof p.default, 'number');
      assert.ok(['mm', '1'].includes(p.unit));
    }
  }
  assert.deepEqual(schema.models.coupon.fixed, { compensate_polygon: true, label_mode: 'none', index_notch: true });
});

test('plate drawing geometry recovers entered dimensions and independent wall distances', () => {
  const values = { ...plate(), plate_length: 80, plate_width: 40, hole_spacing: 50 };
  const g = C.evaluate(schema, 'plate', values);
  assert.deepEqual([g.length, g.width, g.thickness], [80, 40, 4]);
  assert.deepEqual(g.holes.map((h) => h.x), [15, 65]);
  assert.equal(g.end_wall, 12.5);
  assert.equal(g.side_wall, 17.5);
  assert.equal(g.hole_wall, 45);
  assert.ok(C.validate(schema, 'plate', { ...plate(), hole_spacing: 59 }).some((i) => /End walls/.test(i.message)));
  assert.ok(C.validate(schema, 'plate', { ...plate(), plate_width: 7 }).some((i) => /Side walls/.test(i.message)));
  assert.ok(C.validate(schema, 'plate', { ...plate(), hole_spacing: 6 }).some((i) => /between the holes/.test(i.message)));
});

test('coupon uses compensated polygon radii, diametral clearances and the corner-notch rule', () => {
  const g = C.evaluate(schema, 'coupon', coupon());
  assert.deepEqual(g.holes.map((h) => Number(h.diameter.toFixed(3))), [5.1, 5.2, 5.3, 5.4, 5.5]);
  assert.ok(g.holes.every((h) => h.polygon_radius > h.diameter / 2));
  assert.ok(Math.abs(g.holes[0].polygon_radius * Math.cos(Math.PI / g.holes[0].segments) - 2.55) < 1e-12);
  assert.ok(g.notch_wall >= 2);
  assert.ok(C.validate(schema, 'coupon', { ...coupon(), end_wall: 1 }).some((i) => /End wall/.test(i.message)));
  assert.ok(C.validate(schema, 'coupon', { ...coupon(), notch_size: 30 }).some((i) => /index notch/.test(i.message)));
});

test('invalid, blank, non-finite and impractical values block export rather than coercing', () => {
  for (const value of [NaN, Infinity, -1, 0, '60', null, undefined]) assert.ok(C.validate(schema, 'plate', { ...plate(), plate_length: value }).length);
  assert.ok(C.validate(schema, 'coupon', { ...coupon(), clearance_count: 2.5 }).length);
  assert.ok(C.validate(schema, 'coupon', { ...coupon(), clearance_count: 101 }).length);
  assert.ok(C.validate(schema, 'coupon', { ...coupon(), clearance_step: -0.1 }).length);
  assert.ok(C.validate(schema, 'plate', { ...plate(), chord_error: 3 }).length);
  assert.ok(C.validate(schema, 'plate', { ...plate(), chord_error: 1e-12 }).some((i) => /720/.test(i.message)));
  assert.throws(() => C.parameterCSV(schema, 'plate', { ...plate(), plate_length: 0 }), /Length/);
  assert.throws(() => C.scadSource(schema, 'plate', { ...plate(), plate_length: 0 }, templates), /Length/);
  assert.throws(() => C.schematicSVG(schema, 'plate', { ...plate(), plate_length: 0 }), /Length/);
});

test('exported CSV is actually consumed by cadkit.params with commas, quotes and multiline rationale intact', () => {
  const source = 'Calipers, datum "A"\nIndependently recorded';
  const csv = C.parameterCSV(schema, 'plate', { ...plate(), plate_length: 75 }, { plate_length: { evidence_class: 'measured', source_or_rationale: source } }, '2026-11-09');
  const script = 'import sys,csv,io,json; from cadkit.params import COLUMNS; r=list(csv.DictReader(io.StringIO(sys.stdin.read()))); assert tuple(r[0])==COLUMNS; print(json.dumps(r))';
  const result = spawnSync('python3', ['-c', script], { cwd: new URL('../..', import.meta.url), input: csv, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const rows = JSON.parse(result.stdout);
  assert.equal(rows.length, 7);
  assert.equal(rows[0].value, '75');
  assert.equal(rows[0].unit, 'mm');
  assert.equal(rows[0].evidence_class, 'measured');
  assert.equal(rows[0].source_or_rationale, source);
  assert.equal(rows[0].decided_on, '2026-11-09');
  assert.equal(rows[1].evidence_class, 'inferred');
});

test('SCAD export replaces selected defaults once and leaves geometry and safe Customizer controls', () => {
  const source = C.scadSource(schema, 'plate', { ...plate(), plate_length: 75.5 }, templates, { plate_length: { evidence_class: 'inferred', source_or_rationale: 'value\nassert(false);' } });
  assert.match(source, /plate_length = 75\.5;/);
  assert.equal((source.match(/^plate_length\s*=/gm) || []).length, 1);
  assert.match(source, /\/\* \[Parameters\] \*\//);
  assert.match(source, /\/\* \[Hidden\] \*\//);
  assert.match(source, /difference\(\)/);
  assert.match(source, /wall between holes below minimum/);
  assert.doesNotMatch(source, /^assert\(false\);/m);
  const couponSource = C.scadSource(schema, 'coupon', coupon(), templates);
  assert.equal((couponSource.match(/^compensate_polygon\s*=/gm) || []).length, 1);
  assert.match(couponSource, /^compensate_polygon = true;/m);
  assert.match(couponSource, /^label_mode = "none";/m);
  assert.match(couponSource, /module body\(\)/);
});

test('parameter export retains input precision, requires rationale and neutralizes spreadsheet formulas', () => {
  const v = { ...plate(), plate_length: 60.12345678901234 };
  assert.match(C.parameterCSV(schema, 'plate', v), /60\.12345678901234/);
  assert.match(C.scadSource(schema, 'plate', v, templates), /plate_length = 60\.12345678901234;/);
  assert.throws(() => C.parameterCSV(schema, 'plate', plate(), { plate_length: { source_or_rationale: '  ' } }), /record a source/);
  assert.match(C.parameterCSV(schema, 'plate', plate(), { plate_length: { source_or_rationale: '=HYPERLINK("example")' } }), /'\=HYPERLINK/);
});

test('SVG export carries explicit dimensional and evidence boundaries in accessible text', () => {
  const svg = C.schematicSVG(schema, 'plate', plate());
  assert.match(svg, /^<svg xmlns=/);
  assert.match(svg, /60 by 30 mm/);
  assert.match(svg, /not a CAD render/);
  assert.match(svg, /Thickness 4 mm/);
  assert.equal((svg.match(/<circle /g) || []).length, 2);
});
