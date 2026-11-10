// Build the offline library from its editable sources.
//
//   node scripts/build-library.mjs
//
// Reads:  sources.json (authoritative catalog), library.json (revision), HANDBOOK.md,
//         RESEARCH-NOTES.md, templates/*.md, assets/{css,js,data}, assets/figures/*.svg
// Writes: sources.csv, REFERENCES.md, GITHUB.md, index.html, tmp/*.html (PDF fragments),
//         tmp/build-info.json
// Run scripts/make-figures.py first so figures (including the catalog chart) are current.
import fs from 'node:fs';
import path from 'node:path';
import { ROOT, importModule, read, readJSON, write, esc, slugify, EVIDENCE, validateSources } from './lib/runtime.mjs';

const { marked } = await importModule('marked');
const lib = readJSON('library.json');
const sources = readJSON('sources.json');
const routes = readJSON('assets/data/routes.json');
const calculators = readJSON('assets/data/calculators.json');
const openscadModels = readJSON('assets/data/openscad-models.json');
const openscadTemplates = Object.fromEntries(Object.entries(openscadModels.models).map(([id, model]) => [id, read(model.template)]));

// ---- validate before writing anything ----------------------------------------------
const problems = validateSources(sources);
const ids = new Set(sources.map((s) => s.id));
for (const [k, r] of Object.entries(routes.by_input)) {
  if (!routes.workflows[r.workflow]) problems.push(`routes.by_input.${k}: unknown workflow ${r.workflow}`);
  for (const id of r.sources) if (!ids.has(id)) problems.push(`routes.by_input.${k}: unknown source ${id}`);
}
for (const [k, g] of Object.entries(routes.by_goal)) {
  for (const id of g.sources) if (!ids.has(id)) problems.push(`routes.by_goal.${k}: unknown source ${id}`);
  for (const w of [g.lead, ...(g.also || [])].filter(Boolean)) if (!routes.workflows[w]) problems.push(`routes.by_goal.${k}: unknown workflow ${w}`);
}
for (const item of routes.inputs) if (!Object.hasOwn(routes.by_input, item.id)) problems.push(`routes.inputs: ${item.id} has no by_input rule`);
for (const item of routes.goals) if (!Object.hasOwn(routes.by_goal, item.id)) problems.push(`routes.goals: ${item.id} has no by_goal rule`);
for (const [k, pair] of Object.entries(routes.pairs || {})) {
  const [inp, goal] = k.split('|');
  if (!Object.hasOwn(routes.by_input, inp) || !Object.hasOwn(routes.by_goal, goal)) problems.push(`routes.pairs.${k}: unknown input or goal`);
  for (const w of [pair.workflow, ...(pair.also || [])].filter(Boolean)) if (!routes.workflows[w]) problems.push(`routes.pairs.${k}: unknown workflow ${w}`);
}
const calcIds = new Set(calculators.map((c) => c.id));
for (const [k, w] of Object.entries(routes.workflows)) {
  for (const c of w.calculators) if (!calcIds.has(c)) problems.push(`routes.workflows.${k}: unknown calculator ${c}`);
}
if (problems.length) {
  console.error('Refusing to build; fix these first:\n  ' + problems.join('\n  '));
  process.exit(1);
}

const categories = [...new Set(sources.map((s) => s.category))];
const repos = sources.filter((s) => s.type === 'GitHub repository');
const evidenceLabel = (k) => EVIDENCE[k].label;

// ---- generated data files ------------------------------------------------------------
const cols = ['id', 'category', 'title', 'url', 'type', 'level', 'use', 'limit', 'evidence', 'checked', 'repository', 'license_metadata', 'archived', 'last_push', 'default_branch'];
const csvCell = (v) => '"' + String(v ?? '').replaceAll('"', '""') + '"';
write('sources.csv', cols.map(csvCell).join(',') + '\n' + sources.map((s) => cols.map((k) => csvCell(s[k])).join(',')).join('\n') + '\n');

let refs = `# Annotated source directory\n\n${sources.length} resources. Checked ${lib.date_label}. Review depth is recorded for each entry; links are not claims of full-document review.\n\n`;
for (const cat of categories) {
  refs += `## ${cat}\n\n`;
  for (const s of sources.filter((x) => x.category === cat)) {
    refs += `### [${s.title}](${s.url})\n\n${s.type} | ${s.level} | ${evidenceLabel(s.evidence)}\n\n${s.use}\n\n**Limit:** ${s.limit}\n\n`;
  }
}
write('REFERENCES.md', refs);

const latestCheck = repos.map((s) => s.checked).sort().at(-1) || lib.date;
let github = `# GitHub directory\n\nLive metadata snapshot: ${new Date(latestCheck + 'T12:00:00Z').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' })}, refreshed with \`scripts/refresh-github.mjs\`. These repositories were not installed, executed, or benchmarked. Last push is a repository event, not a stable release or quality score. API license labels are informational; review code, dependencies, data, and model-weight terms separately.\n\n`;
for (const s of repos) {
  github += `## [${s.title}](${s.url})\n\n${s.use}\n\n**Use with care:** ${s.limit}\n\n- Default branch: \`${s.default_branch}\`\n- Last push: ${s.last_push}\n- Archived: ${s.archived ? 'yes' : 'no'}\n- GitHub license metadata: \`${s.license_metadata}\`\n\n`;
}
github += '## License metadata caveat\n\n`NOASSERTION` is not a grant of rights. The libigl API reported GPL-3.0 while the repository description referenced MPL-2.0; this is a reason to read component licensing, not to choose one label by assumption.\n';
write('GITHUB.md', github);

// ---- Markdown rendering ------------------------------------------------------------------
const docs = ['HANDBOOK.md', 'RESEARCH-NOTES.md', 'REFERENCES.md', 'GITHUB.md'];
for (const f of docs) write('tmp/' + f.replace('.md', '.html'), marked.parse(read(f))); // raw fragments for the PDF
const templates = ['PROJECT-BRIEF.md', 'CAPTURE-CHECKLIST.md', 'INDEPENDENT-CHECKS.md', 'PRINT-ACCEPTANCE.md'];
for (const f of templates) write('tmp/' + f.replace('.md', '.html'), marked.parse(read('templates/' + f)));

const stripTags = (h) => h.replace(/<[^>]+>/g, '');
function render(md, prefix, toc) {
  const used = new Set();
  return marked.parse(md)
    .replace(/<h([1-6])>([\s\S]*?)<\/h\1>/g, (_, n, inner) => {
      const base = `${prefix}-${slugify(stripTags(inner))}`;
      let id = base;
      for (let k = 2; used.has(id); k++) id = `${base}-${k}`;
      used.add(id);
      if (toc && n === '2') toc.push({ id, title: stripTags(inner) });
      const anchor = n === '1' ? '' : `<a class="anchor" href="#${id}" aria-label="Link to this section">#</a>`;
      return `<h${n} id="${id}">${inner}${anchor}</h${n}>`;
    })
    .replace(/<p>(<img [^>]*>)<\/p>/g, (_, img) => {
      const alt = (img.match(/alt="([^"]*)"/) || [])[1] || '';
      const title = (img.match(/title="([^"]*)"/) || [])[1];
      const tag = img.replace(/ title="[^"]*"/, '').replace('<img ', '<img loading="lazy" decoding="async" ');
      return `<figure class="fig">${tag}<figcaption>${title || alt}</figcaption></figure>`;
    })
    .replace(/<a href="(https:\/\/[^"]+)"/g, '<a href="$1" target="_blank" rel="noopener noreferrer"');
}
const toc = [];
const book = render(read('HANDBOOK.md'), 'book', toc);
const research = render(read('RESEARCH-NOTES.md'), 'research');
const gh = render(github, 'github');
const sectionIds = {};
for (const t of toc) {
  const m = t.title.match(/^(\d+)\./);
  if (m) sectionIds[m[1]] = t.id;
}
const worksheets = templates.map((f, i) => `<div class="worksheet"><a class="download" href="templates/${f}" download>Download worksheet</a>${render(read('templates/' + f), 'sheet' + i)}</div>`).join('');

// ---- catalog cards ---------------------------------------------------------------------
const catIndex = new Map(categories.map((c, i) => [c, i]));
const levels = [...new Set(sources.map((s) => s.level))].sort();
const card = (s) => {
  const ev = EVIDENCE[s.evidence];
  const search = [s.id, s.title, s.category, s.use, s.limit, s.type, s.level, s.repository].filter(Boolean).join(' ').toLowerCase();
  const repoMeta = s.type === 'GitHub repository'
    ? `<p class="repo-meta">${esc(s.license_metadata)} · last push ${esc(String(s.last_push).slice(0, 10))}${s.archived ? ' · archived' : ''}</p>` : '';
  return `<article class="source" id="src-${esc(s.id)}" style="--c:var(--cat-${catIndex.get(s.category) % 10})" data-category="${esc(s.category)}" data-strength="${ev.strength}" data-rank="${ev.rank}" data-level="${esc(s.level)}" data-title="${esc(s.title.toLowerCase())}" data-push="${esc(s.last_push || '')}" data-search="${esc(search)}">`
    + `<div class="kicker"><span class="dot" aria-hidden="true"></span>${esc(s.category)} · ${esc(s.type)}</div>`
    + `<h3><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} <span aria-hidden="true">↗</span></a></h3>`
    + `<p>${esc(s.use)}</p><p class="limit">${esc(s.limit)}</p>${repoMeta}`
    + `<div class="source-footer"><span>${esc(s.level)}</span><span class="badge ${ev.strength}" title="Review depth">${esc(ev.label)}</span></div></article>`;
};
const cards = sources.map(card).join('');
const chips = categories.map((c) => `<button type="button" class="chip" data-topic="${esc(c)}" aria-pressed="false" style="--c:var(--cat-${catIndex.get(c) % 10})"><span class="dot" aria-hidden="true"></span>${esc(c)} <b>${sources.filter((s) => s.category === c).length}</b></button>`).join('');

// ---- figures -------------------------------------------------------------------------------
const figurePath = (name) => path.join(ROOT, 'assets/figures', name + '.svg');
const inlineFlow = path.join(ROOT, 'tmp/figures-inline/process-flow.svg');
const heroFlow = fs.existsSync(inlineFlow)
  ? fs.readFileSync(inlineFlow, 'utf8').replace('<svg ', '<svg class="hero-flow" ')
  : `<img class="hero-flow" src="assets/figures/process-flow.svg" alt="Capture, measure, reconstruct, model and draw, print and check">`;
const figureCount = fs.existsSync(path.join(ROOT, 'assets/figures')) ? fs.readdirSync(path.join(ROOT, 'assets/figures')).filter((f) => f.endsWith('.svg')).length : 0;
const composition = fs.existsSync(figurePath('catalog-composition'))
  ? `<img class="composition" src="assets/figures/catalog-composition.svg" alt="Bar chart of ${sources.length} sources by topic, split by review depth" loading="lazy">` : '';

// ---- worksheet and example links (only files that exist) ------------------------------------
const linkIf = (href, label, attrs = '') => (fs.existsSync(path.join(ROOT, href)) ? `<a href="${href}" ${attrs}>${label}</a>` : '');
const exampleLinks = [
  linkIf('examples/two-hole-plate.scad', 'OpenSCAD plate', 'download'),
  linkIf('examples/plate-parameters.csv', 'Plate parameter register', 'download'),
  linkIf('examples/build_plate.py', 'Parameter → STL → checks pipeline', 'download'),
  linkIf('examples/clearance-coupon.scad', 'Clearance coupon (OpenSCAD)', 'download'),
  linkIf('examples/two-hole-plate.svg', 'SVG diagram', 'download'),
  linkIf('examples/calculate.py', 'Calculation script', 'download'),
  linkIf('examples/calculation-results.json', 'Calculated values', 'download'),
  linkIf('cadkit/README.md', 'cadkit command-line guide'),
].filter(Boolean).join('');

// ---- page ---------------------------------------------------------------------------------
const libraryData = {
  revision: lib.revision, routes, calculators, sectionIds, openscadModels, openscadTemplates,
  sourceIndex: Object.fromEntries(sources.map((s) => [s.id, { title: s.title, url: s.url }])),
};
const jsonForScript = (v) => JSON.stringify(v).replaceAll('<', '\\u003c').replaceAll('\u2028', '\\u2028').replaceAll('\u2029', '\\u2029');
const tabsSpec = [['handbook', 'Handbook', ''], ['toolkit', 'Toolkit', calculators.length], ['photos', 'Photos', ''], ['cad', 'OpenSCAD', ''], ['sources', 'Sources', sources.length],
  ['github', 'GitHub', repos.length], ['research', 'Research notes', ''], ['worksheets', 'Worksheets & examples', '']];
const option = (v, label = v) => `<option value="${esc(v)}">${esc(label)}</option>`;
const css = read('assets/css/library.css') + '\n' + read('assets/css/photos.css') + '\n' + read('assets/css/cad.css');
const js = read('assets/js/cadcalc.js') + '\n' + read('assets/js/app.js') + '\n' + read('assets/js/photos.js') + '\n' + read('assets/js/photo-transfer.js') + '\n' + read('assets/js/photo-register.js') + '\n' + read('assets/js/photo-workspace.js') + '\n' + read('assets/js/cad-models.js') + '\n' + read('assets/js/cad-workspace.js');
const photoWorkspace = read('assets/photo-workspace.html');
const cadWorkspace = read('assets/cad-workspace.html');

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Offline reference library for turning photographs into printable CAD: handbook, ${sources.length} annotated sources, ${calculators.length} calculators, worksheets.">
<meta name="color-scheme" content="light dark">
<title>Pictures to printable CAD | Reference library</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23174d68'/%3E%3Crect x='6' y='11' width='20' height='10' fill='none' stroke='white' stroke-width='2'/%3E%3Ccircle cx='11' cy='16' r='2' fill='white'/%3E%3Ccircle cx='21' cy='16' r='2' fill='white'/%3E%3C/svg%3E">
<style>
${css}</style>
</head>
<body>
<a class="skip" href="#main">Skip to reference material</a>
<div class="mast-wrap"><header class="mast">
<div class="brand"><span class="eyebrow">Field reference / 3D &amp; CAD</span><span class="brand-meta"><span>Revision ${lib.revision} · ${esc(lib.date_label)} · Works offline</span><button id="theme-toggle" type="button" aria-pressed="false" title="Switch light or dark theme"><span>Dark</span></button></span></div>
<h1>From pictures<br>to <em>printable</em> CAD.</h1>
<p class="lede">A practical library for recovering shape, establishing dimensions, rebuilding editable geometry, and checking the part you print, with calculators that show their working.</p>
<div class="actions"><a class="btn primary" href="#photos">Add reference photos</a><a class="btn" href="#cad">Make an OpenSCAD part</a><a class="btn" href="output/pdf/pictures-to-printable-cad.pdf">Read the PDF</a><a class="btn" href="#toolkit">Open the toolkit</a><a class="btn" href="sources.csv" download>Source CSV</a><a class="btn" href="HANDBOOK.md" download>Editable handbook</a></div>
<ul class="stats" aria-label="Library contents">
<li><b>${toc.length}</b><span>Handbook chapters</span></li>
<li><b>${sources.length}</b><span>Annotated sources</span></li>
<li><b>${repos.length}</b><span>Repository records</span></li>
<li><b>${calculators.length}</b><span>Calculators</span></li>
<li><b>${figureCount}</b><span>Figures</span></li>
</ul>
${heroFlow}
</header></div>
<div class="tabs-wrap"><nav class="tabs" role="tablist" aria-label="Reference library sections">${tabsSpec.map(([id, label, count], i) => `<button id="tab-${id}" role="tab" aria-controls="${id}" aria-selected="${i === 0}" tabindex="${i === 0 ? 0 : -1}" data-tab="${id}">${label}${count !== '' ? ` <span class="count">${count}</span>` : ''}</button>`).join('')}</nav><div id="progress" aria-hidden="true"></div></div>
<main class="main" id="main">
<section class="panel" id="handbook" role="tabpanel" aria-labelledby="tab-handbook" tabindex="-1"><div class="reading"><aside class="contents" aria-label="Handbook contents"><h2>In this handbook</h2>${toc.map((t) => `<a href="#${t.id}">${t.title}</a>`).join('')}</aside><article class="prose"><div class="note"><strong>First project:</strong> choose a simple measured part, model its critical interfaces, and print a small fit coupon. The <a href="#toolkit">Toolkit</a> suggests a route and checks the arithmetic.</div>${book}</article></div></section>
<section class="panel" id="toolkit" role="tabpanel" aria-labelledby="tab-toolkit" tabindex="-1" hidden>
<div class="tool-intro"><div><h2 class="panel-title">Toolkit</h2><p class="panel-lede">A route finder and ${calculators.length} calculators for the handbook's formulas. They run in this page with no network, mirror <code>python3 -m cadkit</code> exactly (the test suite compares them), and flag the conditions the handbook warns about. Results are arithmetic under stated assumptions, not measurements.</p></div></div>
<div class="route" id="route-finder"><h3>Which route fits my project?</h3><p class="panel-lede">Pick what you have and what you need. The answer follows handbook section 1 and workflows A–E.</p>
<form class="route-form" onsubmit="return false"><label>What do you have?<select id="route-input">${routes.inputs.map((x) => option(x.id, x.label)).join('')}</select></label><label>What do you need?<select id="route-goal">${routes.goals.map((x) => option(x.id, x.label)).join('')}</select></label></form>
<div id="route-out" aria-live="polite"></div></div>
<div id="calc-grid"></div>
</section>
${photoWorkspace}
${cadWorkspace}
<section class="panel" id="sources" role="tabpanel" aria-labelledby="tab-sources" tabindex="-1" hidden>
<div class="catalog-head"><div><h2>The source library</h2><p>Official guides, primary research, geometry resources, and implementation projects. Each entry has a use case, a limitation, and the depth of review. Press <kbd>/</kbd> to search.</p></div><a href="REFERENCES.md" class="download" download>Markdown directory</a></div>
<details class="catalog-coverage"><summary>Explore catalog coverage and review depth</summary>${composition}</details>
<div class="filters"><label>Search the catalog<input id="search" type="search" placeholder="Try: FreeCAD, calibration, NURBS, anatomy…" autocomplete="off"></label><label>Topic<select id="category"><option value="">All topics</option>${categories.map((c) => option(c)).join('')}</select></label><label>Review depth<select id="depth"><option value="">Any depth</option>${option('strong', 'Page or document read')}${option('medium', 'Search index or metadata')}${option('limited', 'Abstract or bibliographic')}</select></label><label>Level<select id="level"><option value="">Any level</option>${levels.map((l) => option(l)).join('')}</select></label><label>Sort<select id="sort">${option('default', 'Catalog order')}${option('title', 'Title A–Z')}${option('depth', 'Deepest review first')}${option('push', 'Most recent repository push')}</select></label></div>
<div class="chips" role="group" aria-label="Filter by topic">${chips}</div>
<div class="result-row"><div id="result-count" role="status" aria-live="polite" aria-atomic="true"></div><button type="button" class="linkish" id="reset-filters">Clear filters</button></div>
<div class="cards">${cards}</div><div id="empty" class="empty" hidden><p>No matching sources. Try a shorter search or fewer filters.</p><button type="button" class="ghost" id="reset-empty">Show all sources</button></div></section>
<section class="panel" id="github" role="tabpanel" aria-labelledby="tab-github" tabindex="-1" hidden><article class="prose">${gh}</article></section>
<section class="panel" id="research" role="tabpanel" aria-labelledby="tab-research" tabindex="-1" hidden><article class="prose">${research}</article></section>
<section class="panel" id="worksheets" role="tabpanel" aria-labelledby="tab-worksheets" tabindex="-1" hidden><article class="prose"><h1>Make the process repeatable.</h1><p>Use these templates to connect observations, modeling decisions, and print acceptance. Empty measurements mean unknown, never zero. <code>python3 -m cadkit new-project</code> copies them into a fresh project folder.</p><div class="resources"><a href="templates/measurement-register.csv" download>Measurement CSV</a><a href="templates/assumptions-register.csv" download>Assumptions CSV</a><a href="templates/validation-results.csv" download>Validation CSV</a><a href="templates/design-parameters.csv" download>Design-parameter CSV</a><a href="templates/independent-checks.csv" download>Independent-check CSV</a></div>${worksheets}<h2>Synthetic two-hole plate</h2><p>Teaching geometry: 60 × 30 × 4 mm, with two 5 mm holes spaced 40 mm apart. One parameter register drives the OpenSCAD model; <code>examples/build_plate.py</code> renders it and checks the STL against design rules. No real object or physical print was tested.</p><img class="example" src="examples/two-hole-plate.svg" alt="Dimensioned teaching diagram of a rectangular two-hole plate" loading="lazy"><div class="resources">${exampleLinks}</div></article></section>
</main>
<footer class="footer">Revision ${lib.revision} · ${sources.length} curated resources · ${repos.length} repository snapshots · ${calculators.length} calculators · Original explanations and synthetic examples. No reconstruction benchmark or physical printing qualification is implied.</footer>
<button id="to-top" type="button" aria-label="Back to top" hidden>↑</button>
<script type="application/json" id="library-data">${jsonForScript(libraryData)}</script>
<script>
${js}</script>
</body>
</html>
`;
write('index.html', html);
const info = {
  revision: lib.revision, sources: sources.length, repositories: repos.length, categories: categories.length,
  handbook_sections: toc.length, calculators: calculators.length, figures: figureCount,
  route_inputs: routes.inputs.length, route_goals: routes.goals.length, html_bytes: Buffer.byteLength(html),
};
write('tmp/build-info.json', JSON.stringify(info, null, 2) + '\n');
console.log(JSON.stringify(info));
