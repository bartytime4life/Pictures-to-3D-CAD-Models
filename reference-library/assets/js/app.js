/* app.js - interface for the offline reference library (inlined into index.html at build).
 * Tabs with deep links, catalog filters, the Toolkit (route finder + calculators), handbook
 * scroll-spy, reading progress, and a light/dark theme. Hash text is only ever used to look
 * elements up by id or as filter values; it is never inserted into the page as HTML.
 */
(function () {
  'use strict';
  const data = JSON.parse(document.getElementById('library-data').textContent);
  const C = window.CadCalc;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
  };
  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'text') node.textContent = v;
      else if (k === 'class') node.className = v;
      else node.setAttribute(k, v === true ? '' : v);
    }
    for (const c of children.flat()) if (c !== null && c !== undefined) node.append(c);
    return node;
  };
  const fmt = (v, digits = 6) => {
    if (!Number.isFinite(v)) return String(v);
    if (Math.abs(v) >= 1e5 || (Math.abs(v) < 1e-4 && v !== 0)) return v.toExponential(3);
    return String(Number(v.toPrecision(digits)));
  };
  const sectionLink = (n) => (data.sectionIds[n] ? '#' + data.sectionIds[n] : '#handbook');

  // ---- theme ------------------------------------------------------------------
  const themeBtn = $('#theme-toggle');
  const prefersDark = () => window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  function effectiveTheme() { return document.documentElement.dataset.theme || (prefersDark() ? 'dark' : 'light'); }
  function paintThemeButton() {
    const dark = effectiveTheme() === 'dark';
    themeBtn.setAttribute('aria-pressed', String(dark));
    themeBtn.querySelector('span').textContent = dark ? 'Light' : 'Dark';
  }
  const saved = store.get('cad-theme');
  if (saved === 'light' || saved === 'dark') document.documentElement.dataset.theme = saved;
  themeBtn.addEventListener('click', () => {
    const next = effectiveTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    store.set('cad-theme', next);
    paintThemeButton();
  });
  paintThemeButton();

  // ---- tabs and deep links ------------------------------------------------------
  const tabs = $$('[role="tab"]');
  const panels = $$('.panel');
  let current = null;
  function activate(id, { focus = false, hash = true } = {}) {
    if (!panels.some((p) => p.id === id)) id = 'handbook';
    current = id;
    tabs.forEach((t) => {
      const on = t.dataset.tab === id;
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      if (on && focus) t.focus();
    });
    panels.forEach((p) => { p.hidden = p.id !== id; });
    // Returning to Sources must keep the same shareable filter state as the controls.
    if (hash) {
      const nextHash = id === 'sources' ? catalogHash() : '#' + id;
      if (location.hash !== nextHash) history.replaceState(null, '', nextHash);
    }
    updateProgress();
  }
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => { activate(t.dataset.tab); window.scrollTo({ top: $('.tabs-wrap').offsetTop, behavior: 'auto' }); });
    t.addEventListener('keydown', (e) => {
      const keys = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 };
      if (!(e.key in keys)) return;
      e.preventDefault();
      const next = tabs[(keys[e.key] + tabs.length) % tabs.length];
      activate(next.dataset.tab, { focus: true });
    });
  });
  function route() {
    // Split before decoding: the query keeps its own %-escapes (a topic like "CAD & drawings"
    // is written as CAD+%26+drawings) and is parsed by URLSearchParams, never decoded twice.
    const raw = location.hash.slice(1);
    const cut = raw.indexOf('?');
    const query = cut < 0 ? undefined : raw.slice(cut + 1);
    let head;
    try { head = decodeURIComponent(cut < 0 ? raw : raw.slice(0, cut)); } catch { return activate('handbook', { hash: false }); }
    if (!head) return activate(current || 'handbook', { hash: false });
    if (panels.some((p) => p.id === head)) {
      activate(head, { hash: false });
      if (head === 'sources') readCatalogQuery(query || '');
      const top = $('.tabs-wrap').offsetTop;
      if (window.scrollY > top || head !== 'handbook') window.scrollTo({ top, behavior: 'auto' });
      return;
    }
    const target = document.getElementById(head);
    if (!target) return activate('handbook', { hash: false });
    const panel = target.closest('.panel');
    if (panel) activate(panel.id, { hash: false });
    requestAnimationFrame(() => {
      target.scrollIntoView({ block: 'start' });
      if (target.classList.contains('calc')) target.querySelector('input,select,textarea')?.focus({ preventScroll: true });
    });
  }
  window.addEventListener('hashchange', route);

  // ---- catalog --------------------------------------------------------------------
  const cards = $$('.source');
  const cardsBox = $('.cards');
  const order = new Map(cards.map((c, i) => [c, i]));
  const f = { q: $('#search'), topic: $('#category'), depth: $('#depth'), level: $('#level'), sort: $('#sort') };
  const sorters = {
    default: (a, b) => order.get(a) - order.get(b),
    title: (a, b) => a.dataset.title.localeCompare(b.dataset.title),
    depth: (a, b) => a.dataset.rank - b.dataset.rank || order.get(a) - order.get(b),
    push: (a, b) => (b.dataset.push || '').localeCompare(a.dataset.push || '') || order.get(a) - order.get(b),
  };
  function catalogHash() {
    const params = new URLSearchParams();
    for (const [k, input] of Object.entries(f)) if (input.value && !(k === 'sort' && input.value === 'default')) params.set(k, input.value);
    const qs = params.toString();
    return '#sources' + (qs ? '?' + qs : '');
  }
  function filterCatalog({ writeHash = true } = {}) {
    const terms = f.q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    const sorted = [...cards].sort(sorters[f.sort.value] || sorters.default);
    sorted.forEach((c) => cardsBox.append(c));
    for (const c of cards) {
      const match = (!f.topic.value || f.topic.value === c.dataset.category)
        && (!f.depth.value || f.depth.value === c.dataset.strength)
        && (!f.level.value || f.level.value === c.dataset.level)
        && terms.every((t) => c.dataset.search.includes(t));
      c.hidden = !match;
      if (match) visible++;
    }
    $('#result-count').textContent = `${visible} of ${cards.length} sources`;
    $('#empty').hidden = visible !== 0;
    $$('.chip[data-topic]').forEach((chip) => chip.setAttribute('aria-pressed', String(chip.dataset.topic === f.topic.value)));
    if (writeHash && current === 'sources') {
      history.replaceState(null, '', catalogHash());
    }
  }
  function readCatalogQuery(query) {
    const params = new URLSearchParams(query);
    for (const [k, input] of Object.entries(f)) {
      const fallback = k === 'sort' ? 'default' : '';
      const v = params.get(k) || fallback;
      // Unknown URL values reset to the default, never retain an unrelated old filter.
      input.value = input.tagName === 'SELECT' && ![...input.options].some((o) => o.value === v) ? fallback : v;
    }
    filterCatalog({ writeHash: false });
  }
  Object.values(f).forEach((input) => input.addEventListener(input.tagName === 'INPUT' ? 'input' : 'change', () => filterCatalog()));
  $$('.chip[data-topic]').forEach((chip) => chip.addEventListener('click', () => {
    f.topic.value = f.topic.value === chip.dataset.topic ? '' : chip.dataset.topic;
    filterCatalog();
  }));
  function resetCatalog() {
    Object.entries(f).forEach(([k, input]) => { input.value = k === 'sort' ? 'default' : ''; });
    filterCatalog(); f.q.focus();
  }
  $('#reset-filters').addEventListener('click', resetCatalog);
  $('#reset-empty').addEventListener('click', resetCatalog);
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
      e.preventDefault(); activate('sources'); f.q.focus();
    }
  });
  filterCatalog({ writeHash: false });

  // ---- toolkit: calculators ----------------------------------------------------------
  const need = (ok, message) => { if (!ok) throw new RangeError(message); };
  const RUN = {
    scale(v) {
      const s = C.planarScale(v.lref, v.pref);
      const warnings = C.scaleWarnings(v.pref, v.p);
      return { rows: [['Scale', fmt(s), 'mm/px'], ['Feature length', fmt(C.scaledLength(v.p, s)), 'mm']], warnings };
    },
    uncertainty(v) {
      const r = C.ratioUncertainty(v.p, v.up, v.pref, v.upref, v.lref, v.ulref);
      return {
        rows: [['Length L', fmt(r.length), 'mm'], ['Standard uncertainty u(L)', fmt(r.u, 4), 'mm'],
          ['Relative', fmt(r.relative * 100, 4), '%'], ['Expanded, k = 2', fmt(r.expanded_k2, 4), 'mm']],
        warnings: r.warnings,
      };
    },
    aspect(v) {
      const r = C.aspectCheck(v.kw, v.kh, v.pw, v.ph);
      const warnings = r.warnings;
      return {
        rows: [['Known aspect H/W', fmt(r.known_aspect), ''], ['Image aspect', fmt(r.image_aspect), ''],
          ['Appears too squat by', fmt(r.squat_percent, 4), '%'], ['Scale, horizontal', fmt(r.scale_h), 'mm/px'],
          ['Scale, vertical', fmt(r.scale_v), 'mm/px'], ['Vertical stretch of mapped content', fmt(r.stretch_percent, 3), '%']],
        warnings,
      };
    },
    homography(v) {
      const lines = String(v.pairs).split('\n').map((l, i) => [i + 1, l.trim()]).filter(([, l]) => l && !l.startsWith('#'));
      const pairs = lines.map(([lineNo, l]) => {
        const n = l.split(/[\s,;]+/).map(Number);
        if (n.length !== 4 || n.some((x) => !Number.isFinite(x))) throw new RangeError(`Line ${lineNo} needs four numbers: u v x y`);
        return n;
      });
      const src = pairs.map((p) => [p[0], p[1]]);
      const dst = pairs.map((p) => [p[2], p[3]]);
      const r = C.homography.report(src, dst, [v.u, v.v]);
      return {
        rows: [['Point pairs', String(pairs.length), ''], ['RMS residual', fmt(r.rms, 4), 'mm'], ['Largest residual', fmt(r.max, 4), 'mm'],
          ['(u, v) maps to', `${fmt(r.mapped[0], 5)}, ${fmt(r.mapped[1], 5)}`, 'mm'],
          ['Local scale along u', fmt(r.local_scale_u, 5), 'mm/px'], ['Local scale along v', fmt(r.local_scale_v, 5), 'mm/px'],
          ['Local anisotropy', fmt(r.local_anisotropy_percent, 3), '%']],
        matrix: r.H,
        warnings: r.warnings,
      };
    },
    depth(v) {
      need(v.size >= 0, 'Size at reference scale must be zero or positive');
      const factor = C.depthFactor(v.z, v.d);
      const [lo, hi] = C.depthFactorRange(v.zmin, v.zmax, v.dmin, v.dmax);
      const warnings = [];
      if (Math.abs(v.d) / v.z > C.LIMITS.depthRatio) warnings.push('Δ is more than 20 % of Z, so the correction is large and depends strongly on the camera distance.');
      return {
        rows: [['Depth factor', fmt(factor, 5), '×'], ['Corrected size', fmt(v.size * factor, 5), 'mm'],
          ['Factor range from bounds', `${fmt(lo, 4)} – ${fmt(hi, 4)}`, '×'],
          ['Size range from bounds', `${fmt(v.size * lo, 4)} – ${fmt(v.size * hi, 4)}`, 'mm']],
        warnings,
      };
    },
    camera(v) {
      const fpx = C.focalPxFrom35mm(v.f35, v.w, v.h);
      return { rows: [['Focal length', fmt(fpx, 5), 'px'], ['Distance to reference Z', fmt(C.cameraDistance(fpx, v.L, v.l), 5), 'mm']], warnings: [] };
    },
    label(v) {
      const r = C.roundingUncertainty(v.value, v.unit, v.decimals);
      return {
        rows: [['Value', fmt(r.value_mm), 'mm'], ['Rounding bound ±a', fmt(r.half_interval_mm, 4), 'mm'],
          ['Standard uncertainty a/√3', fmt(r.standard_uncertainty_mm, 4), 'mm']],
        warnings: [],
      };
    },
    chord(v) {
      const n = C.minSegments(v.r, v.e);
      const warnings = n > C.LIMITS.segments ? ['More than 720 segments: consider chordal/angular export settings or a coarser tolerance.'] : [];
      return {
        rows: [['Minimum segments n', String(n), ''], ['Actual error at n', fmt(C.chordError(v.r, n), 4), 'mm'],
          ['Error at n − 1', n > 3 ? fmt(C.chordError(v.r, n - 1), 4) : '–', 'mm'], ['OpenSCAD', `$fn = ${n}`, '']],
        warnings,
      };
    },
    clearance(v) {
      need(v.count <= 200, 'Show at most 200 holes here; python3 -m cadkit coupon handles longer series');
      const series = C.clearanceSeries(v.nominal, v.start, v.step, v.count);
      const warnings = Math.abs(v.step) < 0.05 ? ['Steps under 0.05 mm are finer than many printers resolve; measure the coupon rather than trusting nominal steps.'] : [];
      return {
        rows: [['Holes', String(series.length), ''], ['Hole diameters', `${fmt(series[0].hole_diameter)} – ${fmt(series[series.length - 1].hole_diameter)}`, 'mm']],
        table: { head: ['Hole', 'Hole D (mm)', 'Diametral (mm)', 'Radial (mm)'], rows: series.map((s, i) => [i + 1, fmt(s.hole_diameter), fmt(s.diametral), fmt(s.radial)]) },
        warnings,
      };
    },
    coating(v) {
      need(v.width > 0, 'Slot width must be positive');
      const loss = C.coatingLoss(v.coat, v.faces);
      const warnings = loss >= v.width ? ['The coating closes the slot completely.'] : [];
      return { rows: [['Width lost', fmt(loss, 4), 'mm'], ['Finished slot width', fmt(v.width - loss, 5), 'mm']], warnings };
    },
    gear(v) {
      const r = C.gearPair(v.m, v.z1, v.z2);
      return {
        rows: [['Pitch diameter d₁', fmt(r.d1), 'mm'], ['Pitch diameter d₂', fmt(r.d2), 'mm'],
          ['Centre distance a', fmt(r.center_distance), 'mm'], ['Speed ratio ω₂/ω₁', fmt(r.speed_ratio, 4), '']],
        warnings: r.warnings,
      };
    },
    units(v) {
      const ranked = C.suggestUnitConversion(v.observed, v.expected);
      const best = ranked[0];
      const warnings = best.relative_error >= 0.05 // same threshold and wording as python3 -m cadkit units
        ? ['No common unit explains the mismatch within 5 %; check which dimension is meant.'] : [];
      return {
        rows: [['Most likely', best.interpretation, ''], ['Multiply by', fmt(best.factor), ''], ['Corrected extent', fmt(best.corrected_mm, 5), 'mm'],
          ['Remaining difference', fmt(best.relative_error * 100, 3), '%']],
        table: { head: ['Explanation', 'Factor', 'Corrected (mm)', 'Off by'], rows: ranked.slice(0, 5).map((r) => [r.interpretation, fmt(r.factor), fmt(r.corrected_mm, 5), fmt(r.relative_error * 100, 3) + ' %']) },
        warnings,
      };
    },
    evidence(v) {
      const chosen = [v.a, v.b, v.c, v.d].filter((x) => x && x !== '(none)');
      return { rows: [['Inputs', chosen.join(' + ') || '–', ''], ['Result class', C.weakestEvidence(chosen), '']], warnings: [] };
    },
    wind(v) {
      need(v.diameter > 0, 'Rotor diameter must be positive');
      const area = Math.PI * (v.diameter / 2) ** 2;
      return {
        rows: [['Swept area A', fmt(area, 4), 'm²'], ['Power P', fmt(C.windPower(v.rho, area, v.v, v.cp), 4), 'W']],
        warnings: v.cp > 0.45 ? ['C_p above about 0.45 is optimistic for a small rotor; the Betz limit is 0.593.'] : [],
      };
    },
  };

  function buildCalc(spec) {
    const form = el('form', { class: 'calc-form', novalidate: true });
    for (const input of spec.inputs) {
      const id = `in-${spec.id}-${input.k}`;
      let control;
      if (input.type === 'select') {
        control = el('select', { id, name: input.k }, input.options.map((o) => el('option', { value: o, text: o, selected: o === input.value })));
      } else if (input.type === 'textarea') {
        control = el('textarea', { id, name: input.k, rows: 7, spellcheck: 'false' });
        control.value = input.value;
      } else {
        control = el('input', { id, name: input.k, type: 'number', inputmode: 'decimal', step: input.step ?? 'any', value: input.value });
      }
      control.dataset.default = input.value;
      form.append(el('label', { for: id, class: input.type === 'textarea' ? 'wide' : '' },
        el('span', { text: input.label }), el('span', { class: 'field' }, control, input.unit ? el('span', { class: 'unit', text: input.unit }) : null)));
    }
    const out = el('div', { class: 'calc-out', role: 'status', 'aria-live': 'polite' });
    const actions = el('div', { class: 'calc-actions' },
      el('button', { type: 'button', class: 'ghost', 'data-action': 'reset', text: 'Reset' }),
      el('button', { type: 'button', class: 'ghost', 'data-action': 'copy', text: 'Copy result' }));
    const card = el('section', { class: 'calc', id: `calc-${spec.id}`, 'aria-labelledby': `calc-${spec.id}-title` },
      el('header', {},
        el('h3', { id: `calc-${spec.id}-title`, text: spec.title }),
        el('a', { class: 'sec', href: sectionLink(spec.section), text: `§${spec.section}` })),
      el('p', { class: 'blurb', text: spec.blurb }),
      el('code', { class: 'formula', text: spec.formula }),
      form, out, el('p', { class: 'calc-note', text: spec.note }), actions);
    let lastText = '';
    function run() {
      const values = {};
      out.replaceChildren();
      try {
        for (const input of spec.inputs) {
          const control = form.elements[input.k];
          if (input.type === 'select' || input.type === 'textarea') { values[input.k] = control.value; continue; }
          // An empty or unparsable field is an error, never a silent zero.
          need(control.value.trim() !== '' && Number.isFinite(Number(control.value)), `${input.label} needs a number`);
          values[input.k] = Number(control.value);
        }
        const r = RUN[spec.id](values);
        const dl = el('dl');
        for (const [k, val, unit] of r.rows) dl.append(el('dt', { text: k }), el('dd', { 'data-out': k }, el('strong', { text: val }), unit ? ` ${unit}` : ''));
        out.append(dl);
        if (r.matrix) {
          out.append(el('table', { class: 'matrix', 'aria-label': 'Homography matrix H' },
            el('tbody', {}, r.matrix.map((row) => el('tr', {}, row.map((x) => {
              const big = Math.max(...r.matrix.flat().map(Math.abs));
              return el('td', { text: Math.abs(x) < 1e-12 * big ? '0' : fmt(x, 6) }); // hide round-off noise
            }))))));
        }
        if (r.table) {
          out.append(el('table', { class: 'mini' }, el('thead', {}, el('tr', {}, r.table.head.map((h) => el('th', { text: h })))),
            el('tbody', {}, r.table.rows.map((row) => el('tr', {}, row.map((x) => el('td', { text: String(x) })))))));
        }
        if (r.warnings.length) out.append(el('ul', { class: 'warn' }, r.warnings.map((w) => el('li', { text: w }))));
        card.dataset.state = r.warnings.length ? 'warn' : 'ok';
        lastText = `${spec.title}\n` + r.rows.map(([k, v2, u]) => `${k}: ${v2}${u ? ' ' + u : ''}`).join('\n')
          + (r.warnings.length ? '\nWarnings: ' + r.warnings.join(' ') : '');
      } catch (err) {
        out.append(el('p', { class: 'error', text: err instanceof RangeError ? err.message : 'Could not calculate: ' + err.message }));
        card.dataset.state = 'error';
        lastText = '';
      }
    }
    form.addEventListener('input', run);
    form.addEventListener('submit', (e) => e.preventDefault());
    actions.addEventListener('click', async (e) => {
      const action = e.target.dataset.action;
      if (action === 'reset') {
        for (const input of spec.inputs) form.elements[input.k].value = form.elements[input.k].dataset.default;
        run();
      } else if (action === 'copy' && lastText) {
        try { await navigator.clipboard.writeText(lastText); e.target.textContent = 'Copied'; }
        catch { e.target.textContent = 'Copy unavailable'; }
        setTimeout(() => { e.target.textContent = 'Copy result'; }, 1600);
      }
    });
    run();
    return card;
  }
  const grid = $('#calc-grid');
  data.calculators.forEach((spec) => grid.append(buildCalc(spec)));

  // ---- toolkit: route finder ------------------------------------------------------------
  const routeIn = $('#route-input'), routeGoal = $('#route-goal'), routeOut = $('#route-out');
  function renderRoute() {
    const r = C.recommendRoute(data.routes, routeIn.value, routeGoal.value);
    const steps = el('ol', { class: 'route-steps' }, r.workflows.map((w, i) => {
      const wf = data.routes.workflows[w];
      return el('li', {},
        el('div', { class: 'route-badge', text: w }),
        el('div', {},
          el('h4', {}, el('a', { href: sectionLink(wf.section), text: `${wf.name} (§${wf.section})` })),
          el('p', {}, el('strong', { text: i === 0 ? 'Start: ' : 'Then: ' }), wf.start + '.'),
          el('p', { class: 'meta' }, `Deliverable: ${wf.deliverable}. Still missing: ${wf.missing}.`)));
    }));
    const srcList = el('ul', { class: 'route-sources' }, r.sources.filter((id) => data.sourceIndex[id]).map((id) =>
      el('li', {}, el('a', { href: data.sourceIndex[id].url, target: '_blank', rel: 'noopener noreferrer', text: data.sourceIndex[id].title }))));
    const calcs = el('p', { class: 'route-calcs' }, 'Calculators: ', r.calculators.map((id) => {
      const spec = data.calculators.find((c) => c.id === id);
      return spec ? el('a', { class: 'chip', href: '#calc-' + id, text: spec.title }) : null;
    }));
    routeOut.replaceChildren(
      r.warnings.length ? el('p', { class: 'route-warn', role: 'note' }, el('strong', { text: 'Watch out: ' }), r.warnings.join(' ')) : '',
      steps,
      el('div', { class: 'route-cols' },
        el('div', {}, el('h4', { text: 'Checks before you print' }), el('ul', {}, r.checks.map((c) => el('li', { text: c })))),
        el('div', {}, el('h4', { text: 'Read first' }), srcList)),
      calcs);
  }
  routeIn.addEventListener('change', renderRoute);
  routeGoal.addEventListener('change', renderRoute);
  renderRoute();

  // ---- handbook: scroll-spy, progress, back to top ------------------------------------------
  const tocLinks = new Map($$('.contents a').map((a) => [a.getAttribute('href').slice(1), a]));
  if ('IntersectionObserver' in window) {
    const seen = new Map();
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((e) => seen.set(e.target.id, e.isIntersecting));
      const firstVisible = [...tocLinks.keys()].find((id) => seen.get(id));
      if (!firstVisible) return;
      tocLinks.forEach((a, id) => (id === firstVisible ? a.setAttribute('aria-current', 'true') : a.removeAttribute('aria-current')));
      const link = tocLinks.get(firstVisible);
      const box = link.closest('.contents');
      if (box && (link.offsetTop < box.scrollTop || link.offsetTop > box.scrollTop + box.clientHeight - 40)) box.scrollTop = link.offsetTop - 60;
    }, { rootMargin: '-90px 0px -60% 0px' });
    tocLinks.forEach((_, id) => { const h = document.getElementById(id); if (h) spy.observe(h); });
  }
  const bar = $('#progress');
  const topBtn = $('#to-top');
  function updateProgress() {
    const doc = document.documentElement;
    const max = doc.scrollHeight - window.innerHeight;
    const ratio = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    bar.style.transform = `scaleX(${ratio})`;
    topBtn.hidden = window.scrollY < 900;
  }
  window.addEventListener('scroll', updateProgress, { passive: true });
  topBtn.addEventListener('click', () => { window.scrollTo({ top: 0 }); $('[role="tab"][aria-selected="true"]').focus(); });

  route();
  window.CadLibrary = { activate, route, RUN };
})();
