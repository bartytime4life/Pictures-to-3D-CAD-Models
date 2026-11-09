// Unit and cross-language tests for assets/js/cadcalc.js.
//   node --test tests/node/
// The Python half of each comparison runs `python3 -m cadkit ... --json`
// (override the interpreter with CAD_REFERENCE_PYTHON).
import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const require = createRequire(import.meta.url);
const C = require(path.join(ROOT, 'assets/js/cadcalc.js'));
const golden = require(path.join(ROOT, 'examples/calculation-results.json'));
const routes = require(path.join(ROOT, 'assets/data/routes.json'));
const PY = process.env.CAD_REFERENCE_PYTHON || 'python3';

const close = (a, b, rel = 1e-12, msg = '') => {
  const tol = rel * Math.max(1, Math.abs(a), Math.abs(b));
  assert.ok(Math.abs(a - b) <= tol, `${msg} expected ${b}, got ${a}`);
};
// stderr is captured, not inherited: some tests expect the CLI to reject input with exit code 2.
const cadkit = (...args) => JSON.parse(execFileSync(PY, ['-m', 'cadkit', ...args.map(String), '--json'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }));

test('golden values from examples/calculation-results.json', () => {
  const u = C.ratioUncertainty(640, 2, 1000, 2, 50, 0.05);
  assert.equal(C.planarScale(50, 1000), golden.scale_mm_per_pixel);
  assert.equal(u.length, golden.feature_length_mm);
  assert.equal(u.u, golden.standard_uncertainty_mm_independent_small_error_model);
  assert.equal(C.minSegments(10, 0.02), golden.minimum_circle_segments);
  assert.equal(C.chordError(10, 50), golden.actual_chord_error_mm);
  assert.equal(C.chordError(10, 49), golden.previous_segment_count_error_mm);
  const g = C.gearPair(2, 20, 40);
  assert.deepEqual([g.d1, g.d2, g.center_distance, g.speed_ratio],
    [...golden.gear_pitch_diameters_mm, golden.gear_nominal_center_distance_mm, golden.gear_output_input_speed_ratio]);
  const a = C.aspectCheck(50, 90, 400, 675);
  assert.equal(a.known_aspect, golden.calibration_check_known_aspect);
  assert.equal(a.image_aspect, golden.calibration_check_image_aspect);
  assert.equal(a.squat_percent, golden.calibration_check_squat_percent);
  assert.equal(a.scale_v, golden.calibration_check_scale_mm_per_pixel_vertical);
  assert.equal(a.stretch_percent, golden.calibration_check_vertical_stretch_percent);
  assert.equal(C.depthFactor(500, 60), golden.off_plane_depth_factor);
  assert.equal(40 * C.depthFactor(500, 60), golden.off_plane_corrected_size_mm);
  assert.deepEqual(C.depthFactorRange(350, 800, 30, 80), golden.off_plane_factor_range);
  const f = C.focalPxFrom35mm(26, 4000, 3000);
  assert.equal(f, golden.camera_focal_length_px);
  assert.equal(C.cameraDistance(f, 100, 500), golden.camera_distance_mm);
  const r = C.roundingUncertainty(3.25, 'in', 2);
  assert.equal(r.value_mm, golden.label_mm);
  assert.equal(r.half_interval_mm, golden.label_rounding_half_interval_mm);
  assert.equal(r.standard_uncertainty_mm, golden.label_rounding_standard_uncertainty_mm);
  assert.equal(C.coatingLoss(0.08), golden.coated_slot_width_loss_mm);
});

test('tessellation: n is the smallest count meeting the tolerance', () => {
  for (const [R, e] of [[10, 0.02], [2.5, 0.02], [50, 0.01], [1, 0.1], [100, 0.5]]) {
    const n = C.minSegments(R, e);
    assert.ok(C.chordError(R, n) <= e, `n=${n} meets e for R=${R}`);
    if (n > 3) assert.ok(C.chordError(R, n - 1) > e, `n-1 fails for R=${R}`);
  }
  assert.throws(() => C.minSegments(1, 1), RangeError);
  assert.throws(() => C.chordError(1, 2), RangeError);
});

test('homography recovers a known projective map and reports local scale', () => {
  const Ht = [[0.12, 0.01, -3], [0.004, 0.13, -5], [0.00002, 0.00005, 1]];
  const src = [[100, 120], [900, 140], [880, 1000], [80, 960], [500, 560], [300, 800]];
  const dst = src.map((p) => C.homography.apply(Ht, p));
  const r = C.homography.report(src, dst, [400, 400]);
  r.H.flat().forEach((v, i) => close(v, Ht.flat()[i], 1e-9, `H[${i}]`));
  assert.ok(r.rms < 1e-9);
  // (100,120), (500,560), (880,1000) lie close to one line, and with six points the fit says so.
  assert.deepEqual(r.warnings, ['Some image points are nearly collinear; the estimate is fragile.']);
  // Jacobian against central finite differences.
  const h = 1e-4;
  const J = C.homography.jacobian(Ht, [400, 400]);
  for (const [col, du, dv] of [[0, h, 0], [1, 0, h]]) {
    const a = C.homography.apply(Ht, [400 + du, 400 + dv]);
    const b = C.homography.apply(Ht, [400 - du, 400 - dv]);
    close(J[0][col], (a[0] - b[0]) / (2 * h), 1e-6, 'dx');
    close(J[1][col], (a[1] - b[1]) / (2 * h), 1e-6, 'dy');
  }
  // An affine map has the same local scale everywhere.
  const A = [[0.5, 0, 2], [0, 0.25, 1], [0, 0, 1]];
  assert.deepEqual(C.homography.localScale(A, [10, 10]), [0.5, 0.25]);
});

test('homography validation mirrors the Python rules', () => {
  const four = C.homography.report([[0, 0], [10, 0], [10, 10], [0, 10]], [[0, 0], [5, 0], [5, 5], [0, 5]]);
  assert.match(four.warnings[0], /zero by construction/);
  assert.throws(() => C.homography.fit([[0, 0], [1, 1], [2, 2], [3, 3]], [[0, 0], [1, 0], [1, 1], [0, 1]]), /collinear/);
  assert.throws(() => C.homography.fit([[0, 0], [1, 0], [2, 0], [0, 1]], [[0, 0], [1, 0], [1, 1], [0, 1]]), /three src points are collinear/);
  assert.throws(() => C.homography.fit([[0, 0], [0, 0], [1, 0], [0, 1]], [[0, 0], [1, 0], [1, 1], [0, 1]]), /duplicate/);
  assert.throws(() => C.homography.fit([[0, 0], [1, 0], [1, 1]], [[0, 0], [1, 0], [1, 1]]), /at least four/);
});

test('homography reports on large point sets without a cubic scan', () => {
  // Codex review of PR #2: the near-collinear warning needs at most six points, so a larger
  // set must not enumerate every triple (3000 points is 4.5e9 triples, many seconds).
  const Ht = [[0.05, 0.004, -12], [-0.003, 0.049, -8], [1.2e-5, -2e-5, 1]];
  let seed = 20261108;
  const rand = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
  const src = Array.from({ length: 3000 }, () => [rand() * 3000, rand() * 2000]);
  const dst = src.map((p) => C.homography.apply(Ht, p));
  const t0 = performance.now();
  const r = C.homography.report(src, dst);
  const ms = performance.now() - t0;
  assert.ok(ms < 1500, `report took ${ms.toFixed(0)} ms`);
  assert.equal(r.points, 3000);
  assert.ok(r.rms < 1e-6, `rms ${r.rms}`);
  assert.deepEqual(r.warnings, []);
});

test('input validation rejects impossible values', () => {
  assert.throws(() => C.planarScale(0, 100), RangeError);
  assert.throws(() => C.depthFactor(500, -600), /in front of the camera/);
  assert.throws(() => C.windPower(1.2, 1, 5, 0.6), /Betz/);
  assert.throws(() => C.roundingUncertainty(1, 'ft', 2), /unit/);
  assert.throws(() => C.weakestEvidence(['measured', 'guessed']), /unknown evidence/);
  assert.throws(() => C.weakestEvidence([]), RangeError);
  assert.throws(() => C.clearanceSeries(5, -6, 0.1, 3), /positive/);
});

test('evidence propagation, unit detective, coupon rounding', () => {
  assert.equal(C.weakestEvidence(['measured', 'Image derived']), 'image-derived');
  assert.equal(C.weakestEvidence(['confirmed', 'synthetic']), 'inferred');
  assert.equal(C.weakestEvidence(['measured', 'unknown', 'estimated']), 'unknown');
  for (const [observed, expect] of [[0.06, 'm'], [6, 'cm'], [2.3622, 'in'], [60, 'mm'], [1524, '1/in']]) {
    assert.equal(C.suggestUnitConversion(observed, 60)[0].unit, expect, `observed ${observed}`);
  }
  assert.deepEqual(C.clearanceSeries(5, 0.1, 0.1, 5).map((r) => r.hole_diameter), [5.1, 5.2, 5.3, 5.4, 5.5]);
  assert.equal(C.clearanceSeries(5, 0.1, 0.1, 3)[2].diametral, 0.3);
});

test('JavaScript and Python calculators agree', { timeout: 60000 }, () => {
  const s = cadkit('scale', '--known-mm', 33, '--reference-px', 150, '--feature-px', 520);
  close(C.scaledLength(520, C.planarScale(33, 150)), s.feature_length_mm);
  assert.equal(C.scaleWarnings(150, 520).length, s.warnings.length);

  const u = cadkit('uncertainty', '--p', 812.5, '--up', 1.5, '--pref', 233, '--upref', 2.5, '--lref', 25.4, '--ulref', 0.02);
  const uj = C.ratioUncertainty(812.5, 1.5, 233, 2.5, 25.4, 0.02);
  for (const k of ['length', 'u', 'relative', 'expanded_k2']) close(uj[k], u[k], 1e-12, k);
  assert.equal(uj.warnings.length, u.warnings.length);

  const ch = cadkit('chord', '--radius', 3.175, '--error', 0.005);
  assert.equal(C.minSegments(3.175, 0.005), ch.segments);
  close(C.chordError(3.175, ch.segments), ch.chord_error_mm);

  const d = cadkit('depth', '--z', 420, '--delta', -35, '--size', 18.2, '--z-range', 380, 460, '--delta-range', -40, -30);
  close(C.depthFactor(420, -35), d.depth_factor);
  C.depthFactorRange(380, 460, -40, -30).forEach((v, i) => close(v, d.factor_range[i]));

  const cam = cadkit('camera', '--f35', 24, '--width-px', 4032, '--height-px', 3024, '--length-mm', 210, '--length-px', 1430);
  const fpx = C.focalPxFrom35mm(24, 4032, 3024);
  close(fpx, cam.focal_length_px);
  close(C.cameraDistance(fpx, 210, 1430), cam.camera_distance_mm);

  const aj = C.aspectCheck(54, 85.6, 1200, 760);
  const ap = cadkit('aspect', '--known', 54, 85.6, '--pixels', 1200, 760);
  for (const k of ['known_aspect', 'image_aspect', 'squat_percent', 'scale_h', 'scale_v', 'stretch_percent']) close(aj[k], ap[k], 1e-12, k);
  assert.equal(aj.warnings.length, ap.warnings.length);
});

test('JavaScript and Python agree on labels, fits, gears, wind, units, evidence', { timeout: 60000 }, () => {
  const l = cadkit('label', '--value', 12.7, '--unit', 'mm', '--decimals', 1);
  const lj = C.roundingUncertainty(12.7, 'mm', 1);
  for (const k of ['value_mm', 'half_interval_mm', 'standard_uncertainty_mm']) close(lj[k], l[k], 1e-12, k);

  close(C.coatingLoss(0.05, 4), cadkit('coating', '--per-face', 0.05, '--faces', 4).width_loss_mm);

  const g = cadkit('gear', '--module', 1.5, '--teeth', 14, 33);
  const gj = C.gearPair(1.5, 14, 33);
  for (const k of ['d1', 'd2', 'center_distance', 'speed_ratio', 'undercut_limit_teeth']) close(gj[k], g[k], 1e-12, k);
  assert.equal(gj.warnings.length, g.warnings.length);

  const w = cadkit('wind', '--rho', 1.2, '--area', 0.5, '--v', 7.5, '--cp', 0.3);
  close(C.windPower(1.2, 0.5, 7.5, 0.3), w.power_w);

  const cp = cadkit('coupon', '--nominal', 3, '--start', 0.05, '--step', 0.05, '--count', 7);
  assert.deepEqual(C.clearanceSeries(3, 0.05, 0.05, 7), cp.rows);

  const un = cadkit('units', '--observed', 1.9685, '--expected-mm', 50, '--top', 9);
  const uj = C.suggestUnitConversion(1.9685, 50);
  assert.deepEqual(uj.map((c) => c.unit), un.candidates.map((c) => c.unit));
  uj.forEach((c, i) => close(c.relative_error, un.candidates[i].relative_error, 1e-12, c.unit));

  for (const set of [['measured', 'nominal'], ['confirmed', 'estimated'], ['image derived', 'unknown', 'measured']]) {
    assert.equal(C.weakestEvidence(set), cadkit('evidence', ...set).weakest, set.join('+'));
  }
});

test('JavaScript and Python homography fits agree', { timeout: 60000 }, () => {
  const pairs = [[[112, 96], [0, 0]], [[511, 81], [50, 0]], [[592, 802], [50, 90]], [[48, 770], [0, 90]],
    [[305.99, 88.71], [25, 0]], [[307.6, 383.69], [25, 45]], [[155.89, 677.18], [10, 80]]];
  const py = cadkit('homography', '--points', JSON.stringify(pairs), '--at', 308, 384);
  const js = C.homography.report(pairs.map((p) => p[0]), pairs.map((p) => p[1]), [308, 384]);
  js.H.flat().forEach((v, i) => close(v, py.H.flat()[i], 1e-10, `H[${i}]`));
  close(js.rms, py.rms_residual, 1e-9, 'rms');
  close(js.local_scale_u, py.local_scale_u, 1e-10, 'sx');
  close(js.local_scale_v, py.local_scale_v, 1e-10, 'sy');
  assert.deepEqual(js.warnings, py.warnings);
});

test('route finder: every input and goal gives the same answer in JavaScript and Python', { timeout: 60000 }, () => {
  const py = cadkit('route', '--all');
  const js = routes.inputs.flatMap((i) => routes.goals.map((g) => C.recommendRoute(routes, i.id, g.id)));
  assert.equal(js.length, routes.inputs.length * routes.goals.length);
  assert.deepEqual(js, py);
  for (const r of js) {
    assert.ok(r.workflows.length >= 1);
    for (const w of r.workflows) assert.ok(routes.workflows[w], `workflow ${w}`);
  }
  assert.deepEqual(C.recommendRoute(routes, 'photo-set', 'mount').workflows, ['E', 'C']);
  assert.deepEqual(C.recommendRoute(routes, 'mesh', 'decorative').workflows, ['C']);
  assert.throws(() => C.recommendRoute(routes, 'nope', 'holder'), /unknown input/);
});

test('regressions from the independent review agree with Python', { timeout: 60000 }, () => {
  // Rounding: toFixed-based round6 must equal Python's round(x, 6).
  for (const [nominal, start, step, count] of [[5, 0.439521, 0, 1], [5, 5e-7, 0, 1], [3, 0.0333333, 0.0166667, 12], [8, 0.1, 0.1, 201]]) {
    const py = cadkit('coupon', '--nominal', nominal, '--start', start, '--step', step, '--count', count);
    assert.deepEqual(C.clearanceSeries(nominal, start, step, count), py.rows, `coupon ${nominal} ${start} ${step} ${count}`);
  }
  // Jacobi stopping rule: a near-collinear set used to differ by 0.16 % in H.
  const fx = require(path.join(ROOT, 'tests/node/fixtures/near-collinear-homography.json'));
  const pairs = fx.src.map((p, i) => [p, fx.dst[i]]);
  const py = cadkit('homography', '--points', JSON.stringify(pairs));
  const js = C.homography.report(fx.src, fx.dst);
  js.H.flat().forEach((v, i) => close(v, py.H.flat()[i], 1e-9, `H[${i}]`));
  close(js.rms, py.rms_residual, 1e-9, 'rms');
  // Inputs that used to crash Python or mislead in JavaScript are rejected in both.
  const fails = (...args) => { try { cadkit(...args); return false; } catch (e) { return e.status === 2; } };
  assert.ok(fails('chord', '--radius', 10, '--error', 1e-17));
  assert.throws(() => C.minSegments(10, 1e-17), /too small/);
  assert.ok(fails('label', '--value', 1, '--decimals', 400));
  assert.throws(() => C.roundingUncertainty(1, 'in', 400), /from 0 to 12/);
  const l = cadkit('label', '--value', 1, '--unit', 'in', '--decimals', 4);
  assert.equal(C.roundingUncertainty(1, 'IN', 4).half_interval_mm, l.half_interval_mm);
  assert.equal(C.scaledLength(0, 0.05), 0);
  assert.throws(() => C.recommendRoute(routes, 'constructor', 'holder'), /unknown input/);
  assert.throws(() => C.recommendRoute(routes, 'mesh', '__proto__'), /unknown goal/);
});
