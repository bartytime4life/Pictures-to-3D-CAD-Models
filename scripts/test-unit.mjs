import { readdir } from 'node:fs/promises';

// Import each pure TypeScript suite in this process. node:test reports their
// results and sets a failing exit code without spawning a second test process.
const directory = new URL('../tests/unit/', import.meta.url);
const suites = (await readdir(directory)).filter((name) => name.endsWith('.test.ts')).sort();
if (!suites.length) throw new Error('No unit test suites found.');
for (const suite of suites) await import(new URL(suite, directory).href);
