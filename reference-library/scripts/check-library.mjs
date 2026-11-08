// End-to-end check of index.html in a real browser (Playwright + Chrome/Chromium).
//
//   node scripts/check-library.mjs
//
// Opens the page from file:// by default, or a private loopback HTTP server when
// CAD_REFERENCE_BROWSER_TRANSPORT=http. Exercises every tab, the
// catalog filters and their URL state, the Toolkit calculators and route finder, the
// theme toggle, deep links, and desktop/mobile layouts. Writes screenshots and
// tmp/qa/browser-check.json. It does not visit external websites (see check-links.mjs).
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { ROOT, requireModule, findChrome, readJSON, validateSources } from './lib/runtime.mjs';

const { chromium } = requireModule('playwright');
const sources = readJSON('sources.json');
const calculators = readJSON('assets/data/calculators.json');
const routes = readJSON('assets/data/routes.json');
const lib = readJSON('library.json');
const results = { checks: [] };
const qaFile = path.join(ROOT, 'tmp/qa/browser-check.json');
const transport = process.env.CAD_REFERENCE_BROWSER_TRANSPORT || 'file';
let browser;
let server;
let pageUrl;
const assert = (condition, message) => {
  if (!condition) throw new Error('FAILED: ' + message);
  results.checks.push(message);
};
// Never leave an earlier "passed" record behind a failing run.
fs.mkdirSync(path.dirname(qaFile), { recursive: true });
fs.rmSync(qaFile, { force: true });

// Serve only published reader content. Never expose scripts, dependencies,
// environment files, or the parent repository; realpath also excludes symlinks
// escaping the library. The two Python examples are downloadable source text.
const publishedFiles = new Set([
  'index.html', 'HANDBOOK.md', 'REFERENCES.md', 'sources.csv', 'cadkit/README.md',
  'examples/build_plate.py', 'examples/calculate.py', 'examples/calculation-results.json',
  'examples/clearance-coupon.scad', 'examples/plate-parameters.csv',
  'examples/two-hole-plate.scad', 'examples/two-hole-plate.svg',
  'output/pdf/pictures-to-printable-cad.pdf',
]);
const mimeTypes = {
  '.html': 'text/html; charset=utf-8', '.svg': 'image/svg+xml',
  '.pdf': 'application/pdf', '.json': 'application/json', '.csv': 'text/csv; charset=utf-8',
};
function servePublishedFile(request, response) {
  if (!['GET', 'HEAD'].includes(request.method)) {
    response.writeHead(405, { Allow: 'GET, HEAD' }).end();
    return;
  }
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const relative = pathname === '/' ? 'index.html' : pathname.slice(1);
    const allowed = publishedFiles.has(relative)
      || /^assets\/figures\/[a-z0-9-]+\.svg$/.test(relative)
      || /^templates\/[a-zA-Z0-9-]+\.(md|csv)$/.test(relative);
    if (!allowed) { response.writeHead(404).end(); return; }
    const realFile = fs.realpathSync(path.join(ROOT, relative));
    if (!realFile.startsWith(fs.realpathSync(ROOT) + path.sep) || !fs.statSync(realFile).isFile()) {
      response.writeHead(404).end(); return;
    }
    const body = fs.readFileSync(realFile);
    response.writeHead(200, {
      'Content-Type': mimeTypes[path.extname(realFile)] || 'text/plain; charset=utf-8',
      'Content-Length': body.length, 'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
    });
    response.end(request.method === 'HEAD' ? undefined : body);
  } catch {
    response.writeHead(404).end();
  }
}

try {
if (!['file', 'http'].includes(transport)) {
  throw new Error('CAD_REFERENCE_BROWSER_TRANSPORT must be file or http.');
}

const problems = validateSources(sources);
assert(problems.length === 0, 'catalog passes schema validation' + (problems.length ? ': ' + problems.join('; ') : ''));
const repos = sources.filter((s) => s.type === 'GitHub repository');
const categoryCount = (c) => sources.filter((s) => s.category === c).length;

const qa = path.join(ROOT, 'tmp/qa');
fs.mkdirSync(qa, { recursive: true });
pageUrl = pathToFileURL(path.join(ROOT, 'index.html')).href;
if (transport === 'http') {
  server = http.createServer(servePublishedFile);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  pageUrl = `http://127.0.0.1:${server.address().port}/index.html`;
}
browser = await chromium.launch({ headless: true, executablePath: findChrome() });
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
const page = await context.newPage();
const errors = []; const dialogs = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
page.on('dialog', async (d) => { dialogs.push(d.message()); await d.dismiss(); });

// ---- handbook, local links, figures ---------------------------------------------
await page.goto(pageUrl);
await page.screenshot({ path: path.join(qa, 'desktop.png') });
assert(await page.locator('#handbook').isVisible(), 'handbook is the initial tab');
const tocCount = await page.locator('.contents a').count();
const sectionCount = (fs.readFileSync(path.join(ROOT, 'HANDBOOK.md'), 'utf8').match(/^## /gm) || []).length;
assert(tocCount === sectionCount, `contents lists all ${sectionCount} handbook chapters`);
const localRefs = await page.evaluate(() => [
  ...[...document.querySelectorAll('a[href]')].map((e) => e.getAttribute('href')),
  ...[...document.querySelectorAll('img[src]')].map((e) => e.getAttribute('src')),
].filter((h) => h && !/^(https:|#|data:|mailto:)/.test(h)));
const uniqueLocal = [...new Set(localRefs)];
for (const ref of uniqueLocal) assert(fs.existsSync(path.resolve(ROOT, decodeURIComponent(ref.split('#')[0]))), 'local file exists: ' + ref);
const anchors = await page.evaluate(() => [...document.querySelectorAll('a[href^="#"]')].map((a) => a.getAttribute('href').slice(1)).filter(Boolean));
const missingAnchors = await page.evaluate((ids) => ids.filter((id) => !document.getElementById(id.split('?')[0])), [...new Set(anchors)]);
assert(missingAnchors.length === 0, 'every in-page link has a target' + (missingAnchors.length ? ': ' + missingAnchors.join(', ') : ''));
await page.evaluate(() => Promise.all([...document.images].map((img) => { img.loading = 'eager'; return img.decode().catch(() => {}); })));
const brokenImages = await page.evaluate(() => [...document.images].filter((i) => !(i.complete && i.naturalWidth > 0)).map((i) => i.getAttribute('src')));
assert(brokenImages.length === 0, 'all figures and images load' + (brokenImages.length ? ': ' + brokenImages.join(', ') : ''));
const figureCount = await page.locator('.prose figure.fig').count();
assert(figureCount >= 8, `handbook shows ${figureCount} captioned figures`);

// ---- tabs: click, keyboard, deep links ------------------------------------------------
await page.getByRole('tab', { name: /Handbook/ }).focus();
await page.keyboard.press('ArrowRight');
assert(await page.locator('#toolkit').isVisible(), 'ArrowRight moves from Handbook to Toolkit');
assert(page.url().endsWith('#toolkit'), 'active tab is reflected in the URL hash');
await page.keyboard.press('End');
assert(await page.locator('#worksheets').isVisible(), 'End key selects the last tab');
await page.goto(pageUrl + '#calc-depth');
assert(await page.locator('#toolkit').isVisible() && await page.locator('#calc-depth').isVisible(), 'deep link #calc-depth opens the Toolkit at that calculator');
const chapter = await page.locator('.contents a').nth(10).getAttribute('href');
await page.goto(pageUrl + chapter);
assert(await page.locator('#handbook').isVisible(), 'deep link to a handbook chapter opens the handbook');

// ---- toolkit ------------------------------------------------------------------------------
await page.goto(pageUrl + '#toolkit');
assert(await page.locator('.calc').count() === calculators.length, `all ${calculators.length} calculators render`);
for (const c of calculators) assert(await page.locator(`#calc-${c.id}`).count() === 1, `calculator card #calc-${c.id}`);
assert(await page.locator('.calc .error').count() === 0, 'no calculator errors with default inputs');
const out = (id, label) => page.locator(`#calc-${id} dd[data-out="${label}"] strong`).textContent();
assert(await out('depth', 'Corrected size') === '44.8', 'depth calculator: 40 mm at Z 500, Δ 60 → 44.8 mm');
assert(await out('chord', 'Minimum segments n') === '50', 'chord calculator: R 10, e 0.02 → 50 segments');
assert(await out('uncertainty', 'Standard uncertainty u(L)') === '0.123', 'uncertainty calculator: u(L) = 0.123 mm');
assert(await out('camera', 'Distance to reference Z') === '600.93', 'camera calculator: Z ≈ 601 mm');
assert(await out('units', 'Most likely') === 'file units are m', 'unit detective: 0.06 vs 60 mm → metres');
assert(Number(await out('homography', 'RMS residual')) < 0.01, 'homography calculator fits the default points');
await page.fill('#in-depth-z', '0');
assert(await page.locator('#calc-depth .error').isVisible(), 'invalid input shows an error instead of a number');
await page.locator('#calc-depth [data-action="reset"]').click();
assert(await out('depth', 'Corrected size') === '44.8', 'reset restores the defaults');
await page.fill('#in-uncertainty-up', '');
assert((await page.locator('#calc-uncertainty .error').textContent()).includes('needs a number'), 'an empty field is reported, never treated as zero');
await page.locator('#calc-uncertainty [data-action="reset"]').click();
await page.fill('#in-depth-size', '-40');
assert(await page.locator('#calc-depth .error').isVisible(), 'a negative size is rejected');
await page.locator('#calc-depth [data-action="reset"]').click();
await page.fill('#in-units-observed', '0.064');
assert((await page.locator('#calc-units .warn').textContent()).includes('within 5 %'), 'unit detective warns at the same 5 % threshold as the CLI');
await page.locator('#calc-units [data-action="reset"]').click();
await page.fill('#in-homography-pairs', '0 0 0 0\n\n# comment\nnot a pair');
assert((await page.locator('#calc-homography .error').textContent()).includes('Line 4'), 'homography errors report the real line number');
await page.locator('#calc-homography [data-action="reset"]').click();
await page.fill('#in-scale-pref', '150');
assert(await page.locator('#calc-scale .warn li').count() >= 1 && await page.locator('#calc-scale').getAttribute('data-state') === 'warn', 'a short reference raises a warning');
await page.fill('#in-homography-pairs', '0 0 0 0\n10 0 5 0\n10 10 5 5\n0 10 0 5');
assert((await page.locator('#calc-homography .warn').textContent()).includes('zero by construction'), 'four-point homography warns that residuals mean nothing');
await page.selectOption('#route-input', 'photo-set');
await page.selectOption('#route-goal', 'editable');
assert(await page.locator('.route-steps li').count() === 2, 'route finder: photo set + editable → two workflows');
assert((await page.locator('#route-out').textContent()).includes('Workflow D'), 'route finder names Workflow D');
await page.selectOption('#route-goal', 'holder');
assert((await page.locator('.route-badge').first().textContent()) === 'H', 'route finder: holder goal leads with the held-object section');
await page.screenshot({ path: path.join(qa, 'toolkit.png'), fullPage: false });
await page.locator('#route-out a.chip').first().click();
assert(page.url().includes('#calc-'), 'route finder links jump to a calculator');

// ---- catalog ---------------------------------------------------------------------------------
await page.goto(pageUrl + '#sources');
assert(await page.locator('.source:visible').count() === sources.length, `all ${sources.length} sources visible`);
await page.getByLabel('Search the catalog').fill('FreeCAD');
const freecad = await page.locator('.source:visible').count();
assert(freecad > 0 && freecad < sources.length, 'search filters resources');
assert(page.url().includes('#sources?q=FreeCAD'), 'search state is written to the URL');
await page.reload();
assert(await page.getByLabel('Search the catalog').inputValue() === 'FreeCAD' && await page.locator('.source:visible').count() === freecad, 'reload restores the search from the URL');
await page.getByLabel('Search the catalog').fill('not-a-real-resource-zzzz');
assert(await page.locator('.source:visible').count() === 0 && await page.locator('#empty').isVisible(), 'empty search feedback');
await page.locator('#reset-filters').click();
await page.locator('#category').selectOption('Advanced geometry');
const advanced = await page.locator('.source:visible').count();
assert(advanced === categoryCount('Advanced geometry'), 'topic filter');
await page.locator('#category').selectOption('');
await page.locator('.chip[data-topic="Research literature"]').click();
assert(await page.locator('.source:visible').count() === categoryCount('Research literature'), 'topic chip filters');
await page.locator('.chip[data-topic="Research literature"]').click();
await page.locator('#depth').selectOption('limited');
const limited = sources.filter((s) => ['abstract', 'discovery-abstract', 'metadata'].includes(s.evidence)).length;
assert(await page.locator('.source:visible').count() === limited, 'review-depth filter');
await page.locator('#depth').selectOption('');
await page.locator('#sort').selectOption('push');
assert(await page.locator('.source').first().getAttribute('data-push') !== '', 'sort by repository push puts repositories first');
await page.screenshot({ path: path.join(qa, 'catalog.png') });
// Topics containing "&" and searches containing "+" or "&" survive a reload (URL-encoded state).
await page.locator('#reset-filters').click();
await page.locator('.chip[data-topic="CAD & drawings"]').click();
await page.getByLabel('Search the catalog').fill('c++ a&b');
await page.getByLabel('Search the catalog').fill('');
await page.reload();
assert(await page.locator('#category').inputValue() === 'CAD & drawings' && await page.locator('.source:visible').count() === categoryCount('CAD & drawings'), 'a topic containing "&" is restored from the URL');
await page.getByLabel('Search the catalog').fill('c++ a&b');
await page.reload();
assert(await page.getByLabel('Search the catalog').inputValue() === 'c++ a&b', 'search text with "+" and "&" is restored from the URL');
await page.locator('#reset-filters').click();
await page.goto(pageUrl + '#%E0%A4%A');
assert(await page.locator('#handbook').isVisible(), 'a malformed hash falls back to the handbook without an error');
await page.goto(pageUrl + '#sources');
await page.getByRole('tab', { name: /Sources/ }).focus();
await page.keyboard.press('Control+/');
await page.getByRole('tab', { name: /Handbook/ }).click();
await page.getByRole('tab', { name: /Handbook/ }).focus();
await page.keyboard.press('Control+/');
assert(await page.locator('#handbook').isVisible(), 'Ctrl+/ does not trigger the search shortcut');
await page.keyboard.press('/');
assert(await page.locator('#sources').isVisible() && await page.evaluate(() => document.activeElement.id) === 'search', '/ jumps to the catalog search');
await page.getByRole('tab', { name: /GitHub/ }).click();
assert(await page.locator('#github h2').count() === repos.length + 1, `GitHub tab lists ${repos.length} repositories`);
await page.getByRole('tab', { name: /Worksheets/ }).click();
await page.locator('img.example').scrollIntoViewIfNeeded();
assert(await page.locator('img.example').evaluate(async (e) => { await e.decode().catch(() => {}); return e.complete && e.naturalWidth > 0; }), 'example SVG loads');
await page.screenshot({ path: path.join(qa, 'worksheets.png') });

// ---- hostile hash and theme --------------------------------------------------------------
await page.goto(pageUrl + '#' + encodeURIComponent('<img src=x onerror=alert(1)>'));
await page.goto(pageUrl + '#sources?q=' + encodeURIComponent('"><script>alert(2)</script>'));
assert(dialogs.length === 0 && await page.locator('#search').inputValue() === '"><script>alert(2)</script>', 'hash text is treated as data, never as HTML');
await page.goto(pageUrl);
await page.locator('#theme-toggle').click();
const theme = await page.evaluate(() => document.documentElement.dataset.theme);
await page.reload();
assert(await page.evaluate(() => document.documentElement.dataset.theme) === theme, 'theme choice persists across reloads');
await page.emulateMedia({ colorScheme: 'dark' });
await page.evaluate(() => { localStorage.clear(); delete document.documentElement.dataset.theme; });
await page.reload();
const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
assert(bg !== 'rgb(247, 246, 241)', 'dark color scheme changes the page background');
await page.goto(pageUrl + '#toolkit');
await page.screenshot({ path: path.join(qa, 'dark-toolkit.png') });
await page.emulateMedia({ colorScheme: 'light' });

// ---- mobile -------------------------------------------------------------------------------
await page.setViewportSize({ width: 390, height: 844 });
for (const tab of ['handbook', 'toolkit', 'sources', 'github', 'worksheets']) {
  await page.goto(pageUrl + '#' + tab);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert(overflow <= 1, `no horizontal page overflow on mobile: ${tab}`);
}
await page.goto(pageUrl);
await page.screenshot({ path: path.join(qa, 'mobile.png') });

assert(errors.length === 0, 'no JavaScript or console errors' + (errors.length ? ': ' + errors.join('; ') : ''));

Object.assign(results, {
  checked_at: new Date().toISOString(), revision: lib.revision, status: 'passed',
  transport, page_url: pageUrl,
  source_records: sources.length, unique_urls: new Set(sources.map((s) => s.url)).size, github_repositories: repos.length,
  handbook_chapters: tocCount, handbook_figures: figureCount, calculators: calculators.length,
  route_combinations: routes.inputs.length * routes.goals.length, local_files_checked: uniqueLocal.length,
  in_page_anchors_checked: new Set(anchors).size, freecad_search_results: freecad, advanced_geometry_results: advanced,
  browser_errors: errors, desktop_viewport: [1440, 1050], mobile_viewport: [390, 844],
  scope: `Local ${transport === 'http' ? 'loopback HTTP' : 'file'} navigation, tabs and deep links, catalog filters and URL state, calculators and route finder, theme, figures, local links, and overflow. External-page availability is checked separately by scripts/check-links.mjs.`,
});
results.check_count = results.checks.length;
fs.writeFileSync(qaFile, JSON.stringify(results, null, 2) + '\n');
console.log(JSON.stringify({ status: results.status, checks: results.check_count, calculators: results.calculators, figures: figureCount, local_files: uniqueLocal.length }, null, 2));
} catch (error) {
  fs.writeFileSync(qaFile, JSON.stringify({
    status: 'failed', revision: lib.revision, checked_at: new Date().toISOString(),
    transport, page_url: pageUrl, error: error.message, passed_before_failure: results.checks.length,
    scope: `Browser assertions using ${transport} transport; see error for the point of failure.`,
  }, null, 2) + '\n');
  console.error(error);
  process.exitCode = 1;
} finally {
  try {
    await browser?.close();
  } finally {
    if (server) {
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    }
  }
}
