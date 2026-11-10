/* Shared numeric OpenSCAD model helpers. Offline, with no native process or renderer.
 * Node tests exercise these same functions; Python consumes openscad-models.json.
 */
(function (root) {
  'use strict';
  const evidenceClasses = ['inferred', 'image-derived', 'measured', 'unknown'];
  const numberText = (n) => String(Number(Number(n).toPrecision(8)));
  const exactNumber = (n) => String(n);
  function modelFor(schema, id) {
    const model = schema.models[id];
    if (!model) throw new RangeError('Choose a known OpenSCAD model.');
    return model;
  }
  function defaults(schema, id) {
    return Object.fromEntries(modelFor(schema, id).parameters.map((p) => [p.id, p.default]));
  }
  function segments(diameter, error) {
    return Math.max(16, Math.ceil(180 / (Math.acos(1 - error / (diameter / 2)) * 180 / Math.PI)));
  }
  function rawGeometry(id, v) {
    if (id === 'plate') {
      return { length: v.plate_length, width: v.plate_width, thickness: v.plate_thickness,
        end_wall: (v.plate_length - v.hole_spacing - v.hole_diameter) / 2,
        side_wall: (v.plate_width - v.hole_diameter) / 2,
        hole_wall: v.hole_spacing - v.hole_diameter,
        holes: [{ x: (v.plate_length - v.hole_spacing) / 2, y: v.plate_width / 2, diameter: v.hole_diameter },
          { x: (v.plate_length + v.hole_spacing) / 2, y: v.plate_width / 2, diameter: v.hole_diameter }],
        segments: [segments(v.hole_diameter, v.chord_error)] };
    }
    const holes = Array.from({ length: v.clearance_count }, (_, i) => {
      const clearance = v.clearance_start + i * v.clearance_step;
      const diameter = v.pin_diameter + clearance;
      const n = segments(diameter, v.chord_error);
      return { diameter, clearance, segments: n, polygon_radius: diameter / 2 / Math.cos(Math.PI / n) };
    });
    const maxRadius = Math.max(...holes.map((h) => h.polygon_radius));
    const pitch = 2 * maxRadius + v.min_wall;
    const length = 2 * (v.end_wall + maxRadius) + (v.clearance_count - 1) * pitch;
    const width = 2 * (v.min_wall + maxRadius);
    return { length, width, thickness: v.thickness, pitch, max_radius: maxRadius,
      holes: holes.map((h, i) => ({ ...h, x: v.end_wall + maxRadius + i * pitch, y: v.min_wall + maxRadius })),
      segments: holes.map((h) => h.segments),
      notch_wall: (v.end_wall + maxRadius + v.min_wall + maxRadius - v.notch_size) / Math.SQRT2 - maxRadius };
  }
  function validate(schema, id, values) {
    const model = modelFor(schema, id);
    const issues = [];
    const add = (field, message) => issues.push({ field, message });
    for (const p of model.parameters) {
      const v = values[p.id];
      if (typeof v !== 'number' || !Number.isFinite(v)) { add(p.id, `${p.label}: enter a finite number.`); continue; }
      if (p.integer && !Number.isInteger(v)) add(p.id, `${p.label}: enter a whole number.`);
      if (p.min !== undefined && (p.exclusive_min ? v <= p.min : v < p.min)) add(p.id, `${p.label}: use a value ${p.exclusive_min ? 'greater than' : 'at least'} ${p.min} ${p.unit === '1' ? '' : p.unit}.`);
      if (p.max !== undefined && v > p.max) add(p.id, `${p.label}: use at most ${p.max} ${p.unit === '1' ? '' : p.unit}.`);
    }
    if (issues.length) return issues;
    const v = values;
    const smallestDiameter = id === 'plate' ? v.hole_diameter : v.pin_diameter + v.clearance_start;
    if (!(v.chord_error < smallestDiameter / 2)) add('chord_error', 'Radial chord error must be smaller than the smallest hole radius.');
    if (issues.length) return issues;
    const g = rawGeometry(id, v);
    if (Math.max(...g.segments) > 720) add('chord_error', 'Radial chord error is too small for a practical model. Increase it so each hole uses at most 720 sides.');
    if (id === 'plate') {
      if (g.end_wall < v.min_wall) add('hole_spacing', 'End walls are below the minimum wall. Increase length, reduce hole diameter or spacing, or review the wall rule.');
      if (g.side_wall < v.min_wall) add('plate_width', 'Side walls are below the minimum wall. Increase width, reduce hole diameter, or review the wall rule.');
      if (g.hole_wall < v.min_wall) add('hole_spacing', 'Material between the holes is below the minimum wall. Increase spacing, reduce hole diameter, or review the wall rule.');
    } else {
      if (v.end_wall < v.min_wall) add('end_wall', 'End wall must be at least the minimum wall.');
      if (g.notch_wall < v.min_wall) add('notch_size', 'The index notch is too close to the first hole. Reduce the notch size or increase the end wall.');
    }
    return issues;
  }
  function evaluate(schema, id, values) {
    const issues = validate(schema, id, values);
    if (issues.length) throw new RangeError(issues.map((i) => i.message).join(' '));
    return rawGeometry(id, values);
  }
  function metadataFor(model, metadata, p) {
    const supplied = metadata?.[p.id] || {};
    const evidence = supplied.evidence_class ?? p.evidence_class;
    if (!evidenceClasses.includes(evidence)) throw new RangeError(`${p.label}: choose a known evidence class.`);
    const rationale = supplied.source_or_rationale ?? p.source_or_rationale;
    if (typeof rationale !== 'string' || !rationale.trim()) throw new RangeError(`${p.label}: record a source or rationale for this value.`);
    return { evidence_class: evidence, source_or_rationale: rationale,
      notes: supplied.notes ?? p.notes, used_by: model.template };
  }
  const csvCell = (v) => {
    let text = String(v ?? '');
    if (/^\s*[=+\-@]/u.test(text) || /^\s*[\t\r\n]/u.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  function parameterCSV(schema, id, values, metadata = {}, date = '') {
    evaluate(schema, id, values);
    const model = modelFor(schema, id);
    const rows = model.parameters.map((p) => ({ parameter_id: p.id, value: exactNumber(values[p.id]), unit: p.unit,
      ...metadataFor(model, metadata, p), decided_on: date, supersedes: '' }));
    return schema.csv_columns.map(csvCell).join(',') + '\n' + rows.map((row) => schema.csv_columns.map((c) => csvCell(row[c])).join(',')).join('\n') + '\n';
  }
  const comment = (text) => String(text ?? '').replace(/[\r\n]+/g, ' ').replace(/[\u0000-\u001f]/g, ' ').slice(0, 2000);
  function scadSource(schema, id, values, templates, metadata = {}) {
    evaluate(schema, id, values);
    const model = modelFor(schema, id);
    let template = templates[id];
    if (typeof template !== 'string' || !template.trim()) throw new Error('The model template is unavailable. Rebuild the local reference library.');
    // Put the selected defaults before geometry so OpenSCAD Customizer exposes them.
    const controls = model.parameters.map((p) => {
      const meta = metadataFor(model, metadata, p);
      return `// ${p.label} (${p.unit === '1' ? 'count' : p.unit}). ${comment(meta.evidence_class)}: ${comment(meta.source_or_rationale)}\n${p.id} = ${exactNumber(values[p.id])}; // [${p.min}:${p.step}:${p.max}]`;
    }).join('\n\n');
    const identifiers = [...model.parameters.map((p) => p.id), ...Object.keys(model.fixed)];
    for (const key of identifiers) template = template.replace(new RegExp('^' + key + '\\s*=.*;[^\\n]*\\n?', 'gm'), '');
    const fixed = Object.entries(model.fixed).map(([key, value]) => `${key} = ${JSON.stringify(value)};`).join('\n');
    const guard = id === 'plate'
      ? 'assert(min_wall > 0, "minimum wall must be positive");\nassert((plate_length - hole_spacing - hole_diameter) / 2 >= min_wall, "end wall below minimum");\nassert((plate_width - hole_diameter) / 2 >= min_wall, "side wall below minimum");\nassert(hole_spacing - hole_diameter >= min_wall, "wall between holes below minimum");'
      : '';
    return `// Offline OpenSCAD workspace / ${comment(model.title)}\n// Units: mm. Values carry self-recorded evidence; defaults are synthetic.\n// Review F5 preview, then F6 render and export STL in OpenSCAD.\n// No physical fit, strength or printer qualification is implied.\n\n/* [Parameters] */\n${controls}\n\n/* [Hidden] */\n${fixed}\n${guard}\n\n${template}`;
  }
  const xml = (s) => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
  function schematicSVG(schema, id, values) {
    const g = evaluate(schema, id, values);
    const model = modelFor(schema, id);
    // Fit to a fixed export page, preserving XY proportions. Dimensions stay in mm.
    const s = Math.min(630 / g.length, 265 / g.width);
    const w = g.length * s, h = g.width * s, x = (800 - w) / 2, y = 110 + (265 - h) / 2;
    const holes = g.holes.map((hole) => `<circle cx="${x + hole.x * s}" cy="${y + hole.y * s}" r="${hole.diameter / 2 * s}" fill="#fffefa" stroke="#174d68" stroke-width="1.7"/>`).join('');
    const outline = id === 'coupon' && values.notch_size > 0
      ? `<path d="M ${x + values.notch_size * s} ${y} H ${x + w} V ${y + h} H ${x} V ${y + values.notch_size * s} Z"/>`
      : `<rect x="${x}" y="${y}" width="${w}" height="${h}"/>`;
    const dimensions = `<path d="M ${x} ${y - 9} V 63 M ${x + w} ${y - 9} V 63 M ${x} 78 H ${x + w}"/><path d="M ${x + w + 9} ${y} H ${x + w + 47} M ${x + w + 9} ${y + h} H ${x + w + 47} M ${x + w + 31} ${y} V ${y + h}"/>`;
    const label = (tx, ty, str, extra = '') => `<text x="${tx}" y="${ty}" ${extra}>${xml(str)}</text>`;
    const secondLine = id === 'plate'
      ? `2 × Ø${numberText(values.hole_diameter)} mm · centers ${numberText(values.hole_spacing)} mm apart`
      : `Ø${numberText(g.holes[0].diameter)} → Ø${numberText(g.holes.at(-1).diameter)} mm · ${g.holes.length} holes · notch marks first`;
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 510" role="img" aria-labelledby="cad-svg-title cad-svg-desc"><title id="cad-svg-title">${xml(model.title)} dimensional sketch</title><desc id="cad-svg-desc">Top view, ${numberText(g.length)} by ${numberText(g.width)} mm, thickness ${numberText(g.thickness)} mm. Dimensional schematic, not a CAD render.</desc><rect width="800" height="510" rx="12" fill="#fffefa"/><g fill="#d8e9ef" stroke="#174d68" stroke-width="2">${outline}</g>${holes}<g fill="none" stroke="#7d98b7" stroke-width="1.2" stroke-dasharray="5 5"><path d="M ${x - 12} ${y + h / 2} H ${x + w + 12}"/></g><g fill="none" stroke="#566975" stroke-width="1">${dimensions}</g><g font-family="system-ui,sans-serif" fill="#172b37" text-anchor="middle" font-size="16">${label(400, 55, numberText(g.length) + ' mm')}${label(x + w + 38, y + h / 2, numberText(g.width) + ' mm', `transform="rotate(90 ${x + w + 38} ${y + h / 2})"`)}${label(400, 420, secondLine)}${label(400, 451, 'Thickness ' + numberText(g.thickness) + ' mm · top view', 'font-size="14"')}${label(400, 480, 'DIMENSIONAL SKETCH / not a CAD render', 'font-size="12" fill="#566975" letter-spacing="1"')}</g></svg>`;
  }
  const api = { defaults, validate, evaluate, parameterCSV, scadSource, schematicSVG, evidenceClasses, numberText };
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.CadModels = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
