// Refresh the GitHub metadata snapshot stored in sources.json.
//
//   node scripts/refresh-github.mjs            # dry run: print what would change
//   node scripts/refresh-github.mjs --write    # update sources.json
//
// Uses the public REST API. Set GITHUB_TOKEN (or GH_TOKEN) to raise the rate limit.
// Only metadata fields are touched: default_branch, last_push, archived, license_metadata, checked.
// Metadata is a snapshot, not a quality score; GITHUB.md says so in its preamble.
import { readJSON, writeJSON } from './lib/runtime.mjs';

const writeBack = process.argv.includes('--write');
const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
const today = new Date().toISOString().slice(0, 10);
const sources = readJSON('sources.json');
const repos = sources.filter((s) => s.type === 'GitHub repository');
const changes = []; const failures = [];

for (const s of repos) {
  const res = await fetch(`https://api.github.com/repos/${s.repository}`, {
    headers: {
      Accept: 'application/vnd.github+json',
      'User-Agent': 'pictures-to-printable-cad-reference-library',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) { failures.push({ id: s.id, status: res.status }); continue; }
  const repo = await res.json();
  const next = {
    default_branch: repo.default_branch,
    last_push: repo.pushed_at,
    archived: Boolean(repo.archived),
    license_metadata: repo.license?.spdx_id || 'none',
  };
  // A rename/transfer would silently change what the entry points at: report, never rewrite the URL.
  if (repo.full_name.toLowerCase() !== s.repository.toLowerCase()) {
    failures.push({ id: s.id, status: `moved to ${repo.full_name}` });
  }
  const diff = Object.entries(next).filter(([k, v]) => s[k] !== v).map(([k, v]) => ({ field: k, from: s[k], to: v }));
  if (diff.length) changes.push({ id: s.id, diff });
  if (writeBack) Object.assign(s, next, { checked: today });
}

if (writeBack && failures.length === 0) writeJSON('sources.json', sources);
console.log(JSON.stringify({ repositories: repos.length, changed: changes.length, changes, failures, written: writeBack && failures.length === 0 }, null, 2));
if (failures.length) process.exitCode = 1;
