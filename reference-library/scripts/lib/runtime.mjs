// Shared helpers for the library's Node scripts.
//
// Dependency resolution order (first hit wins):
//   1. reference-library/node_modules        (after `npm ci`)
//   2. $CAD_REFERENCE_NODE_MODULES            (any directory holding the packages)
//   3. the Codex bundled runtime used to author Revisions 1–2
// so the same scripts run on a fresh clone, in CI, or on the original machine.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const CODEX_MODULES = path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');

const require = createRequire(path.join(ROOT, 'package.json'));

export function moduleSearchPaths() {
  return [path.join(ROOT, 'node_modules'), process.env.CAD_REFERENCE_NODE_MODULES, CODEX_MODULES]
    .filter(Boolean)
    .filter((p) => fs.existsSync(p));
}

export function resolveModule(name) {
  for (const dir of moduleSearchPaths()) {
    try {
      return require.resolve(name, { paths: [dir] });
    } catch { /* try the next location */ }
  }
  throw new Error(
    `Cannot find the Node package "${name}". Run \`npm ci\` in ${ROOT}, ` +
    'or set CAD_REFERENCE_NODE_MODULES to a node_modules directory that contains it.'
  );
}

export async function importModule(name) {
  return import(pathToFileURL(resolveModule(name)).href);
}

export function requireModule(name) {
  return require(resolveModule(name));
}

/** Locate a Chrome/Chromium executable, or return undefined to let Playwright use its own. */
export function findChrome() {
  if (process.env.CAD_REFERENCE_CHROME) return process.env.CAD_REFERENCE_CHROME;
  const candidates = [
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/snap/bin/chromium', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
  ];
  return candidates.find((p) => fs.existsSync(p));
}

export const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');
export const readJSON = (p) => JSON.parse(read(p));
export function write(p, data) {
  const target = path.join(ROOT, p);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, data);
}
export const writeJSON = (p, value) => write(p, JSON.stringify(value, null, 2) + '\n');

export const esc = (s) => String(s ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#39;');

/** Stable, readable heading slugs: "6. Workflow A: one picture" -> "6-workflow-a-one-picture". */
export function slugify(text) {
  return String(text)
    .replace(/<[^>]+>/g, '')
    .replace(/&[a-z#0-9]+;/gi, ' ')
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64)
    .replace(/-+$/g, '') || 'section';
}

/** Review-depth labels, strongest first. `rank` drives catalog sorting and badge colour. */
export const EVIDENCE = {
  page: { label: 'Page content checked', rank: 1, strength: 'strong' },
  'page-http-gzip-decoded': { label: 'Page content checked via HTTP', rank: 1, strength: 'strong' },
  'repository-content': { label: 'Repository document read', rank: 1, strength: 'strong' },
  'search-content': { label: 'Search-index content checked', rank: 2, strength: 'medium' },
  'repository-metadata': { label: 'Repository metadata checked', rank: 2, strength: 'medium' },
  abstract: { label: 'Abstract / scholarly record', rank: 3, strength: 'limited' },
  'discovery-abstract': { label: 'Discovery abstract only', rank: 4, strength: 'limited' },
  metadata: { label: 'Bibliographic metadata only', rank: 4, strength: 'limited' },
};

export const REQUIRED_FIELDS = ['id', 'category', 'title', 'url', 'type', 'level', 'use', 'limit', 'evidence', 'checked'];
export const REPO_FIELDS = ['repository', 'license_metadata', 'archived', 'last_push', 'default_branch'];

/** Catalog validation shared by the builder, the browser check, and the Node tests. */
export function validateSources(sources) {
  const problems = [];
  const ids = new Set(); const urls = new Set();
  sources.forEach((s, i) => {
    const where = `entry ${i} (${s.id ?? 'no id'})`;
    for (const f of REQUIRED_FIELDS) if (!String(s[f] ?? '').trim()) problems.push(`${where}: missing ${f}`);
    if (ids.has(s.id)) problems.push(`${where}: duplicate id`); ids.add(s.id);
    if (urls.has(s.url)) problems.push(`${where}: duplicate url`); urls.add(s.url);
    if (s.url && !String(s.url).startsWith('https://')) problems.push(`${where}: url must use https`);
    if (s.url && /[?&]utm_[a-z]+=/i.test(s.url)) problems.push(`${where}: url carries a utm_ tracking parameter`);
    if (s.evidence && !EVIDENCE[s.evidence]) problems.push(`${where}: unknown evidence "${s.evidence}"`);
    if (s.checked && !/^\d{4}-\d{2}-\d{2}$/.test(s.checked)) problems.push(`${where}: checked must be YYYY-MM-DD`);
    if (s.type === 'GitHub repository') {
      for (const f of REPO_FIELDS) if (s[f] === undefined || s[f] === '') problems.push(`${where}: GitHub entry missing ${f}`);
      if (s.repository && !String(s.url).toLowerCase().endsWith('/' + String(s.repository).toLowerCase())) {
        problems.push(`${where}: repository ${s.repository} does not match url`);
      }
    }
  });
  return problems;
}
