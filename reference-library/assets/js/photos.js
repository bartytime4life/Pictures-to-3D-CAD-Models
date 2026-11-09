/* Local photo workspace. No photos are uploaded. Metadata and image
 * blobs are stored separately so filtering and exports do not load originals.
 * A calibrated image ratio is an estimate, not a reconstruction or verified CAD.
 */
(function (root) {
  'use strict';

  const VIEWPOINTS = Object.freeze(['unassigned', 'front', 'back', 'left', 'right', 'top', 'bottom', 'detail']);
  const MAX_FILE_BYTES = 50 * 1024 * 1024;
  const MAX_PIXELS = 60000000;
  const TYPES = Object.freeze(['image/jpeg', 'image/png', 'image/webp']);
  const DB_NAME = 'cad-photo-workspace';

  function validateFile(file) {
    if (!file || typeof file.arrayBuffer !== 'function' || typeof file.slice !== 'function' ||
        !Number.isSafeInteger(file.size) || file.size <= 0) {
      throw new RangeError('Choose a non-empty JPEG, PNG, or WebP photo.');
    }
    if (file.size > MAX_FILE_BYTES) throw new RangeError('Each photo must be 50 MiB or smaller. Add larger originals after resizing them.');
    if (file.type && !TYPES.includes(file.type.toLowerCase())) {
      throw new RangeError('Only JPEG, PNG, and WebP photos are supported. Convert HEIC, SVG, and other formats first.');
    }
    return file;
  }

  function detectImageType(bytes) {
    if (!(bytes instanceof Uint8Array)) throw new TypeError('Image bytes must be a Uint8Array.');
    if (bytes.length >= 8 && [137, 80, 78, 71, 13, 10, 26, 10].every((v, i) => bytes[i] === v)) return 'image/png';
    if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'image/jpeg';
    if (bytes.length >= 12 && String.fromCharCode(...bytes.subarray(0, 4)) === 'RIFF' &&
        String.fromCharCode(...bytes.subarray(8, 12)) === 'WEBP') return 'image/webp';
    throw new RangeError('This file is not a supported JPEG, PNG, or WebP photo, regardless of its filename.');
  }

  function dimensions(width, height) {
    if (!Number.isSafeInteger(width) || !Number.isSafeInteger(height) || width < 1 || height < 1) {
      throw new RangeError('The photo must have valid, positive image dimensions.');
    }
    if (width * height > MAX_PIXELS) throw new RangeError('This photo exceeds 60 megapixels. Resize it before adding it.');
  }

  // Read dimensions before decoding to avoid allocating an oversized image.
  function headerDimensions(bytes, type) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    if (type === 'image/png' && bytes.length >= 24 && String.fromCharCode(...bytes.subarray(12, 16)) === 'IHDR') {
      return [view.getUint32(16), view.getUint32(20)];
    }
    if (type === 'image/jpeg') {
      let offset = 2;
      while (offset + 3 < bytes.length) {
        if (bytes[offset++] !== 0xff) break;
        while (bytes[offset] === 0xff) offset++;
        const marker = bytes[offset++];
        if (marker === 0xda || marker === 0xd9) break;
        if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) continue;
        if (offset + 2 > bytes.length) break;
        const length = view.getUint16(offset);
        if (length < 2 || offset + length > bytes.length) break;
        if ([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf].includes(marker) && length >= 7) {
          return [view.getUint16(offset + 5), view.getUint16(offset + 3)];
        }
        offset += length;
      }
    }
    if (type === 'image/webp' && bytes.length >= 20) {
      // The first VP8X/VP8/VP8L chunk specifies the canvas or image dimensions.
      let offset = 12;
      const u24 = (start) => bytes[start] + (bytes[start + 1] << 8) + (bytes[start + 2] << 16);
      while (offset + 8 <= bytes.length) {
        const chunk = String.fromCharCode(...bytes.subarray(offset, offset + 4));
        const size = view.getUint32(offset + 4, true);
        const start = offset + 8;
        if (size > bytes.length - start) break;
        if (chunk === 'VP8X' && size >= 10) return [u24(start + 4) + 1, u24(start + 7) + 1];
        if (chunk === 'VP8 ' && size >= 10 && bytes[start + 3] === 0x9d && bytes[start + 4] === 0x01 && bytes[start + 5] === 0x2a) {
          return [view.getUint16(start + 6, true) & 0x3fff, view.getUint16(start + 8, true) & 0x3fff];
        }
        if (chunk === 'VP8L' && size >= 5 && bytes[start] === 0x2f) {
          const bits = view.getUint32(start + 1, true);
          return [(bits & 0x3fff) + 1, ((bits >>> 14) & 0x3fff) + 1];
        }
        offset = start + size + (size % 2);
      }
    }
    throw new RangeError('This photo has an incomplete or invalid image header.');
  }

  async function decode(file) {
    if (typeof root.createImageBitmap === 'function') {
      try { return await root.createImageBitmap(file, { imageOrientation: 'from-image' }); }
      catch (_) { throw new RangeError('The browser could not decode this photo. It may be damaged or use an unsupported image variant.'); }
    }
    if (typeof root.Image !== 'function' || !root.URL || !root.URL.createObjectURL) {
      throw new Error('Photo decoding is unavailable in this browser. Use a current browser with image support.');
    }
    return new Promise((resolve, reject) => {
      const url = root.URL.createObjectURL(file);
      const img = new root.Image();
      img.onload = () => { root.URL.revokeObjectURL(url); resolve(img); };
      img.onerror = () => { root.URL.revokeObjectURL(url); reject(new RangeError('The browser could not decode this photo. It may be damaged.')); };
      img.src = url;
    });
  }

  async function makeThumbnail(img, width, height) {
    const ratio = Math.min(1, 480 / Math.max(width, height));
    const w = Math.max(1, Math.round(width * ratio));
    const h = Math.max(1, Math.round(height * ratio));
    let canvas;
    if (typeof root.OffscreenCanvas === 'function') canvas = new root.OffscreenCanvas(w, h);
    else if (root.document) { canvas = root.document.createElement('canvas'); canvas.width = w; canvas.height = h; }
    else throw new Error('Thumbnail creation is unavailable in this browser.');
    const context = canvas.getContext('2d');
    if (!context) throw new Error('The browser could not create a photo thumbnail.');
    context.fillStyle = '#fff';
    context.fillRect(0, 0, w, h);
    context.drawImage(img, 0, 0, w, h);
    const blob = canvas.convertToBlob
      ? await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.82 })
      : await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82));
    if (!blob || !blob.size) throw new Error('The browser could not create a photo thumbnail.');
    return blob;
  }

  async function prepareFile(file) {
    validateFile(file);
    let buffer;
    try { buffer = await file.arrayBuffer(); }
    catch (_) { throw new Error('The browser could not read this photo. Select the file again.'); }
    if (buffer.byteLength !== file.size) throw new RangeError('The photo could not be read completely.');
    const bytes = new Uint8Array(buffer);
    const type = detectImageType(bytes);
    if (file.type && file.type.toLowerCase() !== type) throw new RangeError('This photo’s declared format does not match its contents. Convert or re-export the original image.');
    dimensions(...headerDimensions(bytes, type));
    if (!root.crypto || !root.crypto.subtle) throw new Error('Photo fingerprinting is unavailable. Open this library through localhost or a secure browser page.');
    const digest = await root.crypto.subtle.digest('SHA-256', buffer);
    const id = Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, '0')).join('');
    const img = await decode(file);
    try {
      const width = img.naturalWidth || img.width;
      const height = img.naturalHeight || img.height;
      dimensions(width, height);
      const thumbnail = await makeThumbnail(img, width, height);
      return { id, name: file.name || 'Untitled photo', type, size: file.size, width, height,
        addedAt: new Date().toISOString(), viewpoint: 'unassigned', notes: '', measurement: null, blob: file, thumbnail };
    } finally { if (typeof img.close === 'function') img.close(); }
  }

  function measurementValue(measurement, width, height) {
    dimensions(width, height);
    if (!measurement || typeof measurement !== 'object' || Array.isArray(measurement)) throw new RangeError('Choose a reference and target line before estimating a length.');
    if (!Number.isFinite(measurement.knownMm) || measurement.knownMm <= 0) throw new RangeError('The known reference length must be a positive number in millimeters.');
    const line = (points, name) => {
      if (!Array.isArray(points) || points.length !== 2) throw new RangeError(`The ${name} line needs two image points.`);
      const copy = points.map((point) => {
        if (!Array.isArray(point) || point.length !== 2 || !point.every(Number.isFinite)) throw new RangeError(`Each ${name} point needs two finite image coordinates.`);
        if (point[0] < 0 || point[0] > width || point[1] < 0 || point[1] > height) throw new RangeError(`The ${name} points must be inside the photo.`);
        return [point[0], point[1]];
      });
      if (Math.hypot(copy[1][0] - copy[0][0], copy[1][1] - copy[0][1]) === 0) throw new RangeError(`The ${name} line must have nonzero length.`);
      return copy;
    };
    return { reference: line(measurement.reference, 'reference'), target: line(measurement.target, 'target'), knownMm: measurement.knownMm };
  }

  function estimate(measurement, width, height) {
    const value = measurementValue(measurement, width, height);
    const distance = (line) => Math.hypot(line[1][0] - line[0][0], line[1][1] - line[0][1]);
    const referencePixels = distance(value.reference);
    const targetPixels = distance(value.target);
    const mmPerPixel = value.knownMm / referencePixels;
    const estimatedMm = targetPixels * mmPerPixel;
    if (![mmPerPixel, estimatedMm].every((v) => Number.isFinite(v) && v > 0)) throw new RangeError('These values exceed the supported numerical range. Use a longer reference line and realistic dimensions.');
    const warnings = ['Unverified image estimate: the reference and target must lie in the same plane, photographed front-on. Perspective, lens distortion, and endpoint choices can change the result.'];
    if (referencePixels < 200) warnings.push('The reference is shorter than 200 pixels; use a longer, clearly visible reference to reduce endpoint-picking error.');
    if (targetPixels > 3 * referencePixels) warnings.push('The target is over three times longer than the reference; this magnifies reference-picking errors.');
    return { referencePixels, targetPixels, mmPerPixel, estimatedMm, warnings };
  }

  function viewpointValue(value) {
    if (!VIEWPOINTS.includes(value)) throw new RangeError('Choose a valid photo viewpoint.');
    return value;
  }

  function notesValue(value) {
    if (typeof value !== 'string') throw new TypeError('Photo notes must be text.');
    return value;
  }

  function metadataFrom(prepared) {
    if (!prepared || !/^[a-f0-9]{64}$/.test(prepared.id || '')) throw new RangeError('Prepare this photo before saving it.');
    validateFile(prepared.blob);
    if (!TYPES.includes(prepared.type) || prepared.size !== prepared.blob.size || typeof prepared.name !== 'string') throw new RangeError('The prepared photo has invalid metadata.');
    if (!root.Blob || !(prepared.thumbnail instanceof root.Blob) || !prepared.thumbnail.size) throw new RangeError('The prepared photo needs a thumbnail.');
    if (!Number.isFinite(Date.parse(prepared.addedAt))) throw new RangeError('The prepared photo needs a valid date.');
    dimensions(prepared.width, prepared.height);
    let measurement = null;
    if (prepared.measurement != null) {
      measurement = measurementValue(prepared.measurement, prepared.width, prepared.height);
      estimate(measurement, prepared.width, prepared.height);
    }
    return { id: prepared.id, name: prepared.name, type: prepared.type, size: prepared.size,
      width: prepared.width, height: prepared.height, addedAt: new Date(prepared.addedAt).toISOString(),
      viewpoint: viewpointValue(prepared.viewpoint), notes: notesValue(prepared.notes), measurement,
      thumbnailBytes: prepared.thumbnail.size };
  }

  function storageError(error) {
    const name = error && error.name;
    let message = 'The browser could not access your photo workspace. Check browser storage settings, then try again.';
    if (name === 'QuotaExceededError') message = 'Photo storage is full. Remove photos from this workspace or free browser storage, then try again. Keep your original files.';
    else if (name === 'SecurityError' || name === 'NotAllowedError') message = 'This browser has blocked local photo storage. Allow site storage or open the library through localhost in a regular browser window.';
    else if (name === 'InvalidStateError') message = 'This photo workspace is closed or unavailable. Reload the page and try again.';
    const result = new Error(message);
    result.name = 'PhotoStorageError';
    result.cause = error;
    return result;
  }

  async function createStore() {
    if (!root.indexedDB) throw new Error('Local photo storage is unavailable in this browser. No photos have been saved. Use a browser with IndexedDB enabled.');
    const db = await new Promise((resolve, reject) => {
      let settled = false;
      let request;
      try { request = root.indexedDB.open(DB_NAME, 1); }
      catch (error) { reject(storageError(error)); return; }
      request.onupgradeneeded = () => {
        const database = request.result;
        const metadata = database.createObjectStore('metadata', { keyPath: 'id' });
        metadata.createIndex('addedAt', 'addedAt');
        database.createObjectStore('files', { keyPath: 'id' });
      };
      request.onblocked = () => { settled = true; reject(new Error('Another copy of this library is blocking photo storage. Close the other copies and reload this page.')); };
      request.onerror = () => { settled = true; reject(storageError(request.error)); };
      request.onsuccess = () => {
        if (settled) { request.result.close(); return; }
        settled = true;
        resolve(request.result);
      };
    });
    let closed = false;
    db.onversionchange = () => { closed = true; db.close(); };
    const transact = (stores, mode, action) => new Promise((resolve, reject) => {
      if (closed) { reject(new Error('This photo workspace is closed. Reload the page to reopen it.')); return; }
      let tx;
      try { tx = db.transaction(stores, mode); }
      catch (error) { reject(storageError(error)); return; }
      let result;
      let failure;
      tx.oncomplete = () => resolve(result);
      tx.onabort = () => reject(failure || storageError(tx.error));
      tx.onerror = () => { /* Abort reports the final transaction failure. */ };
      const fail = (error) => {
        failure = error;
        try { tx.abort(); } catch (_) { reject(error); }
      };
      // All IndexedDB requests are queued synchronously or in request callbacks.
      const guard = (callback) => (...args) => {
        try { callback(...args); } catch (error) { fail(storageError(error)); }
      };
      try { action(tx, (value) => { result = value; }, fail, guard); }
      catch (error) { fail(storageError(error)); }
    });
    const assertId = (id) => {
      if (typeof id !== 'string' || !/^[a-f0-9]{64}$/.test(id)) throw new RangeError('Choose a saved photo.');
    };

    return {
      async put(prepared) {
        const metadata = metadataFrom(prepared);
        const originalBlob = prepared.blob;
        const thumbnailBlob = prepared.thumbnail;
        return transact(['metadata', 'files'], 'readwrite', (tx, result, fail, guard) => {
          const meta = tx.objectStore('metadata');
          const find = meta.get(metadata.id);
          find.onsuccess = guard(() => {
            if (find.result) { result({ added: false }); return; }
            meta.add(metadata);
            const files = tx.objectStore('files');
            files.add({ id: metadata.id, blob: originalBlob });
            files.add({ id: `${metadata.id}:thumbnail`, blob: thumbnailBlob });
            result({ added: true });
          });
        });
      },
      async list({ query = '', viewpoint = '', page = 0, pageSize = 24 } = {}) {
        if (typeof query !== 'string') throw new TypeError('Search must be text.');
        if (viewpoint !== '') viewpointValue(viewpoint);
        if (!Number.isSafeInteger(page) || page < 0 || !Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100 || !Number.isSafeInteger(page * pageSize)) {
          throw new RangeError('Choose a valid page and a page size from 1 to 100.');
        }
        const term = query.trim().toLowerCase();
        return transact(['metadata'], 'readonly', (tx, result, fail, guard) => {
          const data = { items: [], total: 0, count: 0, bytes: 0, viewpoints: Object.fromEntries(VIEWPOINTS.map((v) => [v, 0])) };
          const cursor = tx.objectStore('metadata').index('addedAt').openCursor(null, 'prev');
          cursor.onsuccess = guard(() => {
            const row = cursor.result;
            if (!row) { result(data); return; }
            const photo = row.value;
            data.count++;
            data.bytes += photo.size + photo.thumbnailBytes;
            data.viewpoints[photo.viewpoint]++;
            if ((!viewpoint || photo.viewpoint === viewpoint) && (!term || `${photo.name}\n${photo.notes}`.toLowerCase().includes(term))) {
              const position = data.total++;
              if (position >= page * pageSize && data.items.length < pageSize) data.items.push(photo);
            }
            row.continue();
          });
        });
      },
      async get(id) {
        assertId(id);
        return transact(['metadata', 'files'], 'readonly', (tx, result, fail, guard) => {
          const metadata = tx.objectStore('metadata').get(id);
          metadata.onsuccess = guard(() => {
            if (!metadata.result) { result(null); return; }
            const photo = { ...metadata.result, blob: null, thumbnail: null };
            const original = tx.objectStore('files').get(id);
            const thumb = tx.objectStore('files').get(`${id}:thumbnail`);
            original.onsuccess = () => { photo.blob = original.result ? original.result.blob : null; };
            thumb.onsuccess = () => { photo.thumbnail = thumb.result ? thumb.result.blob : null; };
            result(photo);
          });
        });
      },
      async thumbnail(id) {
        assertId(id);
        return transact(['files'], 'readonly', (tx, result) => {
          const request = tx.objectStore('files').get(`${id}:thumbnail`);
          request.onsuccess = () => result(request.result ? request.result.blob : null);
        });
      },
      async update(id, patch) {
        assertId(id);
        if (!patch || typeof patch !== 'object' || Array.isArray(patch) || Object.keys(patch).some((key) => !['viewpoint', 'notes', 'measurement'].includes(key))) {
          throw new RangeError('Only viewpoint, notes, and measurement can be updated.');
        }
        // Validate caller-owned input before the asynchronous read; snapshot it so
        // later edits by the caller cannot change the committed measurement.
        const values = {};
        if (Object.hasOwn(patch, 'viewpoint')) values.viewpoint = viewpointValue(patch.viewpoint);
        if (Object.hasOwn(patch, 'notes')) values.notes = notesValue(patch.notes);
        if (Object.hasOwn(patch, 'measurement')) {
          if (patch.measurement === null) values.measurement = null;
          else {
            const m = patch.measurement;
            if (!m || typeof m !== 'object') throw new RangeError('Choose a valid measurement or clear it.');
            values.measurement = { reference: Array.isArray(m.reference) ? m.reference.map((p) => Array.isArray(p) ? [...p] : p) : m.reference,
              target: Array.isArray(m.target) ? m.target.map((p) => Array.isArray(p) ? [...p] : p) : m.target, knownMm: m.knownMm };
          }
        }
        return transact(['metadata'], 'readwrite', (tx, result, fail) => {
          const metadata = tx.objectStore('metadata');
          const request = metadata.get(id);
          request.onsuccess = () => {
            try {
              if (!request.result) throw new RangeError('This photo is no longer in the workspace.');
              const photo = { ...request.result, ...values };
              if (photo.measurement !== null) {
                photo.measurement = measurementValue(photo.measurement, photo.width, photo.height);
                estimate(photo.measurement, photo.width, photo.height);
              }
              metadata.put(photo);
              result(photo);
            } catch (error) { fail(error instanceof RangeError || error instanceof TypeError ? error : storageError(error)); }
          };
        });
      },
      async remove(id) {
        assertId(id);
        return transact(['metadata', 'files'], 'readwrite', (tx) => {
          tx.objectStore('metadata').delete(id);
          tx.objectStore('files').delete(id);
          tx.objectStore('files').delete(`${id}:thumbnail`);
        });
      },
      async exportManifest() {
        return transact(['metadata'], 'readonly', (tx, result, fail, guard) => {
          const manifest = { schema: 'cad-photo-workspace', version: 1, exportedAt: new Date().toISOString(), photos: [] };
          const request = tx.objectStore('metadata').index('addedAt').openCursor(null, 'prev');
          request.onsuccess = guard(() => {
            const cursor = request.result;
            if (!cursor) { result(manifest); return; }
            manifest.photos.push(cursor.value);
            cursor.continue();
          });
        });
      },
      close() { closed = true; db.close(); },
    };
  }

  const api = Object.freeze({ VIEWPOINTS, MAX_FILE_BYTES, MAX_PIXELS, validateFile, detectImageType, prepareFile, estimate, createStore });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CadPhotos = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
