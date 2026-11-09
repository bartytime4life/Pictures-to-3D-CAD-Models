import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const require = createRequire(import.meta.url);
const P = require('../../assets/js/photos.js');
const T = require('../../assets/js/photo-transfer.js');
const SOURCE = readFileSync(new URL('../../assets/js/photo-transfer.js', import.meta.url), 'utf8');
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==', 'base64');
const copy = (value) => JSON.parse(JSON.stringify(value));
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const file = (data, name, type) => Object.assign(new Blob([data], { type }), { name });
const record = (index = 0, extra = {}) => {
  const bytes = Buffer.concat([PNG, Buffer.from([index])]);
  const blob = file(bytes, `photo-${index}.png`, 'image/png');
  const metadata = { id: sha(bytes), name: blob.name, type: 'image/png', size: blob.size, width: 800, height: 600,
    addedAt: '2026-11-08T17:00:00.000Z', viewpoint: 'front', notes: `Reference ${index}`, thumbnailBytes: 100,
    measurement: { reference: [[0, 0], [400, 0]], target: [[0, 0], [0, 200]], knownMm: 100 }, ...extra };
  return { ...metadata, blob };
};
const manifest = (photos) => ({ schema: 'cad-photo-workspace', version: 1, exportedAt: '2026-11-08T18:00:00.000Z',
  photos: photos.map(({ blob, ...metadata }) => metadata) });
const manifestFile = (photos, name = 'cad-photo-manifest.json') => file(JSON.stringify(manifest(photos)), name, 'application/json');

// Transfers are orchestrated against deterministic browser/file-system doubles.
// Real decoding, IndexedDB, and directory-handle behavior have separate browser checks.
function transfer(core = {}) {
  const context = { CadPhotos: { ...P, ...core }, crypto: webcrypto, Blob, Uint8Array, setTimeout, console };
  vm.runInNewContext(SOURCE, context, { filename: 'photo-transfer.js' });
  return context.CadPhotoTransfer;
}
function restoreTransfer() {
  return transfer({ prepareFile: async (source) => {
    const buffer = new Uint8Array(await source.arrayBuffer());
    const type = P.detectImageType(buffer);
    return { id: sha(buffer), name: source.name, type, size: source.size, width: 800, height: 600,
      addedAt: '2026-11-09T00:00:00.000Z', viewpoint: 'unassigned', notes: '', measurement: null,
      blob: source, thumbnail: new Blob(['regenerated thumbnail']) };
  } });
}
function store(photos = []) {
  const rows = new Map(photos.map((photo) => [photo.id, { ...photo }]));
  return { rows, gets: [], saves: [], snapshots: 0,
    async exportManifest() { this.snapshots++; return copy(manifest([...rows.values()])); },
    async get(id) { this.gets.push(id); return rows.get(id) || null; },
    async put(photo) { this.saves.push(photo); if (rows.has(photo.id)) return { added: false }; rows.set(photo.id, { ...photo }); return { added: true }; },
  };
}
function failure(name, message = name) { return Object.assign(new Error(message), { name }); }
class Directory {
  constructor(name = 'destination', state = { events: [], fail: () => {} }, path = '') {
    this.name = name; this.state = state; this.path = path; this.directories = new Map(); this.files = new Map();
  }
  async getDirectoryHandle(name, { create = false } = {}) {
    assert.ok(!/[\\/]/.test(name), `Unsafe folder path: ${name}`);
    this.state.fail('directory', `${this.path}/${name}`);
    if (this.files.has(name)) throw failure('TypeMismatchError');
    if (!this.directories.has(name)) {
      if (!create) throw failure('NotFoundError');
      this.directories.set(name, new Directory(name, this.state, `${this.path}/${name}`));
    }
    return this.directories.get(name);
  }
  async getFileHandle(name, { create = false } = {}) {
    assert.ok(!/[\\/]/.test(name), `Unsafe file path: ${name}`);
    const path = `${this.path}/${name}`;
    this.state.fail('file', path);
    if (this.directories.has(name)) throw failure('TypeMismatchError');
    if (!this.files.has(name)) {
      if (!create) throw failure('NotFoundError');
      this.files.set(name, { data: new Blob([]) });
    }
    const entry = this.files.get(name);
    const { state } = this;
    return { async createWritable() {
      state.fail('writable', path);
      let pending;
      return {
        async write(contents) { state.events.push(['write', path]); state.fail('write', path); pending = contents; },
        async close() { state.events.push(['close', path]); state.fail('close', path); entry.data = pending; },
        async abort() { state.events.push(['abort', path]); },
      };
    } };
  }
  async removeEntry(name) {
    this.state.fail('remove', `${this.path}/${name}`);
    if (!this.files.delete(name)) throw failure('NotFoundError');
    this.state.events.push(['remove', `${this.path}/${name}`]);
  }
}

function onlyFolder(directory) {
  assert.equal(directory.directories.size, 1);
  return [...directory.directories.values()][0];
}

test('manifest validation preserves annotations and strips unrelated metadata', () => {
  const photo = record(0, { name: '../../unsafe/<img onerror=x>.png', notes: 'Line 1\nLine 2, "quoted"', extra: 'ignored' });
  const input = manifest([photo]);
  const result = T.validateManifest(input);
  assert.equal(result.schema, 'cad-photo-workspace');
  assert.equal(result.version, 1);
  assert.equal(result.photos[0].name, photo.name);
  assert.equal(result.photos[0].notes, photo.notes);
  assert.equal(result.photos[0].extra, undefined);
  assert.deepEqual(result.photos[0].measurement, photo.measurement);
  result.photos[0].measurement.reference[0][0] = 99;
  assert.equal(input.photos[0].measurement.reference[0][0], 0);
  delete input.photos[0].thumbnailBytes;
  assert.equal(T.validateManifest(input).photos[0].thumbnailBytes, 0);
});

test('manifest validation rejects malformed schema, IDs, duplicates, dimensions, sizes and annotations', () => {
  for (const value of [null, [], {}, { ...manifest([]), schema: 'other' }, { ...manifest([]), version: 2 }, { ...manifest([]), exportedAt: 'yesterday' }]) {
    assert.throws(() => T.validateManifest(value), /manifest|timestamp/);
  }
  for (const patch of [
    { id: '../image' }, { id: 'A'.repeat(64) }, { name: null }, { name: '' }, { notes: 42 },
    { type: 'image/svg+xml' }, { size: 0 }, { size: Infinity }, { size: 1.5 }, { size: P.MAX_FILE_BYTES + 1 },
    { width: NaN }, { height: 0 }, { width: 10000, height: 10000 }, { width: 5.5 },
    { viewpoint: 'constructor' }, { thumbnailBytes: -1 }, { thumbnailBytes: Infinity },
    { addedAt: 'not a date' }, { addedAt: '2026-02-30T12:00:00.000Z' }, { measurement: undefined }, { measurement: { reference: [[0, 0], [0, 0]], target: [[0, 0], [1, 1]], knownMm: 1 } },
    { measurement: { reference: [[0, 0], [1, 0]], target: [[0, 0], [900, 0]], knownMm: 1 } },
  ]) assert.throws(() => T.validateManifest(manifest([record(0, patch)])), undefined, JSON.stringify(patch));
  assert.throws(() => T.validateManifest(manifest([record(), record()])), /repeats a photo fingerprint/);
  assert.throws(() => T.validateManifest({ ...manifest([]), photos: new Array(1) }), /fingerprint/);
});

test('folder export writes exact originals using fingerprints and a snapshot manifest last', async () => {
  const photos = [record(0, { name: '../../unsafe.png' }), record(1)];
  const workspace = store(photos);
  const originalGet = workspace.get;
  workspace.get = async function (id) { const row = await originalGet.call(this, id); row.notes = 'changed during backup'; return row; };
  const destination = new Directory();
  const progress = [];
  const result = await transfer().exportFolder(workspace, destination, { onProgress: (value) => progress.push(copy(value)) });
  assert.equal(result.status, 'complete');
  assert.equal(result.count, 2);
  assert.equal(result.bytes, photos.reduce((sum, photo) => sum + photo.size, 0));
  assert.match(result.folderName, /^cad-photos-/);
  assert.equal(workspace.snapshots, 1);
  const backup = onlyFolder(destination);
  const images = backup.directories.get('photos');
  assert.deepEqual([...images.files.keys()], photos.map((photo) => `${photo.id}.png`));
  for (const photo of photos) assert.equal(sha(new Uint8Array(await images.files.get(`${photo.id}.png`).data.arrayBuffer())), photo.id);
  const savedManifest = JSON.parse(await backup.files.get('cad-photo-manifest.json').data.text());
  assert.equal(savedManifest.photos[0].notes, 'Reference 0');
  assert.equal(savedManifest.photos[0].name, '../../unsafe.png');
  assert.deepEqual(destination.state.events.at(-1), ['close', `/${result.folderName}/cad-photo-manifest.json`]);
  assert.deepEqual(progress.map((value) => value.processed), [0, 1, 2, 2]);
});

test('separate backups use separate folders and preserve an existing destination', async () => {
  const destination = new Directory();
  const workspace = store([record()]);
  const a = await transfer().exportFolder(workspace, destination);
  const firstManifest = destination.directories.get(a.folderName).files.get('cad-photo-manifest.json').data;
  const b = await transfer().exportFolder(workspace, destination);
  assert.notEqual(a.folderName, b.folderName);
  assert.equal(destination.directories.size, 2);
  assert.equal(destination.directories.get(a.folderName).files.get('cad-photo-manifest.json').data, firstManifest);
});

test('export rejects missing or tampered originals and leaves no completion manifest', async () => {
  for (const kind of ['missing', 'tampered']) {
    const workspace = store([record()]);
    workspace.get = async () => kind === 'missing' ? null : { blob: new Blob([Buffer.concat([PNG, Buffer.from([99])])]) };
    const destination = new Directory();
    await assert.rejects(transfer().exportFolder(workspace, destination), (error) => {
      assert.match(error.message, /incomplete.*No completion manifest/);
      assert.match(error.folderName, /^cad-photos-/);
      return true;
    });
    assert.equal(onlyFolder(destination).files.has('cad-photo-manifest.json'), false);
  }
});

test('writer failures abort and remove even an unfinished final manifest', async () => {
  for (const failureAt of ['photo write', 'manifest close']) {
    const state = { events: [], fail(operation, path) {
      if ((failureAt === 'photo write' && operation === 'write' && path.endsWith('.png')) ||
          (failureAt === 'manifest close' && operation === 'close' && path.endsWith('.json'))) throw failure('QuotaExceededError', 'Destination is full.');
    } };
    const destination = new Directory('destination', state);
    await assert.rejects(transfer().exportFolder(store([record()]), destination), /incomplete.*Destination is full/);
    assert.ok(state.events.some(([operation]) => operation === 'abort'));
    assert.equal(onlyFolder(destination).files.has('cad-photo-manifest.json'), false);
  }
});

test('export cancellation retains completed originals without a completion manifest', async () => {
  let stop = false;
  const destination = new Directory();
  const result = await transfer().exportFolder(store([record(0), record(1)]), destination, {
    shouldCancel: () => stop,
    onProgress: ({ processed }) => { if (processed === 1) stop = true; },
  });
  assert.equal(result.status, 'cancelled');
  assert.equal(result.count, 1);
  assert.equal(onlyFolder(destination).files.has('cad-photo-manifest.json'), false);
  assert.equal(onlyFolder(destination).directories.get('photos').files.size, 1);
});

test('cancellation during the manifest write aborts and removes that manifest', async () => {
  let stop = false;
  const state = { events: [], fail(operation, path) { if (operation === 'write' && path.endsWith('.json')) stop = true; } };
  const destination = new Directory('destination', state);
  const result = await transfer().exportFolder(store([record()]), destination, { shouldCancel: () => stop });
  assert.equal(result.status, 'cancelled');
  assert.equal(onlyFolder(destination).files.has('cad-photo-manifest.json'), false);
  assert.ok(state.events.some(([operation]) => operation === 'abort'));
});

test('restore validates every manifest entry before the first photo write', async () => {
  const photos = [record(0), record(1, { notes: null })];
  const workspace = store();
  await assert.rejects(restoreTransfer().restoreFiles(workspace, [photos[0].blob, manifestFile(photos), photos[1].blob]), /text notes/);
  assert.equal(workspace.saves.length, 0);
  assert.equal(workspace.rows.size, 0);
});

test('restore requires one unambiguous bounded manifest', async () => {
  const workspace = store();
  const photo = record();
  const run = (files) => restoreTransfer().restoreFiles(workspace, files);
  await assert.rejects(run([photo.blob]), /No photo manifest/);
  await assert.rejects(run([manifestFile([photo]), manifestFile([photo])]), /multiple possible manifests/);
  await assert.rejects(run([manifestFile([photo], 'one.json'), manifestFile([photo], 'two.json')]), /multiple possible manifests/);
  await assert.rejects(run([{ name: 'cad-photo-manifest.json', size: T.MAX_MANIFEST_BYTES + 1, async text() { throw new Error('must not read'); } }]), /64 MiB/);
  await assert.rejects(run([file('{broken', 'cad-photo-manifest.json', 'application/json')]), /not valid JSON/);
  assert.equal(workspace.saves.length, 0);
});

test('restore matches content regardless of filename and saves original annotations atomically', async () => {
  const photo = record(0, { name: '../../unsafe/<img>.png', notes: 'Keep\nexact text', viewpoint: 'left' });
  const workspace = store();
  const renamed = file(await photo.blob.arrayBuffer(), 'renamed.png', 'image/png');
  const progress = [];
  const result = await restoreTransfer().restoreFiles(workspace, [manifestFile([photo], 'original-list.json'), renamed], { onProgress: (value) => progress.push(copy(value)) });
  assert.deepEqual(copy(result), { added: 1, duplicates: 0, failed: 0, missing: 0, unmatched: 0, cancelled: false, errors: [], processed: 1, total: 1 });
  const saved = workspace.rows.get(photo.id);
  for (const key of ['name', 'notes', 'viewpoint', 'addedAt']) assert.equal(saved[key], photo[key]);
  assert.deepEqual(copy(saved.measurement), photo.measurement);
  assert.equal(saved.blob, renamed);
  assert.equal(workspace.saves.length, 1);
  assert.deepEqual(progress.map((value) => value.processed), [0, 1]);
});

test('existing photos retain newer annotations; unrelated and missing images are accounted separately', async () => {
  const photos = [record(0), record(1)];
  const workspace = store([{ ...photos[0], notes: 'Newer local notes', viewpoint: 'back' }]);
  const result = await restoreTransfer().restoreFiles(workspace, [manifestFile(photos), photos[0].blob, record(2).blob, file('readme', 'README.txt', 'text/plain')]);
  assert.equal(result.added, 0);
  assert.equal(result.duplicates, 1);
  assert.equal(result.missing, 1);
  assert.equal(result.unmatched, 2);
  assert.equal(result.failed, 0);
  assert.equal(workspace.rows.get(photos[0].id).notes, 'Newer local notes');
  assert.equal(workspace.rows.get(photos[0].id).viewpoint, 'back');
});

test('restore rejects inconsistent image dimensions without marking the original present', async () => {
  const photo = record(0, { width: 799 });
  const workspace = store();
  const result = await restoreTransfer().restoreFiles(workspace, [manifestFile([photo]), photo.blob]);
  assert.equal(result.failed, 1);
  assert.equal(result.missing, 1);
  assert.match(result.errors[0].message, /do not match/);
  assert.equal(workspace.saves.length, 0);
});

test('storage failures stop restore after preserving earlier successful commits', async () => {
  const photos = [record(0), record(1), record(2)];
  const workspace = store();
  const put = workspace.put;
  workspace.put = async function (photo) {
    if (this.rows.size === 1) throw failure('PhotoStorageError', 'Photo storage is full.');
    return put.call(this, photo);
  };
  const result = await restoreTransfer().restoreFiles(workspace, [manifestFile(photos), ...photos.map((photo) => photo.blob)]);
  assert.equal(result.added, 1);
  assert.equal(result.failed, 1);
  assert.equal(result.processed, 2);
  assert.equal(result.total, 3);
  assert.equal(result.missing, 2);
  assert.equal(workspace.rows.size, 1);
  assert.match(result.errors[0].message, /storage is full/);
});

test('restore cancellation finishes the current image and reports remaining originals', async () => {
  let stop = false;
  const photos = [record(0), record(1)];
  const workspace = store();
  const result = await restoreTransfer().restoreFiles(workspace, [manifestFile(photos), ...photos.map((photo) => photo.blob)], {
    shouldCancel: () => stop,
    onProgress: ({ processed }) => { if (processed === 1) stop = true; },
  });
  assert.equal(result.cancelled, true);
  assert.equal(result.added, 1);
  assert.equal(result.processed, 1);
  assert.equal(result.missing, 1);
  assert.equal(workspace.rows.size, 1);
});


test('restore caps error details while counting every failed image', async () => {
  const photos = Array.from({ length: 45 }, (_, i) => file('not an image', `broken-${i}.png`, 'image/png'));
  const result = await restoreTransfer().restoreFiles(store(), [manifestFile([]), ...photos]);
  assert.equal(result.failed, 45);
  assert.equal(result.errors.length, 30);
  assert.equal(result.processed, 45);
  assert.equal(result.errors[0].name, 'broken-0.png');
  assert.equal(result.errors[29].name, 'broken-29.png');
});

test('a large ignored-file selection yields to an asynchronously requested cancellation', async () => {
  let stop = false;
  const extras = Array.from({ length: 100 }, (_, i) => file('extra', `notes-${i}.txt`, 'text/plain'));
  const result = await restoreTransfer().restoreFiles(store(), [manifestFile([]), ...extras], {
    shouldCancel: () => stop,
    onProgress: ({ processed }) => { if (processed === 1) setTimeout(() => { stop = true; }, 0); },
  });
  assert.equal(result.cancelled, true);
  assert.equal(result.processed, 1);
  assert.equal(result.unmatched, 1);
});


test('restore recognizes renamed originals with missing or generic MIME by their actual signature', async () => {
  for (const type of ['', 'application/octet-stream']) {
    const photo = record();
    const source = file(await photo.blob.arrayBuffer(), 'reference.bin', type);
    const workspace = store();
    const result = await restoreTransfer().restoreFiles(workspace, [manifestFile([photo]), source]);
    assert.equal(result.added, 1, type || 'empty MIME');
    assert.equal(result.missing, 0);
    assert.equal(result.unmatched, 0);
    const saved = workspace.rows.get(photo.id);
    assert.equal(saved.type, 'image/png');
    assert.equal(sha(new Uint8Array(await saved.blob.arrayBuffer())), photo.id);
  }
});

test('restore does not replace an explicit mismatched image MIME with a sniffed type', async () => {
  const photo = record();
  const workspace = store();
  let seenType;
  const api = transfer({ prepareFile: async (source) => { seenType = source.type; throw new RangeError('Declared format does not match contents.'); } });
  const result = await api.restoreFiles(workspace, [manifestFile([photo]), file(await photo.blob.arrayBuffer(), 'reference.bin', 'image/jpeg')]);
  assert.equal(seenType, 'image/jpeg');
  assert.equal(result.failed, 1);
  assert.equal(result.missing, 1);
  assert.equal(workspace.saves.length, 0);
});
