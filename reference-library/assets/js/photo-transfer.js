/* Portable, local photo backups. A completion manifest is written only after
 * every original is saved. Restores match bytes by SHA-256, never by filename.
 */
(function (root) {
  'use strict';
  const P = typeof module !== 'undefined' && module.exports ? require('./photos.js') : root.CadPhotos;
  if (!P) throw new Error('Load the photo workspace before photo transfer.');
  const MAX_MANIFEST_BYTES = 64 * 1024 * 1024;
  const MANIFEST_NAME = 'cad-photo-manifest.json';
  const MAX_REPORTED_ERRORS = 30;
  const yieldTurn = () => new Promise((resolve) => root.setTimeout(resolve, 0));
  const EXTENSIONS = Object.freeze({ 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp' });
  const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
  const dateValue = (value, name) => {
    const parts = typeof value === 'string' && /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.exec(value);
    if (!parts || !Number.isFinite(Date.parse(value))) throw new RangeError(`${name} must be a valid timestamp.`);
    const [year, month, day, hour, minute, second] = parts.slice(1).map(Number);
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (month < 1 || month > 12 || day < 1 || day > days[month - 1] || hour > 23 || minute > 59 || second > 59) {
      throw new RangeError(`${name} must be a valid timestamp.`);
    }
    return new Date(value).toISOString();
  };

  function validateManifest(value) {
    if (!isObject(value) || value.schema !== 'cad-photo-workspace' || value.version !== 1 || !Array.isArray(value.photos)) {
      throw new RangeError('Choose a version 1 cad-photo-workspace manifest.');
    }
    const exportedAt = dateValue(value.exportedAt, 'The manifest export date');
    const ids = new Set();
    const photos = Array.from(value.photos, (photo, index) => {
      const label = `Photo ${index + 1}`;
      if (!isObject(photo) || typeof photo.id !== 'string' || !/^[a-f0-9]{64}$/.test(photo.id)) throw new RangeError(`${label} needs a valid lowercase SHA-256 fingerprint.`);
      if (ids.has(photo.id)) throw new RangeError(`${label} repeats a photo fingerprint. Every manifest photo must be unique.`);
      ids.add(photo.id);
      if (typeof photo.name !== 'string' || !photo.name.length || typeof photo.notes !== 'string') throw new RangeError(`${label} needs a filename and text notes.`);
      if (typeof photo.type !== 'string' || !Object.hasOwn(EXTENSIONS, photo.type)) throw new RangeError(`${label} must be a JPEG, PNG, or WebP photo.`);
      if (!Number.isSafeInteger(photo.size) || photo.size <= 0 || photo.size > P.MAX_FILE_BYTES) throw new RangeError(`${label} has an invalid original file size.`);
      if (!Number.isSafeInteger(photo.width) || !Number.isSafeInteger(photo.height) || photo.width < 1 || photo.height < 1 || photo.width * photo.height > P.MAX_PIXELS) {
        throw new RangeError(`${label} has invalid dimensions or exceeds 60 megapixels.`);
      }
      if (!P.VIEWPOINTS.includes(photo.viewpoint)) throw new RangeError(`${label} has an unknown viewpoint.`);
      const thumbnailBytes = photo.thumbnailBytes === undefined ? 0 : photo.thumbnailBytes;
      if (!Number.isSafeInteger(thumbnailBytes) || thumbnailBytes < 0 || thumbnailBytes > P.MAX_FILE_BYTES) throw new RangeError(`${label} has an invalid thumbnail size.`);
      let measurement = null;
      if (photo.measurement !== null) {
        if (!isObject(photo.measurement)) throw new RangeError(`${label} needs a valid measurement or null.`);
        P.estimate(photo.measurement, photo.width, photo.height);
        measurement = { reference: photo.measurement.reference.map((point) => [...point]),
          target: photo.measurement.target.map((point) => [...point]), knownMm: photo.measurement.knownMm };
      }
      return { id: photo.id, name: photo.name, type: photo.type, size: photo.size, width: photo.width, height: photo.height,
        addedAt: dateValue(photo.addedAt, `${label}'s added date`), viewpoint: photo.viewpoint,
        notes: photo.notes, measurement, thumbnailBytes };
    });
    return { schema: 'cad-photo-workspace', version: 1, exportedAt, photos };
  }

  function callbacks(options) {
    if (options.onProgress !== undefined && typeof options.onProgress !== 'function') throw new TypeError('Progress must be a callback.');
    if (options.shouldCancel !== undefined && typeof options.shouldCancel !== 'function') throw new TypeError('Cancellation must be a callback.');
    return { report: options.onProgress || (() => {}), cancelled: options.shouldCancel || (() => false) };
  }

  async function fingerprint(blob) {
    if (!root.crypto || !root.crypto.subtle) throw new Error('Photo fingerprinting is unavailable. Use localhost or a secure browser page.');
    const buffer = await blob.arrayBuffer();
    const digest = await root.crypto.subtle.digest('SHA-256', buffer);
    return { id: Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, '0')).join(''),
      type: P.detectImageType(new Uint8Array(buffer)), size: buffer.byteLength };
  }

  function randomSuffix() {
    if (root.crypto && typeof root.crypto.randomUUID === 'function') return root.crypto.randomUUID();
    if (root.crypto && typeof root.crypto.getRandomValues === 'function') {
      return Array.from(root.crypto.getRandomValues(new Uint8Array(16)), (v) => v.toString(16).padStart(2, '0')).join('');
    }
    throw new Error('Secure backup folder naming is unavailable. Use localhost or a secure browser page.');
  }

  async function newBackupFolder(directory) {
    if (!directory || typeof directory.getDirectoryHandle !== 'function') throw new TypeError('Choose a writable backup folder first.');
    for (let attempt = 0; attempt < 8; attempt++) {
      const folderName = `cad-photos-${new Date().toISOString().replace(/[:.]/g, '-')}-${randomSuffix()}`;
      try {
        await directory.getDirectoryHandle(folderName, { create: false });
        continue; // Never reuse an existing folder, including an empty one.
      } catch (error) {
        if (error.name === 'TypeMismatchError') continue; // An existing file also reserves this name.
        if (error.name !== 'NotFoundError') throw error;
      }
      const folder = await directory.getDirectoryHandle(folderName, { create: true });
      return { folder, folderName };
    }
    throw new Error('Could not create a unique backup folder. Try another destination.');
  }

  const cancellation = () => Object.assign(new Error('Backup cancelled.'), { name: 'PhotoTransferCancelled' });
  async function writeFile(directory, name, contents, cancelBeforeClose) {
    let writer;
    try {
      const handle = await directory.getFileHandle(name, { create: true });
      writer = await handle.createWritable({ keepExistingData: false });
      await writer.write(contents);
      if (cancelBeforeClose && cancelBeforeClose()) throw cancellation();
      await writer.close();
    } catch (error) {
      if (writer && typeof writer.abort === 'function') {
        try { await writer.abort(); } catch (_) { /* The failed stream may already be closed. */ }
      }
      throw error;
    }
  }

  async function exportFolder(store, directory, options = {}) {
    const { report, cancelled } = callbacks(options);
    // Snapshot and validate metadata before creating any destination files.
    const manifest = validateManifest(await store.exportManifest());
    const manifestBlob = new root.Blob([JSON.stringify(manifest, null, 2)], { type: 'application/json' });
    if (manifestBlob.size > MAX_MANIFEST_BYTES) throw new RangeError('This manifest exceeds the 64 MiB transfer limit. Export a smaller workspace.');
    const total = manifest.photos.length;
    let count = 0;
    let bytes = 0;
    let folder;
    let folderName = '';
    let manifestMayExist = false;
    const clearManifest = async () => {
      if (!folder || !manifestMayExist) return;
      try { await folder.removeEntry(MANIFEST_NAME); manifestMayExist = false; }
      catch (error) {
        if (error.name === 'NotFoundError') { manifestMayExist = false; return; }
        throw new Error('The unfinished completion manifest could not be removed. Do not use this folder as a completed backup.');
      }
    };
    const result = (status) => ({ status, folderName, count, bytes });
    try {
      report({ processed: 0, total, name: '', phase: 'export' });
      if (cancelled()) return result('cancelled');
      ({ folder, folderName } = await newBackupFolder(directory));
      const images = await folder.getDirectoryHandle('photos', { create: true });
      for (const metadata of manifest.photos) {
        if (cancelled()) return result('cancelled');
        const photo = await store.get(metadata.id);
        if (!photo || !photo.blob || typeof photo.blob.arrayBuffer !== 'function') throw new Error(`The original for “${metadata.name}” is no longer available. Keep the workspace unchanged while backing up.`);
        // Blob values are immutable: annotations can change in another tab while
        // this write safely uses the starting metadata snapshot and exact bytes.
        if (photo.blob.size !== metadata.size) throw new Error(`The original size for “${metadata.name}” differs from the manifest.`);
        const actual = await fingerprint(photo.blob);
        if (actual.id !== metadata.id || actual.type !== metadata.type || actual.size !== metadata.size) throw new Error(`The original for “${metadata.name}” failed its fingerprint or format check.`);
        await writeFile(images, `${metadata.id}.${EXTENSIONS[metadata.type]}`, photo.blob);
        count++;
        bytes += metadata.size;
        report({ processed: count, total, name: metadata.name, phase: 'export' });
        await yieldTurn();
      }
      if (cancelled()) return result('cancelled');
      report({ processed: count, total, name: MANIFEST_NAME, phase: 'manifest' });
      if (cancelled()) return result('cancelled');
      manifestMayExist = true;
      await writeFile(folder, MANIFEST_NAME, manifestBlob, cancelled);
      if (cancelled()) { await clearManifest(); return result('cancelled'); }
      return result('complete');
    } catch (error) {
      let cleanupError;
      try { await clearManifest(); } catch (failure) { cleanupError = failure; }
      if (error.name === 'PhotoTransferCancelled' && !cleanupError) return result('cancelled');
      const location = folderName ? `Backup is incomplete in “${folderName}”.` : 'The backup could not start.';
      const detail = cleanupError ? cleanupError.message : (error && error.message ? error.message : 'The destination could not be written.');
      const failure = new Error(`${location} ${detail}${folderName && !cleanupError ? ' No completion manifest was kept.' : ''}`);
      failure.name = 'PhotoTransferError';
      failure.folderName = folderName;
      failure.count = count;
      failure.bytes = bytes;
      failure.cause = error;
      throw failure;
    }
  }

  function chooseManifest(files) {
    const json = files.filter((file) => typeof file.name === 'string' && /\.json$/i.test(file.name));
    const named = json.filter((file) => file.name.toLowerCase() === MANIFEST_NAME);
    if (named.length > 1 || (named.length === 0 && json.length > 1)) throw new RangeError('The selection contains multiple possible manifests. Select one backup folder or one manifest with its photos.');
    if (named.length === 1) return named[0];
    if (json.length === 1) return json[0];
    throw new RangeError('No photo manifest was found. Include cad-photo-manifest.json or the exported JSON photo list with its originals.');
  }

  async function restoreFiles(store, files, options = {}) {
    const { report, cancelled } = callbacks(options);
    const selected = Array.from(files || []);
    const manifestFile = chooseManifest(selected);
    if (!Number.isSafeInteger(manifestFile.size) || manifestFile.size < 0 || manifestFile.size > MAX_MANIFEST_BYTES || typeof manifestFile.text !== 'function') {
      throw new RangeError('The selected manifest must be a readable JSON file of 64 MiB or smaller.');
    }
    let parsed;
    try { parsed = JSON.parse(await manifestFile.text()); }
    catch (_) { throw new RangeError('The selected manifest is not valid JSON. No photos were restored.'); }
    // Validate every record before any write so a malformed later record cannot
    // leave a partially accepted manifest in the workspace.
    const manifest = validateManifest(parsed);
    const expected = new Map(manifest.photos.map((photo) => [photo.id, photo]));
    const found = new Set();
    const candidates = selected.filter((file) => file !== manifestFile);
    const result = { added: 0, duplicates: 0, failed: 0, missing: expected.size, unmatched: 0, cancelled: false,
      errors: [], processed: 0, total: candidates.length };
    report({ processed: 0, total: result.total, name: '', phase: 'restore' });
    for (const file of candidates) {
      if (cancelled()) { result.cancelled = true; break; }
      const name = file && typeof file.name === 'string' ? file.name : 'Unnamed file';
      let stop = false;
      try {
        // Other files in a selected folder are not photo restoration failures.
        let candidate = file && ((typeof file.type === 'string' && Object.hasOwn(EXTENSIONS, file.type)) || /\.(jpe?g|png|webp)$/i.test(name));
        const genericType = file && (!file.type || file.type === 'application/octet-stream');
        let detectedType;
        if (file && typeof file.slice === 'function' && (!candidate || genericType)) {
          try {
            detectedType = P.detectImageType(new Uint8Array(await file.slice(0, 16).arrayBuffer()));
            candidate = true;
          } catch (_) { /* Unrecognized extras are ignored; declared photos still go through full validation. */ }
        }
        if (!candidate) result.unmatched++;
        else {
          let source = file;
          // Folder pickers can assign a generic MIME to a renamed original. A
          // recognized signature can supply that missing type without changing
          // any bytes. Explicit image MIME mismatches still fail prepareFile.
          if (genericType && detectedType) {
            source = typeof root.File === 'function'
              ? new root.File([file], name, { type: detectedType, lastModified: file.lastModified })
              : Object.assign(new root.Blob([file], { type: detectedType }), { name });
          }
          const prepared = await P.prepareFile(source);
          const metadata = expected.get(prepared.id);
          if (!metadata) result.unmatched++;
          else {
            if (prepared.type !== metadata.type || prepared.size !== metadata.size || prepared.width !== metadata.width || prepared.height !== metadata.height) {
              throw new RangeError('This photo’s format, size, or dimensions do not match its manifest record.');
            }
            Object.assign(prepared, { name: metadata.name, addedAt: metadata.addedAt, viewpoint: metadata.viewpoint,
              notes: metadata.notes, measurement: metadata.measurement });
            let saved;
            try { saved = await store.put(prepared); }
            catch (error) { stop = true; throw error; }
            if (!saved || typeof saved.added !== 'boolean') { stop = true; throw new Error('The photo workspace did not confirm that this photo was saved.'); }
            if (saved.added) result.added++;
            else result.duplicates++;
            found.add(metadata.id);
          }
        }
      } catch (error) {
        result.failed++;
        if (result.errors.length < MAX_REPORTED_ERRORS) result.errors.push({ name, message: error && error.message ? error.message : 'This photo could not be restored.' });
      }
      result.processed++;
      result.missing = expected.size - found.size;
      report({ processed: result.processed, total: result.total, name, phase: 'restore' });
      if (stop) break; // Earlier committed photos remain available on storage failure.
      // In particular, ignored extras have no I/O await. Yield so Cancel and
      // browser rendering remain responsive even for a large folder selection.
      await yieldTurn();
    }
    result.missing = expected.size - found.size;
    if (cancelled()) result.cancelled = true;
    return result;
  }

  const api = Object.freeze({ MAX_MANIFEST_BYTES, MAX_REPORTED_ERRORS, validateManifest, exportFolder, restoreFiles });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CadPhotoTransfer = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
