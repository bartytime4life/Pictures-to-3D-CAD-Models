// Browser acceptance for portable photo-folder backup and restoration.
// Uses synthetic images, isolated browser contexts and actual browser OPFS writes.
// The native folder picker is substituted with an OPFS directory handle; no real
// user folder picker or personal photograph is accessed.
import fs from 'node:fs';
import path from 'node:path';
import { ROOT, requireModule, findChrome, readJSON } from './lib/runtime.mjs';
import { browserTransport, openTransport } from './lib/serve.mjs';

const { chromium } = requireModule('playwright');
const qa = path.join(ROOT, 'tmp/qa');
const qaFile = path.join(qa, 'photo-transfer-check.json');
const fixtureRoot = path.join(qa, 'transfer-fixtures');
const results = {
  checked_at: new Date().toISOString(), revision: readJSON('library.json').revision,
  status: 'running', checks: [], browser_errors: [],
  scope: 'Synthetic PNGs in isolated Chromium contexts. Actual OPFS folder writes through a substituted native picker, physical fixture extraction, directory-input restore into a separate browser context, metadata and byte fidelity, keep-existing duplicates, malformed/incomplete/tampered backups, cancellation, quota failure, unavailable picker, responsive controls, and deterministic controller races. Native operating-system folder chooser interaction is not exercised.',
};
fs.mkdirSync(qa, { recursive: true });
fs.rmSync(qaFile, { force: true });
fs.rmSync(fixtureRoot, { recursive: true, force: true });
fs.mkdirSync(fixtureRoot, { recursive: true });
const assert = (value, label) => {
  if (!value) throw new Error('FAILED: ' + label);
  results.checks.push(label);
};
const record = () => fs.writeFileSync(qaFile, JSON.stringify({ ...results, check_count: results.checks.length }, null, 2) + '\n');
let browser, served;
try {
  const requestedTransport = browserTransport();
  served = await openTransport(requestedTransport);
  browser = await chromium.launch({ headless: true, executablePath: findChrome() });
  let pageUrl = served.pageUrl + '#photos';
  const sourceContext = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
  const watch = (page) => {
    page.on('pageerror', (error) => results.browser_errors.push(error.message));
    page.on('console', (message) => { if (message.type() === 'error') results.browser_errors.push(message.text()); });
  };
  const source = await sourceContext.newPage();
  watch(source);
  await source.goto(pageUrl);
  let opfsReady = await source.evaluate(async () => { try { await navigator.storage.getDirectory(); return true; } catch { return false; } });
  if (!opfsReady && requestedTransport === 'file') {
    // Some browsers deny OPFS on file URLs. Use the same restricted loopback
    // transport as the other browser checks, and record which origin was tested.
    await served.close();
    served = await openTransport('http');
    pageUrl = served.pageUrl + '#photos';
    await source.goto(pageUrl);
    opfsReady = await source.evaluate(async () => { try { await navigator.storage.getDirectory(); return true; } catch { return false; } });
  }
  assert(opfsReady, 'Browser provides an actual origin-private filesystem for backup writes');
  results.transport = pageUrl.startsWith('file:') ? 'file URL' : 'loopback HTTP';
  await source.waitForFunction(() => window.CadPhotoTransfer && !document.querySelector('#photo-input').disabled);
  assert(await source.locator('#photo-transfer-status').getAttribute('role') === 'status', 'Transfer progress and recovery messages are announced as status');
  assert(await source.locator('#photo-restore-input').getAttribute('webkitdirectory') !== null && await source.locator('#photo-restore-input').getAttribute('multiple') !== null, 'Restore chooser accepts a complete backup directory');
  const base64 = await source.evaluate(() => {
    return Array.from({ length: 4 }, (_, index) => {
      const canvas = document.createElement('canvas'); canvas.width = 360; canvas.height = 240;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = `hsl(${30 + index * 73} 55% 60%)`; ctx.fillRect(0, 0, 360, 240);
      ctx.fillStyle = '#163344'; ctx.fillRect(35 + index * 7, 30, 180, 110);
      ctx.fillStyle = '#fff'; ctx.font = '20px sans-serif'; ctx.fillText(`Transfer fixture ${index}`, 20, 210);
      return canvas.toDataURL('image/png').split(',')[1];
    });
  });
  const images = base64.map((data, index) => ({ name: `transfer-view-${index}.png`, mimeType: 'image/png', buffer: Buffer.from(data, 'base64') }));
  const list = (page) => page.evaluate(async () => {
    const store = await window.CadPhotos.createStore();
    try { return await store.list({ page: 0, pageSize: 100 }); } finally { store.close(); }
  });
  const waitImportCount = (page, count) => page.waitForFunction((expected) => !document.querySelector('#photo-input').disabled && document.querySelector('#photo-progress').hidden && new RegExp('^' + expected + '\\s').test(document.querySelector('#photo-count').textContent), count);
  const waitTransfer = (page) => page.waitForFunction(() => document.querySelector('#photo-transfer-progress').hidden && !document.querySelector('#photo-restore-input').disabled);
  const newPage = async (init) => {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    if (init) await context.addInitScript(init);
    const page = await context.newPage(); watch(page);
    await page.goto(pageUrl);
    await page.waitForFunction(() => window.CadPhotoTransfer && !document.querySelector('#photo-input').disabled);
    return { context, page };
  };
  await source.locator('#photo-input').setInputFiles(images.slice(0, 3));
  await waitImportCount(source, 3);
  const expected = await source.evaluate(async () => {
    const store = await window.CadPhotos.createStore();
    try {
      const rows = (await store.list()).items.sort((a, b) => a.name.localeCompare(b.name));
      for (const [index, photo] of rows.entries()) {
        await store.update(photo.id, { viewpoint: ['front', 'left', 'back'][index], notes: `Synthetic portable note ${index}\nKnown surface <datum> — millimeters`,
          measurement: index === 0 ? { reference: [[20, 20], [120, 20]], target: [[20, 50], [70, 50]], knownMm: 10 } : null });
      }
      return (await store.exportManifest()).photos;
    } finally { store.close(); }
  });
  await source.reload();
  await waitImportCount(source, 3);
  await source.evaluate(async () => {
    const directory = await (await navigator.storage.getDirectory()).getDirectoryHandle('transfer-acceptance', { create: true });
    const sentinel = await (await directory.getFileHandle('keep-me.txt', { create: true })).createWritable();
    await sentinel.write('Unrelated destination content must remain unchanged.'); await sentinel.close();
    window.showDirectoryPicker = async () => (await navigator.storage.getDirectory()).getDirectoryHandle('transfer-acceptance', { create: true });
  });
  await source.locator('#photo-backup').click();
  await source.waitForFunction(async () => {
    try {
      const root = await (await navigator.storage.getDirectory()).getDirectoryHandle('transfer-acceptance');
      for await (const handle of root.values()) {
        if (handle.kind === 'directory') { try { await handle.getFileHandle('cad-photo-manifest.json'); return true; } catch {} }
      }
    } catch {}
    return false;
  });
  await waitTransfer(source);
  const exportedAll = await source.evaluate(async () => {
    const root = await (await navigator.storage.getDirectory()).getDirectoryHandle('transfer-acceptance');
    const files = [];
    async function visit(directory, prefix) {
      for await (const [name, handle] of directory.entries()) {
        const rel = prefix + name;
        if (handle.kind === 'directory') await visit(handle, rel + '/');
        else {
          const file = await handle.getFile();
          const bytes = new Uint8Array(await file.arrayBuffer());
          files.push({ path: rel, base64: btoa(Array.from(bytes, (value) => String.fromCharCode(value)).join('')), size: bytes.length });
        }
      }
    }
    await visit(root, ''); return files;
  });
  const manifestFiles = exportedAll.filter((file) => file.path.endsWith('/cad-photo-manifest.json'));
  assert(manifestFiles.length === 1, 'Backup writes one completed manifest inside a dedicated backup folder');
  const folderName = manifestFiles[0].path.split('/')[0];
  const exported = exportedAll.filter((file) => file.path.startsWith(folderName + '/'));
  const backupDir = path.join(fixtureRoot, 'portable', folderName);
  for (const file of exported) {
    assert(!file.path.startsWith('/') && !file.path.split('/').includes('..'), 'Exported relative path remains inside its backup folder: ' + file.path);
    const target = path.join(fixtureRoot, 'portable', file.path);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, Buffer.from(file.base64, 'base64'));
  }
  const manifest = JSON.parse(Buffer.from(manifestFiles[0].base64, 'base64').toString('utf8'));
  assert(manifest.photos.length === 3 && exported.filter((file) => /\/photos\/[a-f0-9]{64}\.png$/.test(file.path)).length === 3, 'Portable folder contains every original named by SHA-256 and its metadata');
  results.exported_file_count = exported.length;
  results.exported_bytes = exported.reduce((sum, file) => sum + file.size, 0);
  const repeatedExport = await source.evaluate(async () => {
    const store = await window.CadPhotos.createStore();
    try {
      const directory = await (await navigator.storage.getDirectory()).getDirectoryHandle('transfer-acceptance');
      const result = await window.CadPhotoTransfer.exportFolder(store, directory);
      const sentinel = await (await directory.getFileHandle('keep-me.txt')).getFile();
      return { result, sentinel: await sentinel.text() };
    } finally { store.close(); }
  });
  assert(repeatedExport.result.status === 'complete' && repeatedExport.result.folderName !== folderName && repeatedExport.sentinel === 'Unrelated destination content must remain unchanged.', 'Repeated backup chooses a distinct subfolder and preserves unrelated destination content');
  const csvDownloadPromise = source.waitForEvent('download');
  await source.locator('#photo-measurements-export').click();
  const csvDownload = await csvDownloadPromise;
  const csvText = fs.readFileSync(await csvDownload.path(), 'utf8');
  const csvRows = []; let row = [], cell = '', quoted = false;
  for (let index = 0; index < csvText.length; index++) {
    const character = csvText[index];
    if (character === '"' && quoted && csvText[index + 1] === '"') { cell += '"'; index++; }
    else if (character === '"') quoted = !quoted;
    else if (character === ',' && !quoted) { row.push(cell); cell = ''; }
    else if (character === '\n' && !quoted) { row.push(cell.replace(/\r$/, '')); csvRows.push(row); row = []; cell = ''; }
    else cell += character;
  }
  const expectedHeader = fs.readFileSync(path.join(ROOT, 'templates/measurement-register.csv'), 'utf8').split(/\r?\n/)[0];
  assert(csvDownload.suggestedFilename() === 'photo-measurement-register.csv' && csvRows[0].join(',') === expectedHeader, 'Measurement CSV download uses the repository measurement-register columns');
  assert(csvRows.length === 2 && csvRows[1][2] === 'image-derived' && Number(csvRows[1][3]) === 5 && [4, 5, 6, 9, 10].every((index) => csvRows[1][index] === ''), 'CSV exports the 5 mm image estimate with unknown physical readings, uncertainty, and acceptance criteria left blank');
  assert(csvRows[1][12].includes('SHA-256:') && csvRows[1][12].includes('not independently verified'), 'Measurement CSV retains photograph provenance and the unverified-reference qualification');
  await source.screenshot({ path: path.join(qa, 'photo-transfer-desktop.png'), fullPage: false });
  await source.setViewportSize({ width: 390, height: 844 });
  await source.locator('#photo-backup').scrollIntoViewIfNeeded();
  assert(await source.evaluate(() => document.documentElement.scrollWidth - innerWidth <= 1), 'Transfer controls fit a 390-pixel viewport without horizontal overflow');
  await source.screenshot({ path: path.join(qa, 'photo-transfer-mobile.png'), fullPage: false });

  const restored = await newPage();
  assert((await list(restored.page)).count === 0, 'Destination context starts with an empty photo workspace');
  await restored.page.locator('#photo-restore-input').setInputFiles(backupDir);
  await waitImportCount(restored.page, 3); await waitTransfer(restored.page);
  const roundtrip = await restored.page.evaluate(async () => {
    const store = await window.CadPhotos.createStore();
    try {
      const rows = (await store.exportManifest()).photos;
      const hashes = {};
      for (const photo of rows) {
        const original = await store.get(photo.id);
        hashes[photo.id] = [...new Uint8Array(await crypto.subtle.digest('SHA-256', await original.blob.arrayBuffer()))].map((value) => value.toString(16).padStart(2, '0')).join('');
      }
      return { rows, hashes };
    } finally { store.close(); }
  });
  const fields = ['id', 'name', 'type', 'size', 'width', 'height', 'addedAt', 'viewpoint', 'notes', 'measurement'];
  const normalize = (rows) => rows.map((photo) => Object.fromEntries(fields.map((field) => [field, photo[field]]))).sort((a, b) => a.id.localeCompare(b.id));
  assert(JSON.stringify(normalize(roundtrip.rows)) === JSON.stringify(normalize(expected)), 'Restoring in a separate browser context preserves names, viewpoints, notes, dimensions, and measurements');
  assert(roundtrip.rows.every((photo) => roundtrip.hashes[photo.id] === photo.id), 'Restored original bytes exactly match their recorded SHA-256 identities');
  const firstId = expected[0].id;
  await restored.page.evaluate(async (id) => {
    const store = await window.CadPhotos.createStore();
    try { await store.update(id, { notes: 'Newer local annotation retained' }); } finally { store.close(); }
  }, firstId);
  await restored.page.locator('#photo-restore-input').setInputFiles(backupDir);
  await waitTransfer(restored.page);
  const afterDuplicate = await list(restored.page);
  assert(afterDuplicate.count === 3 && afterDuplicate.items.find((photo) => photo.id === firstId).notes === 'Newer local annotation retained', 'Repeated restoration skips duplicates and preserves newer local annotations');
  assert(/duplicate|existing|kept|skip/i.test(await restored.page.locator('#photo-transfer-status').innerText()), 'Duplicate restoration explains the keep-existing policy');

  // Make damaged copies from generated fixtures only. Each gets an empty browser
  // context, preventing a previous successful restore from masking bad inputs.
  const originalRelative = exported.find((file) => /\/photos\/[a-f0-9]{64}\.png$/.test(file.path)).path.split('/').slice(1).join('/');
  const damagedPhotoId = path.basename(originalRelative, '.png');
  for (const kind of ['missing-manifest', 'missing-original', 'tampered-original', 'wrong-dimensions']) {
    const directory = path.join(fixtureRoot, kind);
    fs.cpSync(backupDir, directory, { recursive: true });
    if (kind === 'missing-manifest') fs.rmSync(path.join(directory, 'cad-photo-manifest.json'));
    if (kind === 'missing-original') fs.rmSync(path.join(directory, originalRelative));
    if (kind === 'tampered-original') fs.writeFileSync(path.join(directory, originalRelative), images[3].buffer);
    if (kind === 'wrong-dimensions') {
      const altered = structuredClone(manifest);
      altered.photos.find((photo) => photo.id === damagedPhotoId).width += 1;
      fs.writeFileSync(path.join(directory, 'cad-photo-manifest.json'), JSON.stringify(altered));
    }
    const damaged = await newPage();
    await damaged.page.locator('#photo-restore-input').setInputFiles(directory);
    await waitTransfer(damaged.page);
    const data = await list(damaged.page);
    const status = await damaged.page.locator('#photo-transfer-status').innerText();
    assert(data.count < 3 && !data.items.some((photo) => photo.id === damagedPhotoId), `${kind}: incomplete or altered photo evidence is not admitted as a complete backup`);
    assert(!/^Restore complete/i.test(status), `${kind}: failed restore never claims completion`);
    assert(/manifest|missing|match|failed|incomplete|invalid|could not|error|mismatch|fingerprint/i.test(status), `${kind}: restoration reports why the backup could not complete`);
    if (kind === 'missing-manifest') assert(data.count === 0, 'Missing manifest restores no untracked images');
    await damaged.context.close();
  }
  const renamedDir = path.join(fixtureRoot, 'renamed-original');
  fs.cpSync(backupDir, renamedDir, { recursive: true });
  fs.renameSync(path.join(renamedDir, originalRelative), path.join(renamedDir, 'photos', 'renamed-but-identical.bin'));
  fs.writeFileSync(path.join(renamedDir, 'README.txt'), 'Synthetic unrelated folder note.');
  const renamed = await newPage();
  await renamed.page.evaluate(() => {
    document.querySelector('#photo-restore-input').addEventListener('change', (event) => {
      window.selectedRestoreTypes = [...event.target.files].map((file) => ({ name: file.name, type: file.type }));
    }, { capture: true });
  });
  await renamed.page.locator('#photo-restore-input').setInputFiles(renamedDir);
  await waitImportCount(renamed.page, 3); await waitTransfer(renamed.page);
  const renamedMime = await renamed.page.evaluate(() => window.selectedRestoreTypes.find((file) => file.name === 'renamed-but-identical.bin').type);
  assert(renamedMime === '' || /octet-stream/i.test(renamedMime), 'Generic-name restore fixture arrives with an empty or generic MIME type');
  results.renamed_original_mime = renamedMime;
  assert((await list(renamed.page)).items.some((photo) => photo.id === damagedPhotoId), 'Restoration matches an unchanged original by SHA-256 even with a generic .bin filename and MIME');
  assert(/^Restore complete/i.test(await renamed.page.locator('#photo-transfer-status').innerText()), 'Unrelated non-photo files do not make an otherwise complete restoration appear incomplete');
  await renamed.context.close();

  const cancellation = await source.evaluate(async () => {
    const store = await window.CadPhotos.createStore();
    const parent = await (await navigator.storage.getDirectory()).getDirectoryHandle('cancelled-transfer', { create: true });
    let stop = false;
    const progress = [];
    try {
      const result = await window.CadPhotoTransfer.exportFolder(store, parent, {
        onProgress(event) { progress.push(event); if (event.processed >= 1) stop = true; },
        shouldCancel() { return stop; },
      });
      const files = [];
      async function visit(directory, prefix) {
        for await (const [name, handle] of directory.entries()) {
          if (handle.kind === 'directory') await visit(handle, prefix + name + '/');
          else files.push(prefix + name);
        }
      }
      await visit(parent, ''); return { result, files, progress };
    } finally { store.close(); }
  });
  assert(cancellation.result.status === 'cancelled', 'Export cancellation is reported distinctly from successful backup');
  assert(cancellation.files.some((file) => /\/photos\//.test(file)) && !cancellation.files.some((file) => file.endsWith('/cad-photo-manifest.json')), 'Cancelled partial export contains no completion manifest');
  results.cancelled_export = cancellation.result;

  const stopped = await newPage();
  await stopped.page.evaluate(() => {
    window.originalFileText = File.prototype.text;
    File.prototype.text = async function () {
      if (/\.json$/i.test(this.name)) await new Promise((resolve) => { window.releaseManifestRead = resolve; });
      return window.originalFileText.call(this);
    };
  });
  await stopped.page.locator('#photo-restore-input').setInputFiles(backupDir);
  await stopped.page.waitForFunction(() => typeof window.releaseManifestRead === 'function');
  assert(await stopped.page.locator('#photo-input').isDisabled() && await stopped.page.locator('#photo-restore-input').isDisabled(), 'Active restoration prevents competing imports and restorations');
  await stopped.page.locator('#photo-transfer-cancel').click();
  await stopped.page.evaluate(() => { File.prototype.text = window.originalFileText; window.releaseManifestRead(); });
  await waitTransfer(stopped.page);
  assert((await list(stopped.page)).count === 0 && /Restore stopped/i.test(await stopped.page.locator('#photo-transfer-status').innerText()), 'Transfer stop control cancels pending restoration without claiming completion');
  await stopped.page.locator('#photo-restore-input').setInputFiles(backupDir);
  await waitImportCount(stopped.page, 3); await waitTransfer(stopped.page);
  assert((await list(stopped.page)).count === 3, 'A cancelled restore can be retried using the same backup folder');
  await stopped.context.close();

  const quota = await newPage();
  await quota.page.locator('#photo-input').setInputFiles(images[3]);
  await waitImportCount(quota.page, 1);
  const preservedId = (await list(quota.page)).items[0].id;
  await quota.page.evaluate(() => {
    window.originalAdd = IDBObjectStore.prototype.add;
    let records = 0;
    IDBObjectStore.prototype.add = function (...args) {
      if (this.name === 'metadata' && ++records > 1) throw new DOMException('Synthetic restoration quota exhausted', 'QuotaExceededError');
      return window.originalAdd.apply(this, args);
    };
  });
  await quota.page.locator('#photo-restore-input').setInputFiles(backupDir);
  await waitTransfer(quota.page);
  await quota.page.evaluate(() => { IDBObjectStore.prototype.add = window.originalAdd; });
  const afterQuota = await list(quota.page);
  assert(afterQuota.count === 2 && afterQuota.items.some((photo) => photo.id === preservedId), 'Quota failure after one restored photo retains both the earlier workspace and the completed restoration');
  const quotaIntegrity = await quota.page.evaluate(async () => {
    const store = await window.CadPhotos.createStore();
    try {
      for (const photo of (await store.list()).items) {
        const saved = await store.get(photo.id);
        if (!saved.blob || !saved.thumbnail) return false;
        const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', await saved.blob.arrayBuffer()))].map((value) => value.toString(16).padStart(2, '0')).join('');
        if (hash !== photo.id) return false;
      }
      return true;
    } finally { store.close(); }
  });
  assert(quotaIntegrity, 'Quota-interrupted restoration leaves no metadata record without its intact original and thumbnail');
  assert(/storage|space|full|quota/i.test(await quota.page.locator('#photo-transfer-errors').innerText()), 'Restoration quota failure provides storage recovery guidance');
  await quota.context.close();

  const unavailable = await newPage(() => { window.showDirectoryPicker = undefined; });
  await unavailable.page.locator('#photo-input').setInputFiles(images[0]);
  await waitImportCount(unavailable.page, 1);
  if (!await unavailable.page.locator('#photo-backup').isDisabled()) await unavailable.page.locator('#photo-backup').click();
  assert(/not available|not supported|does not support|Chrome|Edge|supported browser|cannot choose|unavailable/i.test(await unavailable.page.locator('#photos').innerText()), 'Browsers without a native folder picker explain the backup limitation');
  await unavailable.context.close();
  const deniedPicker = await newPage(() => {
    window.showDirectoryPicker = async () => { throw new DOMException('Synthetic browser picker restriction', 'SecurityError'); };
  });
  await deniedPicker.page.locator('#photo-input').setInputFiles(images[0]);
  await waitImportCount(deniedPicker.page, 1);
  await deniedPicker.page.locator('#photo-backup').click();
  await waitTransfer(deniedPicker.page);
  const deniedStatus = await deniedPicker.page.locator('#photo-transfer-status').innerText();
  assert(!/Backup saved/i.test(deniedStatus) && (await list(deniedPicker.page)).count === 1, 'Browser-denied folder access never reports a completed backup or changes saved photos');
  assert(/manifest|localhost|secure|browser|blocked|permission/i.test(deniedStatus), 'Denied folder access offers a usable browser or manual-backup recovery path');
  await deniedPicker.context.close();

  // Exercise only controller timing with a synthetic store on an independent
  // page. The main backup/restore pipeline above continues to use real storage.
  const racePage = await sourceContext.newPage(); watch(racePage);
  await racePage.setContent(fs.readFileSync(path.join(ROOT, 'assets/photo-workspace.html'), 'utf8').replace('tabindex="-1" hidden', 'tabindex="-1"'));
  await racePage.evaluate(async () => {
    const canvas = document.createElement('canvas'); canvas.width = 360; canvas.height = 240;
    const blob = await new Promise((resolve) => canvas.toBlob(resolve));
    const photo = { id: 'a'.repeat(64), name: 'race-synthetic.png', width: 360, height: 240, size: blob.size, viewpoint: 'unassigned', notes: '', measurement: null, blob };
    let initialThumbnail = true;
    const store = {
      list: async () => ({ items: [photo], count: 1, total: 1, bytes: blob.size, viewpoints: { unassigned: 1 } }),
      thumbnail: () => {
        if (!initialThumbnail) return Promise.resolve(blob);
        initialThumbnail = false;
        return new Promise((resolve) => { window.releaseThumbnail = () => resolve(blob); });
      },
      get: () => new Promise((resolve) => { window.releasePhoto = () => resolve({ ...photo }); }),
    };
    window.CadPhotos = { VIEWPOINTS: ['unassigned', 'front'], createStore: async () => store, estimate: () => ({ estimatedMm: 1, warnings: [] }) };
    window.CadPhotoTransfer = { exportFolder: async () => { throw new Error('The race harness must cancel the synthetic picker before exporting.'); } };
    window.showDirectoryPicker = () => new Promise((resolve, reject) => { window.rejectPicker = reject; });
  });
  await racePage.addScriptTag({ content: fs.readFileSync(path.join(ROOT, 'assets/js/photo-workspace.js'), 'utf8') });
  await racePage.waitForFunction(() => typeof window.releaseThumbnail === 'function');
  await racePage.locator('#photo-backup').click();
  await racePage.waitForFunction(() => typeof window.rejectPicker === 'function');
  await racePage.evaluate(() => window.releaseThumbnail());
  await racePage.locator('#photo-grid .photo-card').waitFor({ state: 'visible' });
  assert(await racePage.locator('#photo-grid .photo-card').isDisabled() && !await racePage.locator('#photo-transfer-progress').evaluate((progress) => progress.hidden), 'A gallery render finishing after backup starts keeps newly inserted photo cards disabled');
  await racePage.evaluate(() => { window.rejectPicker(new DOMException('Synthetic picker cancellation', 'AbortError')); window.rejectPicker = null; });
  await waitTransfer(racePage);
  await racePage.locator('#photo-grid .photo-card').click();
  await racePage.waitForFunction(() => typeof window.releasePhoto === 'function');
  await racePage.locator('#photo-backup').click();
  await racePage.waitForFunction(() => typeof window.rejectPicker === 'function');
  await racePage.evaluate(async () => {
    window.releasePhoto();
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  assert(!await racePage.locator('#photo-detail').evaluate((dialog) => dialog.open) && !await racePage.locator('#photo-transfer-progress').evaluate((progress) => progress.hidden), 'A pending photo open cannot expose an editable dialog after backup has begun');
  await racePage.evaluate(() => { window.rejectPicker(new DOMException('Synthetic picker cancellation', 'AbortError')); window.rejectPicker = null; });
  await waitTransfer(racePage);
  await racePage.close();
  await restored.context.close();
  assert(results.browser_errors.length === 0, 'No browser script or console errors during backup and restoration');
  results.status = 'passed'; record();
  console.log(JSON.stringify({ status: results.status, checks: results.checks.length, evidence: qaFile }, null, 2));
} catch (error) {
  results.status = 'failed'; results.error = error.message; record();
  console.error(error); process.exitCode = 1;
} finally {
  try {
    if (browser) await browser.close();
  } finally {
    await served?.close();
  }
}
