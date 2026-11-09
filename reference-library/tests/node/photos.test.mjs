import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash, webcrypto } from 'node:crypto';

const require = createRequire(import.meta.url);
const P = require('../../assets/js/photos.js');
const PNG = Uint8Array.from(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==', 'base64'));
const measurement = { reference: [[10, 20], [410, 20]], target: [[30, 40], [30, 240]], knownMm: 100 };
const file = (bytes = PNG, type = 'image/png', name = 'sample.png') => Object.assign(new Blob([bytes], { type }), { name });

function globals(values) {
  const descriptors = new Map(Object.keys(values).map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  for (const [key, value] of Object.entries(values)) Object.defineProperty(globalThis, key, { configurable: true, writable: true, value });
  return () => {
    for (const [key, descriptor] of descriptors) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  };
}

function browserStub(options = {}) {
  const state = { closes: 0, decoded: 0, canvas: null };
  const restore = globals({
    crypto: webcrypto,
    createImageBitmap: async () => {
      state.decoded++;
      if (options.decodeError) throw new Error('decode failure');
      return { width: options.width || 1200, height: options.height || 800, close() { state.closes++; } };
    },
    OffscreenCanvas: class {
      constructor(width, height) { state.canvas = [width, height]; }
      getContext() { return { fillRect() {}, drawImage() {} }; }
      async convertToBlob() {
        if (options.thumbnailError) throw new Error('thumbnail failure');
        return new Blob(['thumbnail'], { type: 'image/jpeg' });
      }
    },
  });
  return { state, restore };
}

test('photo file policy accepts raster formats without a photo-count limit', () => {
  assert.deepEqual(P.VIEWPOINTS, ['unassigned', 'front', 'back', 'left', 'right', 'top', 'bottom', 'detail']);
  assert.equal(P.MAX_FILE_BYTES, 50 * 1024 * 1024);
  assert.equal(P.MAX_PIXELS, 60000000);
  assert.equal(P.validateFile(file()).type, 'image/png');
  assert.equal(P.validateFile(file(PNG, '')).type, '');
  assert.throws(() => P.validateFile(null), /non-empty/);
  assert.throws(() => P.validateFile(new Blob([])), /non-empty/);
  for (const type of ['image/svg+xml', 'image/heic', 'image/gif', 'text/html']) {
    assert.throws(() => P.validateFile(file(PNG, type)), /Only JPEG, PNG, and WebP/);
  }
  const oversized = { size: P.MAX_FILE_BYTES + 1, type: 'image/png', arrayBuffer() {}, slice() {} };
  assert.throws(() => P.validateFile(oversized), /50 MiB/);
});

test('image signatures reject disguised markup and truncated files', () => {
  assert.equal(P.detectImageType(PNG), 'image/png');
  assert.equal(P.detectImageType(new Uint8Array([255, 216, 255, 224])), 'image/jpeg');
  assert.equal(P.detectImageType(new TextEncoder().encode('RIFFxxxxWEBP')), 'image/webp');
  for (const bytes of [new Uint8Array(), new Uint8Array([137, 80, 78]), new TextEncoder().encode('<svg></svg>'), new TextEncoder().encode('not a photo')]) {
    assert.throws(() => P.detectImageType(bytes), /not a supported/);
  }
  assert.throws(() => P.detectImageType([255, 216, 255]), /Uint8Array/);
});

test('calibration computes a same-plane ratio and preserves the original input', () => {
  const original = structuredClone(measurement);
  const result = P.estimate(measurement, 800, 600);
  assert.equal(result.referencePixels, 400);
  assert.equal(result.targetPixels, 200);
  assert.equal(result.mmPerPixel, 0.25);
  assert.equal(result.estimatedMm, 50);
  assert.deepEqual(measurement, original);
  assert.equal(result.warnings.length, 1);
  assert.match(result.warnings[0], /Unverified.*same plane.*front-on/);
});

test('calibration supports diagonal lines, warns about weak baselines and extrapolation', () => {
  const result = P.estimate({ reference: [[0, 0], [3, 4]], target: [[0, 0], [30, 40]], knownMm: 10 }, 100, 100);
  assert.equal(result.referencePixels, 5);
  assert.equal(result.targetPixels, 50);
  assert.equal(result.estimatedMm, 100);
  assert.match(result.warnings.join(' '), /shorter than 200/);
  assert.match(result.warnings.join(' '), /three times/);
  // Coordinates are continuous image-space positions; the image edge is valid.
  assert.equal(P.estimate({ reference: [[0, 0], [100, 0]], target: [[0, 0], [100, 100]], knownMm: 100 }, 100, 100).estimatedMm, Math.hypot(100, 100));
});

test('calibration rejects invalid, out-of-image, zero-length, and overflowing inputs', () => {
  for (const knownMm of [0, -1, Infinity, NaN, '100', null]) {
    assert.throws(() => P.estimate({ ...measurement, knownMm }, 800, 600), /positive number/);
  }
  for (const points of [null, [], [[0, 0]], [[0, 0], [1, 1], [2, 2]], [[NaN, 0], [1, 1]], [[0, 0], [Infinity, 1]], [[0, 0], ['1', 1]], [[0, 0, 0], [1, 1]]]) {
    assert.throws(() => P.estimate({ ...measurement, reference: points }, 800, 600), /points|coordinates/);
  }
  for (const points of [[[-1, 0], [1, 1]], [[0, 0], [801, 1]], [[0, 0], [1, 601]]]) {
    assert.throws(() => P.estimate({ ...measurement, target: points }, 800, 600), /inside the photo/);
  }
  for (const key of ['reference', 'target']) {
    assert.throws(() => P.estimate({ ...measurement, [key]: [[1, 1], [1, 1]] }, 800, 600), /nonzero/);
  }
  for (const dims of [[0, 600], [-1, 600], [800.5, 600], [800, NaN], [10000, 10000]]) {
    assert.throws(() => P.estimate(measurement, ...dims), /dimensions|megapixels/);
  }
  assert.throws(() => P.estimate(null, 800, 600), /reference and target/);
  assert.throws(() => P.estimate({ reference: [[0, 0], [Number.MIN_VALUE, 0]], target: [[0, 0], [100, 0]], knownMm: Number.MAX_VALUE }, 800, 600), /numerical range/);
});

test('preparation uses actual bytes for identity, creates a bounded thumbnail, and releases decoded images', async () => {
  const { state, restore } = browserStub();
  try {
    const source = file();
    const result = await P.prepareFile(source);
    assert.equal(result.id, createHash('sha256').update(PNG).digest('hex'));
    assert.equal(result.blob, source);
    assert.equal(result.name, 'sample.png');
    assert.equal(result.type, 'image/png');
    assert.equal(result.size, PNG.length);
    assert.deepEqual([result.width, result.height], [1200, 800]);
    assert.deepEqual(state.canvas, [480, 320]);
    assert.equal(result.viewpoint, 'unassigned');
    assert.equal(result.notes, '');
    assert.equal(result.measurement, null);
    assert.ok(result.thumbnail instanceof Blob);
    assert.ok(Number.isFinite(Date.parse(result.addedAt)));
    const renamed = await P.prepareFile(file(PNG, 'image/png', 'renamed.png'));
    assert.equal(renamed.id, result.id);
    assert.equal(state.closes, 2);
  } finally { restore(); }
});

test('preparation refuses forged MIME, corrupt headers, and oversized dimensions before decoding', async () => {
  const { state, restore } = browserStub();
  try {
    await assert.rejects(P.prepareFile(file(PNG, 'image/jpeg')), /declared format/);
    await assert.rejects(P.prepareFile(file(new Uint8Array([255, 216, 255]), 'image/jpeg')), /invalid image header/);
    await assert.rejects(P.prepareFile(file(new TextEncoder().encode('<svg/>'))), /not a supported/);
    const large = PNG.slice();
    const view = new DataView(large.buffer);
    view.setUint32(16, 10000);
    view.setUint32(20, 10000);
    await assert.rejects(P.prepareFile(file(large)), /60 megapixels/);
    assert.equal(state.decoded, 0);
  } finally { restore(); }
});

test('decoding failures and decoded pixel limits reject instead of manufacturing a photo', async () => {
  let stub = browserStub({ decodeError: true });
  try { await assert.rejects(P.prepareFile(file()), /could not decode/); }
  finally { stub.restore(); }
  stub = browserStub({ width: 10000, height: 10000 });
  try {
    await assert.rejects(P.prepareFile(file()), /60 megapixels/);
    assert.equal(stub.state.closes, 1);
  } finally { stub.restore(); }
  stub = browserStub({ thumbnailError: true });
  try {
    await assert.rejects(P.prepareFile(file()), /thumbnail failure/);
    assert.equal(stub.state.closes, 1);
  } finally { stub.restore(); }
});

test('missing storage and fingerprinting produce actionable errors with no memory-only success', async () => {
  const restore = globals({ indexedDB: undefined, crypto: undefined });
  try {
    await assert.rejects(P.createStore(), /unavailable.*No photos have been saved/);
    await assert.rejects(P.prepareFile(file()), /fingerprinting is unavailable/);
  } finally { restore(); }
});

test('storage security and quota failures remain readable', async () => {
  for (const [name, pattern] of [['SecurityError', /blocked local photo storage/], ['QuotaExceededError', /storage is full/]]) {
    const restore = globals({ indexedDB: { open() { throw Object.assign(new Error('browser error'), { name }); } } });
    try { await assert.rejects(P.createStore(), pattern); }
    finally { restore(); }
  }
});
