// Optional network check of every catalog URL and every external link in the Markdown docs.
//
//   node scripts/check-links.mjs [--concurrency 6] [--timeout 20000]
//
// Writes tmp/qa/link-check.json. Exit code is non-zero only for "broken" results
// (DNS failure, or any HTTP 4xx/5xx other than 401/403/429). Those three are recorded as "blocked": many publishers
// refuse automated clients, which says nothing about whether a person can open the page.
// Connection timeouts and resets are retried once and then recorded as "timeout" (transient).
import fs from 'node:fs';
import path from 'node:path';
import { ROOT, readJSON, write } from './lib/runtime.mjs';

const arg = (name, fallback) => {
  const i = process.argv.indexOf(name);
  if (i < 0) return fallback;
  const v = Number(process.argv[i + 1]);
  if (!Number.isInteger(v) || v < 1) { console.error(`${name} needs a positive whole number`); process.exit(2); }
  return v;
};
const concurrency = arg('--concurrency', 6);
const timeout = arg('--timeout', 20000);

const urls = new Map();
for (const s of readJSON('sources.json')) urls.set(s.url, new Set([`sources.json#${s.id}`]));
const docs = ['HANDBOOK.md', 'RESEARCH-NOTES.md', 'BUILD.md', 'README.md', 'CONTRIBUTING.md', 'cadkit/README.md', 'examples/README.md'];
for (const doc of docs) {
  const file = path.join(ROOT, doc);
  if (!fs.existsSync(file)) continue;
  for (const [, url] of fs.readFileSync(file, 'utf8').matchAll(/\]\((https:\/\/[^)\s]+)\)/g)) {
    if (!urls.has(url)) urls.set(url, new Set());
    urls.get(url).add(doc);
  }
}

async function probe(url) {
  const attempt = async (method) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const res = await fetch(url, {
        method, redirect: 'follow', signal: controller.signal,
        headers: { 'User-Agent': 'Mozilla/5.0 (compatible; cad-reference-linkcheck/1.0)', Accept: 'text/html,application/pdf,*/*' },
      });
      res.body?.cancel?.();
      return { status: res.status, final_url: res.url };
    } finally { clearTimeout(timer); }
  };
  const TRANSIENT = new Set(['UND_ERR_CONNECT_TIMEOUT', 'UND_ERR_HEADERS_TIMEOUT', 'UND_ERR_SOCKET', 'ETIMEDOUT', 'ECONNRESET', 'EAI_AGAIN']);
  let last;
  for (let tryNo = 1; tryNo <= 2; tryNo++) { // one retry: transient network errors are common
    try {
      let r = await attempt('HEAD');
      if (r.status >= 400 || r.status === 0) r = await attempt('GET'); // many servers mishandle HEAD
      const verdict = r.status < 400 ? 'ok' : [401, 403, 429].includes(r.status) ? 'blocked' : 'broken';
      return { url, ...r, verdict, attempts: tryNo };
    } catch (error) {
      const code = String(error.cause?.code || error.message);
      const transient = error.name === 'AbortError' || TRANSIENT.has(code);
      last = { url, status: 0, verdict: transient ? 'timeout' : 'broken', error: error.name === 'AbortError' ? `timeout after ${timeout} ms` : code, attempts: tryNo };
      if (!transient) break;
    }
  }
  return last;
}

const queue = [...urls.keys()]; const results = [];
await Promise.all(Array.from({ length: concurrency }, async () => {
  while (queue.length) results.push(await probe(queue.shift()));
}));
results.sort((a, b) => a.url.localeCompare(b.url));
for (const r of results) r.referenced_by = [...urls.get(r.url)];

const count = (v) => results.filter((r) => r.verdict === v).length;
const summary = {
  checked_at: new Date().toISOString(),
  total: results.length, ok: count('ok'), blocked: count('blocked'), timeout: count('timeout'), broken: count('broken'),
  not_ok: results.filter((r) => r.verdict !== 'ok').map(({ url, status, verdict, error, referenced_by }) => ({ url, status, verdict, error, referenced_by })),
};
write('tmp/qa/link-check.json', JSON.stringify({ summary, results }, null, 2) + '\n');
console.log(JSON.stringify(summary, null, 2));
if (summary.broken) process.exitCode = 1;
