import { Buffer } from 'node:buffer';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstatSync, readFileSync, readdirSync } from 'node:fs';
import { join, posix } from 'node:path';

export type FrontendBuildInfo = {
  schema: 1;
  revision: string | null;
  dirty: boolean | null;
  source_sha256: string | null;
};

const FIXED_INPUTS = [
  'frontend/index.html',
  'frontend/vite.config.ts',
  'frontend/tsconfig.json',
  'scripts/frontendBuildInfo.ts',
  'package.json',
  'package-lock.json',
  ...[
    'favicon.svg',
    'metal-texture.png',
    'moon-map.png',
    'moon-elevation.tif',
    'sample.png',
    'relief-sample.png',
    'relief-sample-depth.png',
  ].map((name) => `frontend/public/${name}`),
];
const SKIPPED_DIRECTORIES = new Set(['node_modules', 'dist', '.git']);
const MAX_FILES = 10000;
const MAX_BYTES = 128 * 1024 * 1024;

function safeEntry(root: string, relative: string) {
  let current = root;
  let entry;
  for (const part of relative.split('/')) {
    current = join(current, part);
    try {
      entry = lstatSync(current);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null;
      throw error;
    }
    if (entry.isSymbolicLink()) return null;
  }
  return entry ?? null;
}

/** Diagnostic input fingerprint, not a checksum or attestation of the generated bundle. */
export function frontendSourceFingerprint(root: string): string | null {
  try {
    if (!safeEntry(root, 'frontend/src')?.isDirectory()) return null;
    const paths: string[] = [];
    let entries = 0;
    function walk(relative: string) {
      for (const entry of readdirSync(join(root, relative), { withFileTypes: true })) {
        if (++entries > MAX_FILES) throw new Error('Input limit exceeded.');
        if (entry.isSymbolicLink()) continue;
        const child = posix.join(relative, entry.name);
        if (entry.isDirectory()) {
          if (!SKIPPED_DIRECTORIES.has(entry.name)) walk(child);
        } else if (entry.isFile()) paths.push(child);
        if (paths.length > MAX_FILES) throw new Error('Input limit exceeded.');
      }
    }
    walk('frontend/src');
    for (const relative of FIXED_INPUTS)
      if (safeEntry(root, relative)?.isFile()) paths.push(relative);
    if (paths.length > MAX_FILES) return null;
    paths.sort((left, right) => Buffer.compare(Buffer.from(left), Buffer.from(right)));
    const hash = createHash('sha256').update('picad-frontend-inputs-v1\0');
    let total = 0;
    const length = Buffer.alloc(8);
    for (const relative of paths) {
      const size = safeEntry(root, relative)?.size;
      if (size === undefined || total + size > MAX_BYTES) return null;
      const bytes = readFileSync(join(root, relative));
      total += bytes.length;
      if (total > MAX_BYTES) return null;
      const name = Buffer.from(relative, 'utf8');
      length.writeBigUInt64BE(BigInt(name.length));
      hash.update(length).update(name);
      length.writeBigUInt64BE(BigInt(bytes.length));
      hash.update(length).update(bytes);
    }
    return hash.digest('hex');
  } catch {
    return null;
  }
}

type GitReader = (args: string[], root: string, timeout: number) => string;
const readGit: GitReader = (args, root, timeout) =>
  execFileSync('git', args, {
    cwd: root,
    timeout,
    maxBuffer: 1024 * 1024,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
    windowsHide: true,
  });

export function frontendBuildInfo(root: string, git: GitReader = readGit): FrontendBuildInfo {
  let revision: string | null = null;
  let dirty: boolean | null = null;
  try {
    const deadline = Date.now() + 750;
    const invoke = (args: string[]) => {
      const remaining = deadline - Date.now();
      if (remaining <= 0) throw new Error('Git time budget exhausted.');
      return git(
        [
          '--no-optional-locks',
          '-c',
          'core.fsmonitor=false',
          '-c',
          'core.untrackedCache=false',
          ...args,
        ],
        root,
        remaining,
      );
    };
    const head = invoke(['rev-parse', '--verify', 'HEAD']).trim();
    if (!/^[a-f0-9]{40}$/i.test(head)) throw new Error('Revision unavailable.');
    const status = invoke(['status', '--porcelain=v1', '--untracked-files=normal']);
    revision = head.toLowerCase();
    dirty = status.trim().length > 0;
  } catch {
    // Source archives and machines without Git still build; unknown values stay explicit.
  }
  return { schema: 1, revision, dirty, source_sha256: frontendSourceFingerprint(root) };
}
