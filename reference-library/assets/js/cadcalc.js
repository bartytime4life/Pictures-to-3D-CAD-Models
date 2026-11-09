/* cadcalc.js - calculators for the Pictures-to-printable-CAD reference library.
 *
 * One file serves two places: the build inlines it into index.html (so the Toolkit
 * tab works from file:// with no network), and the Node tests load it to check every
 * result against examples/calculation-results.json and against the Python toolkit
 * (python3 -m cadkit). Function names mirror cadkit/calc.py and cadkit/homography.py.
 *
 * Everything here is arithmetic under stated assumptions (pinhole camera, planar
 * reference, small independent errors). It is teaching and planning support, not
 * a measurement or a qualification of any printer or part.
 */
(function (root) {
  'use strict';

  const FULL_FRAME_DIAGONAL_MM = Math.hypot(36, 24); // 43.27 mm, the 35 mm-equivalent definition
  const MM_PER = { mm: 1, cm: 10, m: 1000, in: 25.4, ft: 304.8 };
  const EVIDENCE_ORDER = ['measured', 'image-derived', 'inferred', 'unknown'];
  // Same aliases as cadkit/calc.py: register labels mapped onto the four handbook classes.
  const EVIDENCE_ALIASES = {
    confirmed: 'measured', estimated: 'image-derived', image_derived: 'image-derived',
    nominal: 'inferred', proposed: 'inferred', synthetic: 'inferred',
  };
  const ROUNDING_UNITS = ['in', 'mm', 'cm'];
  const MAX_DECIMALS = 12; // same limit as cadkit.calc.MAX_DECIMALS
  // Python's round(x, 6) rounds the exact binary value to 6 decimals, with exact ties to even.
  // toFixed also rounds the exact value but takes ties away from zero. A double is an exact tie
  // (x × 10⁶ = k + 0.5) only when x × 128 is an odd integer, as for 0.0078125, so those values
  // take the even neighbour instead.
  function round6(x) {
    let r = Number(x.toFixed(6));
    const t = x * 128; // exact: scaling by a power of two
    if (Number.isInteger(t) && t % 2 !== 0) {
      const k = (BigInt(Math.abs(t)) * 15625n - 1n) / 2n; // |x| × 10⁶ = k + 0.5
      const even = k % 2n === 0n ? k : k + 1n;
      r = Math.sign(x) * Number(`${even / 1000000n}.${String(even % 1000000n).padStart(6, '0')}`);
    }
    return Object.is(r, -0) ? 0 : r;
  }
  const BETZ_LIMIT = 16 / 27;
  const LIMITS = { referencePx: 200, extrapolation: 3, depthRatio: 0.2, segments: 720, aspectPercent: 1 };

  function fail(message) { throw new RangeError(message); }
  function positive(name, v) {
    if (!Number.isFinite(v) || v <= 0) fail(`${name} must be a positive number`);
    return v;
  }
  function nonNegative(name, v) {
    if (!Number.isFinite(v) || v < 0) fail(`${name} must be zero or positive`);
    return v;
  }
  function finite(name, v) {
    if (!Number.isFinite(v)) fail(`${name} must be a number`);
    return v;
  }
  function finiteResult(name, v) { // same rule and wording as cadkit.calc._finite_result
    if (!Number.isFinite(v)) fail(`${name} is too large to represent; check the inputs`);
    return v;
  }

  // ---- scale and uncertainty (handbook section 5) ----------------------------
  function planarScale(knownLengthMm, referencePx) {
    return positive('known length', knownLengthMm) / positive('reference length in pixels', referencePx);
  }
  function scaledLength(featurePx, scale) {
    return nonNegative('feature length in pixels', featurePx) * positive('scale', scale);
  }
  function ratioUncertainty(p, up, pref, upref, lref, ulref) {
    positive('p', p); positive('pref', pref); positive('Lref', lref);
    nonNegative('u(p)', up); nonNegative('u(pref)', upref); nonNegative('u(Lref)', ulref);
    const length = p * lref / pref;
    const relative = Math.sqrt((up / p) ** 2 + (ulref / lref) ** 2 + (upref / pref) ** 2); // same order as Python
    const u = length * relative;
    for (const [name, value] of [['length', length], ['relative uncertainty', relative], ['u', u], ['2u', 2 * u]]) finiteResult(name, value);
    return { length, u, relative, expanded_k2: 2 * u, warnings: scaleWarnings(pref, p) };
  }
  function scaleWarnings(referencePx, featurePx) {
    const warnings = [];
    if (referencePx < LIMITS.referencePx) warnings.push(`The reference spans ${referencePx} px (under ${LIMITS.referencePx} px), so endpoint picking dominates the scale.`);
    if (featurePx !== undefined && featurePx > LIMITS.extrapolation * referencePx) warnings.push(`The feature is ${(featurePx / referencePx).toFixed(1)}x the reference length: this extrapolates beyond the controlled region.`);
    return warnings;
  }

  // ---- tessellation (section 12) --------------------------------------------
  function chordError(radius, n) {
    positive('radius', radius);
    if (!Number.isInteger(n) || n < 3) fail('n must be an integer of at least 3');
    return radius * (1 - Math.cos(Math.PI / n));
  }
  function minSegments(radius, error) {
    positive('radius', radius); positive('allowed error', error);
    if (error >= radius) fail('allowed error must be smaller than the radius');
    const halfAngle = Math.acos(1 - error / radius);
    if (halfAngle === 0) fail('error is too small relative to the radius to give a finite segment count');
    return Math.max(3, Math.ceil(Math.PI / halfAngle));
  }

  // ---- off-plane depth and camera distance (section 5) ------------------------
  function depthFactor(z, delta) {
    positive('Z', z); finite('delta', delta);
    if (z + delta <= 0) fail('Z + delta must be positive (the feature must be in front of the camera)');
    return (z + delta) / z;
  }
  function depthFactorRange(zMin, zMax, dMin, dMax) {
    if (zMin > zMax) fail('Z minimum must not exceed Z maximum');
    if (dMin > dMax) fail('delta minimum must not exceed delta maximum');
    const corners = [[zMin, dMin], [zMin, dMax], [zMax, dMin], [zMax, dMax]].map(([z, d]) => depthFactor(z, d));
    return [Math.min(...corners), Math.max(...corners)];
  }
  function focalPxFrom35mm(f35, widthPx, heightPx) {
    return positive('35 mm-equivalent focal length', f35) * Math.hypot(positive('width', widthPx), positive('height', heightPx)) / FULL_FRAME_DIAGONAL_MM;
  }
  function cameraDistance(fPx, lengthMm, lengthPx) {
    return positive('focal length in pixels', fPx) * positive('reference length', lengthMm) / positive('reference length in pixels', lengthPx);
  }

  // ---- calibration self-check (section 5) -----------------------------------
  function aspectCheck(knownW, knownH, pxW, pxH) {
    positive('known width', knownW); positive('known height', knownH); positive('pixel width', pxW); positive('pixel height', pxH);
    const known_aspect = knownH / knownW;
    const image_aspect = pxH / pxW;
    const scale_h = knownW / pxW;
    const scale_v = knownH / pxH;
    const squat_percent = (1 - image_aspect / known_aspect) * 100;
    const warnings = Math.abs(squat_percent) > LIMITS.aspectPercent
      ? [`Image proportions differ from the known shape by ${Math.abs(squat_percent).toFixed(2)} %: confirm plane tilt with converging lines; otherwise suspect cropping, uneven resampling, or a non-physical image, and use one uniform scale off the plane.`]
      : [];
    return { known_aspect, image_aspect, squat_percent, scale_h, scale_v, stretch_percent: (scale_v / scale_h - 1) * 100, warnings };
  }

  // ---- published labels (section 3) -----------------------------------------
  function roundingUncertainty(value, unit, decimals) {
    finite('value', value);
    unit = String(unit).toLowerCase();
    if (!ROUNDING_UNITS.includes(unit)) fail(`unit must be one of ${ROUNDING_UNITS.join(', ')}`);
    if (!Number.isInteger(decimals) || decimals < 0 || decimals > MAX_DECIMALS) fail(`decimals must be an integer from 0 to ${MAX_DECIMALS}`);
    const f = MM_PER[unit];
    const half_interval_mm = (0.5 / 10 ** decimals) * f; // same operation order as Python
    return { value_mm: value * f, half_interval_mm, standard_uncertainty_mm: half_interval_mm / Math.sqrt(3) };
  }

  // ---- fits, finishes, mechanisms (sections 11, 15, 16) ---------------------
  function coatingLoss(perFaceMm, faces = 2) {
    nonNegative('coating per face', perFaceMm);
    if (!Number.isInteger(faces) || faces < 0) fail('faces must be a whole number of at least 0');
    return perFaceMm * faces;
  }
  function clearanceSeries(nominalMm, start, step, count) {
    positive('nominal diameter', nominalMm); finite('start', start); finite('step', step);
    if (!Number.isInteger(count) || count < 1) fail('count must be a positive whole number');
    return Array.from({ length: count }, (_, i) => { // cadkit rounds to 1e-6 mm so 0.1 + 0.2 reads as 0.3
      const diametral = round6(start + i * step);
      const hole_diameter = round6(nominalMm + diametral);
      if (hole_diameter <= 0) fail('every hole diameter must be positive');
      return { diametral, radial: round6(diametral / 2), hole_diameter };
    });
  }
  function gearPair(module, z1, z2, pressureAngleDeg = 20) {
    positive('module', module);
    if (!(pressureAngleDeg > 0 && pressureAngleDeg < 90)) fail('pressure angle must be between 0 and 90 degrees');
    if (!Number.isInteger(z1) || !Number.isInteger(z2) || z1 < 1 || z2 < 1) fail('tooth counts must be whole numbers');
    const undercut = 2 / Math.sin(pressureAngleDeg * Math.PI / 180) ** 2;
    const warnings = [['z1', z1], ['z2', z2]].filter(([, z]) => z < undercut).map(([name, z]) =>
      `${name} = ${z} is below the theoretical undercut limit 2/sin^2(alpha) = ${undercut.toFixed(1)} for unshifted full-depth teeth; use profile shift or a validated generator.`);
    return { d1: module * z1, d2: module * z2, center_distance: module * (z1 + z2) / 2, speed_ratio: -z1 / z2, undercut_limit_teeth: undercut, warnings };
  }
  function windPower(rho, areaM2, v, cp) {
    positive('air density', rho); positive('area', areaM2); nonNegative('wind speed', v);
    if (!(cp >= 0 && cp <= BETZ_LIMIT)) fail('Cp must be between 0 and the Betz limit 16/27 (about 0.593)');
    return finiteResult('power', 0.5 * rho * areaM2 * v ** 3 * cp);
  }

  // ---- evidence classes (section 3) ------------------------------------------
  function evidenceRank(cls) {
    const key = String(cls).trim().toLowerCase().replaceAll(' ', '-');
    const canonical = EVIDENCE_ALIASES[key] || key;
    const rank = EVIDENCE_ORDER.indexOf(canonical);
    if (rank < 0) fail(`unknown evidence class "${cls}"`);
    return rank;
  }
  function weakestEvidence(classes) {
    const list = [...classes];
    if (!list.length) fail('give at least one evidence class');
    return EVIDENCE_ORDER[Math.max(...list.map(evidenceRank))];
  }

  // ---- unit and import sanity (section 2) -----------------------------------
  // A slicer that assumes millimetres shows `observed`; which authoring unit explains it?
  function suggestUnitConversion(observed, expectedMm) {
    positive('observed extent', observed); positive('expected size', expectedMm);
    // Same candidates, order and ranking (stable sort by relative error) as cadkit.calc.suggest_unit_conversion.
    const candidates = [];
    for (const [unit, factor] of Object.entries(MM_PER)) {
      candidates.push({ interpretation: unit === 'mm' ? 'file units are mm (no change)' : `file units are ${unit}`, unit, factor });
      if (unit !== 'mm') candidates.push({ interpretation: `mm geometry already scaled as if it were ${unit}`, unit: `1/${unit}`, factor: 1 / factor });
    }
    for (const c of candidates) {
      c.corrected_mm = observed * c.factor;
      c.relative_error = Math.abs(c.corrected_mm - expectedMm) / expectedMm;
    }
    return candidates.sort((a, b) => a.relative_error - b.relative_error);
  }

  // ---- homography (sections 5 and 12) ----------------------------------------
  // A line-for-line mirror of cadkit/homography.py: Hartley normalisation, the smallest
  // eigenvector of AᵀA by cyclic Jacobi rotations, and the same validation thresholds.
  const FOUR_POINT_WARNING = 'Exactly four point pairs: the homography reproduces them exactly, so residuals are zero by construction and are not accuracy evidence. Add well-distributed control points and reserve an independent check length.';
  const NEAR_COLLINEAR_AREA = 0.05; // in normalised coordinates (mean distance √2)
  const COLLINEAR_AREA = 1e-9;
  function checkPoints(name, pts) {
    if (!Array.isArray(pts)) fail(`${name} points must be a list`);
    return pts.map((p) => {
      if (!Array.isArray(p) || p.length !== 2) fail(`${name} points must be (x, y) pairs`);
      const [x, y] = p.map(Number);
      if (!Number.isFinite(x) || !Number.isFinite(y)) fail(`${name} points must be finite`);
      return [x, y];
    });
  }
  function normaliser(pts) {
    const n = pts.length;
    const cx = pts.reduce((s, p) => s + p[0], 0) / n;
    const cy = pts.reduce((s, p) => s + p[1], 0) / n;
    const meanDist = pts.reduce((s, p) => s + Math.hypot(p[0] - cx, p[1] - cy), 0) / n;
    if (meanDist === 0) fail('points are all identical');
    const k = Math.SQRT2 / meanDist;
    return { T: [[k, 0, -k * cx], [0, k, -k * cy], [0, 0, 1]], pts: pts.map((p) => [(p[0] - cx) * k, (p[1] - cy) * k]) };
  }
  function spreadRatio(pts) {
    const n = pts.length;
    const cx = pts.reduce((s, p) => s + p[0], 0) / n;
    const cy = pts.reduce((s, p) => s + p[1], 0) / n;
    const sxx = pts.reduce((s, p) => s + (p[0] - cx) ** 2, 0) / n;
    const syy = pts.reduce((s, p) => s + (p[1] - cy) ** 2, 0) / n;
    const sxy = pts.reduce((s, p) => s + (p[0] - cx) * (p[1] - cy), 0) / n;
    const tr = sxx + syy, det = sxx * syy - sxy * sxy;
    const disc = Math.sqrt(Math.max(tr * tr / 4 - det, 0));
    const big = tr / 2 + disc, small = tr / 2 - disc;
    return big <= 0 ? 0 : Math.max(small, 0) / big;
  }
  function minTriangleArea(pts) {
    let best = Infinity;
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) for (let k = j + 1; k < pts.length; k++) {
      const [a, b, c] = [pts[i], pts[j], pts[k]];
      best = Math.min(best, Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2);
    }
    return best;
  }
  const matMul = (A, B) => A.map((row) => B[0].map((_, j) => row.reduce((acc, a, k) => acc + a * B[k][j], 0)));
  function inverseSimilarity(T) {
    const k = T[0][0];
    return [[1 / k, 0, -T[0][2] / k], [0, 1 / k, -T[1][2] / k], [0, 0, 1]];
  }
  // Cyclic Jacobi eigen-decomposition of a symmetric matrix; a line-for-line port of
  // cadkit.homography.jacobi_eigen (Frobenius-norm stopping test, skip only exact zeros).
  function jacobiEigen(S, tol = 1e-15, maxSweeps = 100) {
    const n = S.length;
    const A = S.map((r) => r.map(Number));
    const V = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
    let total = 0;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) total += A[i][j] ** 2;
    const scale = Math.sqrt(total) || 1;
    for (let sweep = 0; sweep < maxSweeps; sweep++) {
      let off = 0;
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j) off += A[i][j] ** 2;
      if (Math.sqrt(off) <= tol * scale) break;
      for (let p = 0; p < n - 1; p++) {
        for (let q = p + 1; q < n; q++) {
          const apq = A[p][q];
          if (apq === 0) continue;
          const theta = (A[q][q] - A[p][p]) / (2 * apq);
          const t = (Object.is(theta, -0) || theta < 0 ? -1 : 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
          const c = 1 / Math.sqrt(t * t + 1), s = t * c;
          for (let k = 0; k < n; k++) {
            const akp = A[k][p], akq = A[k][q];
            A[k][p] = c * akp - s * akq; A[k][q] = s * akp + c * akq;
          }
          for (let k = 0; k < n; k++) {
            const apk = A[p][k], aqk = A[q][k];
            A[p][k] = c * apk - s * aqk; A[q][k] = s * apk + c * aqk;
          }
          for (let k = 0; k < n; k++) {
            const vkp = V[k][p], vkq = V[k][q];
            V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq;
          }
        }
      }
    }
    return { values: A.map((r, i) => r[i]), vectors: V };
  }
  function homographyFit(src, dst) {
    const s = checkPoints('src', src), d = checkPoints('dst', dst);
    if (s.length !== d.length) fail('src and dst must have the same number of points');
    if (s.length < 4) fail('a homography needs at least four point pairs');
    for (const [name, pts] of [['src', s], ['dst', d]]) {
      if (new Set(pts.map((p) => p.join(','))).size !== pts.length) fail(`${name} contains duplicate points`);
      if (spreadRatio(pts) < 1e-12) fail(`${name} points are collinear; a homography is undefined`);
    }
    const ns = normaliser(s), nd = normaliser(d);
    if (s.length === 4) {
      for (const [name, n] of [['src', ns], ['dst', nd]]) {
        if (minTriangleArea(n.pts) < COLLINEAR_AREA) fail(`three ${name} points are collinear; four points cannot define a homography`);
      }
    }
    const AtA = Array.from({ length: 9 }, () => new Array(9).fill(0));
    ns.pts.forEach(([u, v], i) => {
      const [x, y] = nd.pts[i];
      for (const row of [[-u, -v, -1, 0, 0, 0, x * u, x * v, x], [0, 0, 0, -u, -v, -1, y * u, y * v, y]]) {
        for (let a = 0; a < 9; a++) for (let b = 0; b < 9; b++) AtA[a][b] += row[a] * row[b];
      }
    });
    const { values, vectors } = jacobiEigen(AtA);
    const order = [...values.keys()].sort((a, b) => values[a] - values[b]);
    const largest = Math.max(Math.abs(values[order[8]]), 1e-300);
    if (values[order[1]] / largest < 1e-12) fail('degenerate point configuration: the homography is not unique');
    const h = vectors.map((row) => row[order[0]]);
    const H = matMul(matMul(inverseSimilarity(nd.T), [h.slice(0, 3), h.slice(3, 6), h.slice(6, 9)]), ns.T);
    if (Math.abs(H[2][2]) < 1e-12) fail('H[2][2] is zero: the mapping sends the image origin to infinity');
    return H.map((row) => row.map((v) => v / H[2][2]));
  }
  function homographyApply(H, [u, v]) {
    const w = H[2][0] * u + H[2][1] * v + H[2][2];
    if (Math.abs(w) < 1e-15) fail('point maps to infinity');
    return [(H[0][0] * u + H[0][1] * v + H[0][2]) / w, (H[1][0] * u + H[1][1] * v + H[1][2]) / w];
  }
  function homographyResiduals(H, src, dst) {
    const residuals = src.map((p, i) => {
      const [x, y] = homographyApply(H, p);
      return Math.hypot(x - dst[i][0], y - dst[i][1]);
    });
    const rms = Math.sqrt(residuals.reduce((s, r) => s + r * r, 0) / residuals.length);
    return { residuals, rms, max: Math.max(...residuals) };
  }
  function homographyJacobian(H, [u, v]) {
    const w = H[2][0] * u + H[2][1] * v + H[2][2];
    if (Math.abs(w) < 1e-15) fail('point maps to infinity');
    const [x, y] = homographyApply(H, [u, v]);
    return [[(H[0][0] - x * H[2][0]) / w, (H[0][1] - x * H[2][1]) / w],
      [(H[1][0] - y * H[2][0]) / w, (H[1][1] - y * H[2][1]) / w]];
  }
  function homographyLocalScale(H, pt) {
    const J = homographyJacobian(H, pt);
    return [Math.hypot(J[0][0], J[1][0]), Math.hypot(J[0][1], J[1][1])];
  }
  // The query point must be a finite pixel on the control points' side of the plane's vanishing
  // line (same sign of w); across it the formula still maps, but the pixel does not image the plane.
  function queryPoint(at) {
    if (!Array.isArray(at) || at.length !== 2) fail('at must be a (u, v) pixel pair');
    const [u, v] = at.map(Number);
    if (!Number.isFinite(u) || !Number.isFinite(v)) fail('at must be a finite (u, v) pixel position');
    return [u, v];
  }
  const side = (H, [u, v]) => Math.sign(H[2][0] * u + H[2][1] * v + H[2][2]);
  function homographyReport(src, dst, at) {
    const s = checkPoints('src', src), d = checkPoints('dst', dst);
    const q = at === undefined || at === null ? null : queryPoint(at);
    const H = homographyFit(s, d);
    const { residuals, rms, max } = homographyResiduals(H, s, d);
    const warnings = [];
    if (s.length === 4) warnings.push(FOUR_POINT_WARNING);
    // Check the count first: the triangle scan is cubic in the number of points.
    if (s.length <= 6 && minTriangleArea(normaliser(s).pts) < NEAR_COLLINEAR_AREA) warnings.push('Some image points are nearly collinear; the estimate is fragile.');
    if (spreadRatio(s) < 0.05) warnings.push('Control points occupy a narrow region; avoid extrapolating beyond it.');
    const report = { H, points: s.length, residuals, rms, max, warnings };
    if (q) {
      const sq = side(H, q);
      if (s.some((p) => side(H, p) !== sq)) fail("at is on or beyond the plane's vanishing line: w there is zero or has the opposite sign to the control points, so the pixel does not image the plane");
      const [sx, sy] = homographyLocalScale(H, q);
      Object.assign(report, { at: q, mapped: homographyApply(H, q), jacobian: homographyJacobian(H, q),
        local_scale_u: sx, local_scale_v: sy, local_anisotropy_percent: (Math.max(sx, sy) / Math.min(sx, sy) - 1) * 100 });
    }
    return report;
  }

  // ---- route finder (section 1) -----------------------------------------------
  function recommendRoute(routes, input, goal) {
    const own = (obj, key) => (Object.prototype.hasOwnProperty.call(obj || {}, key) ? obj[key] : undefined);
    const base = own(routes.by_input, input);
    const g = own(routes.by_goal, goal);
    if (!base) fail(`unknown input "${input}"`);
    if (!g) fail(`unknown goal "${goal}"`);
    const pair = own(routes.pairs, `${input}|${goal}`) || {};
    const sequence = [];
    const add = (w) => { if (w && !sequence.includes(w)) sequence.push(w); };
    add(g.lead);
    add(pair.workflow || base.workflow);
    for (const w of [...(g.also || []), ...(pair.also || [])]) add(w);
    const uniq = (xs) => [...new Set(xs)];
    return {
      input, goal, workflows: sequence,
      sections: sequence.map((w) => routes.workflows[w].section),
      sources: uniq([...base.sources, ...g.sources]),
      checks: [...(g.checks || [])],
      warnings: pair.warning ? [pair.warning] : [],
      calculators: uniq(sequence.flatMap((w) => routes.workflows[w].calculators)),
    };
  }

  const CadCalc = {
    version: '1.0.0', FULL_FRAME_DIAGONAL_MM, MM_PER, EVIDENCE_ORDER, EVIDENCE_ALIASES, BETZ_LIMIT, LIMITS, MAX_DECIMALS, scaleWarnings,
    planarScale, scaledLength, ratioUncertainty, chordError, minSegments, depthFactor, depthFactorRange,
    focalPxFrom35mm, cameraDistance, aspectCheck, roundingUncertainty, coatingLoss, clearanceSeries,
    gearPair, windPower, weakestEvidence, suggestUnitConversion,
    homography: { fit: homographyFit, apply: homographyApply, residuals: homographyResiduals,
      jacobian: homographyJacobian, localScale: homographyLocalScale, report: homographyReport },
    recommendRoute,
  };
  if (typeof module === 'object' && module.exports) module.exports = CadCalc;
  root.CadCalc = CadCalc;
})(typeof globalThis !== 'undefined' ? globalThis : this);
