import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Buffer } from 'node:buffer';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, symlinkSync, unlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { frontendBuildInfo, frontendSourceFingerprint } from '../../scripts/frontendBuildInfo.ts';

const inputs: Record<string, string> = {
  'frontend/src/main.tsx': 'export const app = "fixture";',
  'frontend/src/é.ts': 'export const accent = true;',
  'frontend/src/😀.ts': 'export const face = true;',
  'frontend/index.html': '<div id="root"></div>',
  'frontend/vite.config.ts': 'export default {};',
  'frontend/tsconfig.json': '{"compilerOptions":{}}',
  'scripts/frontendBuildInfo.ts': 'fixture metadata helper',
  'frontend/public/sample.png': 'fixture source image',
  'package.json': '{"name":"fixture"}',
  'package-lock.json': '{"lockfileVersion":3}',
};
function write(root: string, relative: string, bytes: string) {
  mkdirSync(dirname(join(root, relative)), { recursive: true });
  writeFileSync(join(root, relative), bytes);
}
function fixture(t: { after: (cleanup: () => void) => void }, reversed = false) {
  const root = mkdtempSync(join(tmpdir(), 'picad-build-info-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const entries = Object.entries(inputs);
  for (const [relative, bytes] of reversed ? entries.reverse() : entries)
    write(root, relative, bytes);
  return root;
}

test('input fingerprints use UTF-8 paths and length framing independently of checkout location or creation order', (t) => {
  const first = fixture(t),
    second = fixture(t, true);
  const oracle = createHash('sha256');
  oracle.update('picad-frontend-inputs-v1\0');
  for (const relative of Object.keys(inputs).sort((a, b) =>
    Buffer.compare(Buffer.from(a), Buffer.from(b)),
  )) {
    const name = Buffer.from(relative),
      bytes = Buffer.from(inputs[relative]);
    for (const value of [name, bytes]) {
      const length = Buffer.alloc(8);
      length.writeBigUInt64BE(BigInt(value.length));
      oracle.update(length).update(value);
    }
  }
  const expected = oracle.digest('hex');
  assert.equal(frontendSourceFingerprint(first), expected);
  assert.equal(frontendSourceFingerprint(second), expected);
});

test('source, configuration, helper, fixed assets and lockfile edits change the input fingerprint', (t) => {
  const root = fixture(t);
  const original = frontendSourceFingerprint(root);
  for (const path of Object.keys(inputs)) {
    write(root, path, `${inputs[path]} changed`);
    assert.notEqual(frontendSourceFingerprint(root), original, path);
    write(root, path, inputs[path]);
    assert.equal(frontendSourceFingerprint(root), original);
  }
  unlinkSync(join(root, 'frontend/public/sample.png'));
  assert.notEqual(
    frontendSourceFingerprint(root),
    original,
    'deleting a fixed source asset changes the fingerprint',
  );
  write(root, 'frontend/public/sample.png', inputs['frontend/public/sample.png']);
  write(root, 'frontend/src/a', 'bc');
  const framed = frontendSourceFingerprint(root);
  unlinkSync(join(root, 'frontend/src/a'));
  write(root, 'frontend/src/ab', 'c');
  assert.notEqual(
    frontendSourceFingerprint(root),
    framed,
    'path/content boundaries cannot collide',
  );
});

test('outputs, dependencies, user directories and non-allowlisted public files are excluded', (t) => {
  const root = fixture(t),
    original = frontendSourceFingerprint(root);
  for (const path of [
    'frontend/dist/build-info.json',
    'frontend/dist/assets/app.js',
    'node_modules/package/index.js',
    'frontend/node_modules/package/index.js',
    'frontend/src/node_modules/package.ts',
    'frontend/src/dist/generated.ts',
    '.local/jobs/private.txt',
    'photos/private.jpg',
    'frontend/public/uploads/private.png',
    'frontend/public/not-a-repository-asset.png',
  ])
    write(root, path, 'Excluded fixture data.');
  assert.equal(frontendSourceFingerprint(root), original);
});

test('file and directory symlinks are excluded, including public-directory ancestors', (t) => {
  const root = fixture(t),
    outside = fixture(t);
  const original = frontendSourceFingerprint(root);
  symlinkSync(join(outside, 'package.json'), join(root, 'frontend/src/linked.ts'));
  symlinkSync(join(outside, 'frontend/src'), join(root, 'frontend/src/linked-directory'), 'dir');
  assert.equal(frontendSourceFingerprint(root), original);
  rmSync(join(root, 'frontend/public'), { recursive: true });
  const withoutPublic = frontendSourceFingerprint(root);
  symlinkSync(join(outside, 'frontend/public'), join(root, 'frontend/public'), 'dir');
  assert.equal(frontendSourceFingerprint(root), withoutPublic);
});

test('missing Git gives explicit nulls without publishing paths, branch names or error text', (t) => {
  const root = fixture(t);
  const result = frontendBuildInfo(root, () => {
    throw new Error(`private-branch ${root}`);
  });
  assert.deepEqual(Object.keys(result), ['schema', 'revision', 'dirty', 'source_sha256']);
  assert.equal(result.schema, 1);
  assert.equal(result.revision, null);
  assert.equal(result.dirty, null);
  const invalid = frontendBuildInfo(root, () => 'not-a-revision');
  assert.equal(invalid.revision, null);
  assert.equal(invalid.dirty, null);
  assert.match(result.source_sha256!, /^[a-f0-9]{64}$/);
  assert.doesNotMatch(JSON.stringify(result), /private-branch|picad-build-info-/);
  const incomplete = mkdtempSync(join(tmpdir(), 'picad-build-info-empty-'));
  t.after(() => rmSync(incomplete, { recursive: true, force: true }));
  assert.equal(frontendSourceFingerprint(incomplete), null);
});

test('a failed Git status does not pair a known revision with an unknown dirty state', (t) => {
  const root = fixture(t);
  const commands: string[][] = [];
  const result = frontendBuildInfo(root, (args, cwd, timeout) => {
    assert.equal(cwd, root);
    assert.ok(timeout > 0 && timeout <= 750);
    commands.push(args);
    if (args.includes('rev-parse')) return `${'a'.repeat(40)}\n`;
    throw new Error('Status unavailable.');
  });
  assert.equal(commands.length, 2);
  assert.equal(commands[1].includes('--untracked-files=normal'), true);
  assert.equal(commands[1].includes('--'), false, 'status has no frontend-only pathspec');
  assert.equal(result.revision, null);
  assert.equal(result.dirty, null);
});

test('real Git metadata reports non-frontend edits and untracked files across the full worktree', (t) => {
  const root = fixture(t);
  const run = (args: string[]) =>
    execFileSync('git', args, { cwd: root, timeout: 2000, stdio: 'pipe', encoding: 'utf8' });
  try {
    run(['--version']);
  } catch {
    t.skip(
      'Git cannot be launched in this environment (missing binary or subprocess restriction).',
    );
    return;
  }
  run(['init', '-q']);
  write(root, 'backend/app.py', 'tracked backend fixture');
  run(['add', '.']);
  run([
    '-c',
    'user.name=Build fixture',
    '-c',
    'user.email=fixture@example.invalid',
    'commit',
    '-qm',
    'fixture',
  ]);
  const clean = frontendBuildInfo(root);
  assert.match(clean.revision!, /^[a-f0-9]{40}$/);
  assert.equal(clean.dirty, false);
  write(root, 'backend/app.py', 'backend changed');
  const changed = frontendBuildInfo(root);
  assert.equal(changed.dirty, true);
  assert.equal(changed.source_sha256, clean.source_sha256);
  write(root, 'backend/app.py', 'tracked backend fixture');
  write(root, 'untracked-fixture.txt', 'untracked source fixture');
  assert.equal(frontendBuildInfo(root).dirty, true);
});
