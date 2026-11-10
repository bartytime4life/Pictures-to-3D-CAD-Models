/* OpenSCAD handoff UI. Browser-only numeric drafts; no server or native launch. */
(function () {
  'use strict';
  const host = document.getElementById('cad');
  if (!host) return;
  const C = globalThis.CadModels;
  const data = JSON.parse(document.getElementById('library-data').textContent);
  const schema = data.openscadModels;
  const templates = data.openscadTemplates;
  const $ = (id) => document.getElementById(id);
  const form = $('cad-form');
  const chooser = $('cad-model');
  const storageKey = 'cad-reference-openscad-drafts-v1';
  const drafts = {};
  let selected = 'plate', storageAvailable = true, restored = false;
  function fresh(id) {
    const model = schema.models[id];
    return { values: Object.fromEntries(model.parameters.map((p) => [p.id, String(p.default)])),
      metadata: Object.fromEntries(model.parameters.map((p) => [p.id, { evidence_class: p.evidence_class, source_or_rationale: p.source_or_rationale, notes: p.notes }])) };
  }
  for (const id of Object.keys(schema.models)) drafts[id] = fresh(id);
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw) {
      const saved = JSON.parse(raw);
      if (saved.version === 1 && saved.drafts && typeof saved.drafts === 'object') {
        for (const [id, model] of Object.entries(schema.models)) {
          const draft = saved.drafts[id];
          if (!draft || typeof draft.values !== 'object' || typeof draft.metadata !== 'object') continue;
          for (const p of model.parameters) {
            const value = draft.values[p.id];
            if (typeof value === 'string' && value.length <= 100 && (value === '' || Number.isFinite(Number(value)))) drafts[id].values[p.id] = value;
            const meta = draft.metadata[p.id];
            if (meta && C.evidenceClasses.includes(meta.evidence_class) && typeof meta.source_or_rationale === 'string') {
              drafts[id].metadata[p.id] = { evidence_class: meta.evidence_class, source_or_rationale: meta.source_or_rationale.slice(0, 2000), notes: p.notes };
            }
          }
        }
        if (schema.models[saved.selected]) selected = saved.selected;
        restored = true;
      }
    }
  } catch { storageAvailable = false; }
  function saveStatus(message, state = 'saved') {
    $('cad-save-status').textContent = message;
    $('cad-save-status').dataset.state = state;
  }
  function save() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ version: 1, selected, drafts }));
      storageAvailable = true;
      saveStatus('Draft saved in this browser. Download the files for an independent copy.');
    } catch {
      storageAvailable = false;
      saveStatus('Browser saving is unavailable. Download your SCAD and parameter CSV before refreshing or closing this page.', 'unavailable');
    }
  }
  const numeric = () => Object.fromEntries(Object.entries(drafts[selected].values).map(([id, value]) => [id, value.trim() === '' ? NaN : Number(value)]));
  const buttons = ['cad-download-scad', 'cad-download-csv', 'cad-download-svg'].map($);
  function showIssues(issues) {
    const box = $('cad-errors'); box.replaceChildren(); box.hidden = !issues.length;
    if (!issues.length) return;
    const title = document.createElement('p'); title.textContent = 'Review these dimensions to enable downloads.'; box.append(title);
    const list = document.createElement('ul');
    for (const issue of issues) { const li = document.createElement('li'); li.textContent = issue.message; list.append(li); }
    box.append(list);
  }
  function refresh() {
    const values = numeric();
    const issues = C.validate(schema, selected, values);
    for (const p of schema.models[selected].parameters) {
      if (!drafts[selected].metadata[p.id].source_or_rationale.trim()) issues.push({ field: p.id, message: `${p.label}: record a source or rationale in the field’s evidence note.` });
    }
    showIssues(issues);
    for (const button of buttons) button.disabled = issues.length > 0;
    for (const input of form.querySelectorAll('[data-parameter]')) input.setAttribute('aria-invalid', String(issues.some((i) => i.field === input.dataset.parameter)));
    if (issues.length) {
      const p = document.createElement('p'); p.className = 'cad-sketch-empty'; p.textContent = 'Update the dimensions to see a valid sketch.';
      $('cad-sketch').replaceChildren(p); $('cad-summary').textContent = 'No drawing or export is produced while dimensions are invalid.'; return;
    }
    const g = C.evaluate(schema, selected, values);
    $('cad-sketch').innerHTML = C.schematicSVG(schema, selected, values);
    $('cad-summary').textContent = `${C.numberText(g.length)} × ${C.numberText(g.width)} × ${C.numberText(g.thickness)} mm · ${Math.max(...g.segments)} sides per ${selected === 'coupon' ? 'largest' : ''} hole · geometric wall checks passed.`;
  }
  function render() {
    chooser.value = selected;
    const model = schema.models[selected], draft = drafts[selected];
    $('cad-description').textContent = model.description;
    $('cad-fixed-note').textContent = selected === 'coupon' ? 'Coupon settings: polygon-flat compensation on; labels off; index notch on. Hole openings are drawn as ideal circles; exported SCAD uses compensated polygons.' : 'Plate holes use inscribed polygons; test a coupon if the opening must fit a pin. The minimum-wall rule checks geometry, not strength.';
    $('cad-cli-command').textContent = `python3 -m cadkit openscad build --model ${selected} --params ${selected}-parameters.csv --output-dir output/${selected}`;
    $('cad-default-render').src = `examples/openscad-starter/${selected}/preview.png`;
    $('cad-default-render').alt = `OpenSCAD render of the default synthetic ${model.title.toLowerCase()}`;
    $('cad-default-mesh').href = `examples/openscad-starter/${selected}/model.stl`;
    form.replaceChildren();
    for (const p of model.parameters) {
      const row = document.createElement('div'); row.className = 'cad-parameter';
      const label = document.createElement('label'); label.htmlFor = 'cad-' + p.id; label.textContent = p.label;
      const field = document.createElement('div'); field.className = 'field';
      const input = document.createElement('input'); input.type = 'number'; input.id = label.htmlFor; input.name = p.id; input.value = draft.values[p.id]; input.step = 'any'; input.inputMode = p.integer ? 'numeric' : 'decimal'; input.dataset.parameter = p.id; input.required = true;
      input.setAttribute('aria-describedby', 'cad-' + p.id + '-evidence');
      if (p.min !== undefined) input.min = String(p.min); if (p.max !== undefined) input.max = String(p.max);
      const unit = document.createElement('span'); unit.className = 'unit'; unit.textContent = p.unit === '1' ? 'count' : p.unit;
      field.append(input, unit);
      const details = document.createElement('details'); details.id = 'cad-' + p.id + '-evidence';
      const summary = document.createElement('summary'); summary.textContent = 'Evidence · ' + draft.metadata[p.id].evidence_class;
      const evidenceLabel = document.createElement('label'); evidenceLabel.textContent = 'Evidence class';
      const evidence = document.createElement('select'); evidence.id = 'cad-evidence-' + p.id;
      for (const value of C.evidenceClasses) { const option = document.createElement('option'); option.value = value; option.textContent = value; evidence.append(option); }
      evidence.value = draft.metadata[p.id].evidence_class; evidenceLabel.append(evidence);
      const rationaleLabel = document.createElement('label'); rationaleLabel.textContent = 'Source or rationale';
      const rationale = document.createElement('textarea'); rationale.id = 'cad-rationale-' + p.id; rationale.rows = 3; rationale.maxLength = 2000; rationale.value = draft.metadata[p.id].source_or_rationale; rationaleLabel.append(rationale);
      details.append(summary, evidenceLabel, rationaleLabel); row.append(label, field, details); form.append(row);
      input.addEventListener('input', () => { draft.values[p.id] = input.value; save(); refresh(); });
      evidence.addEventListener('change', () => { draft.metadata[p.id].evidence_class = evidence.value; summary.textContent = 'Evidence · ' + evidence.value; save(); });
      rationale.addEventListener('input', () => { draft.metadata[p.id].source_or_rationale = rationale.value; save(); refresh(); });
    }
    $('cad-download-status').textContent = 'Download the SCAD and its parameter CSV together to keep the selected values and evidence.';
    refresh();
  }
  function download(format) {
    const values = numeric();
    if (C.validate(schema, selected, values).length) { refresh(); return; }
    const model = schema.models[selected], meta = drafts[selected].metadata;
    const now = new Date();
    const localDate = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
    let text, name, type;
    if (format === 'scad') { text = C.scadSource(schema, selected, values, templates, meta); name = model.filename + '.scad'; type = 'text/plain'; }
    if (format === 'csv') { text = C.parameterCSV(schema, selected, values, meta, localDate); name = model.filename + '-parameters.csv'; type = 'text/csv;charset=utf-8'; }
    if (format === 'svg') { text = C.schematicSVG(schema, selected, values); name = model.filename + '-drawing.svg'; type = 'image/svg+xml'; }
    const url = URL.createObjectURL(new Blob([text], { type }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    $('cad-download-status').textContent = `${name} prepared for download. ${format === 'scad' ? 'Open this file in OpenSCAD to preview and render.' : 'Keep this file with the SCAD model and your references.'}`;
  }
  chooser.addEventListener('change', () => { selected = chooser.value; save(); render(); });
  $('cad-reset').addEventListener('click', () => { drafts[selected] = fresh(selected); save(); render(); });
  for (const format of ['scad', 'csv', 'svg']) $('cad-download-' + format).addEventListener('click', () => download(format));
  form.addEventListener('submit', (event) => event.preventDefault());
  render();
  if (storageAvailable) saveStatus(restored ? 'Your saved dimension and evidence draft was restored in this browser.' : 'Edits save in this browser. Download the files for an independent copy.');
  else saveStatus('Browser saving is unavailable. Download your SCAD and parameter CSV before refreshing or closing this page.', 'unavailable');
})();
