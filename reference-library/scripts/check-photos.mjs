// Isolated browser acceptance checks for the local photo workspace.
// Synthetic canvas images only; never reads the user's photographs or browser profile.
//   node scripts/check-photos.mjs
// Opens index.html from file:// by default, or over a private loopback HTTP server when
// CAD_REFERENCE_BROWSER_TRANSPORT=http (see scripts/lib/serve.mjs). Browser storage is
// per origin, so an HTTP result does not establish that file:// storage works.
import fs from 'node:fs';
import path from 'node:path';
import { ROOT, requireModule, findChrome, readJSON } from './lib/runtime.mjs';
import { browserTransport, openTransport } from './lib/serve.mjs';

const { chromium } = requireModule('playwright');
const qa = path.join(ROOT, 'tmp/qa');
const qaFile = path.join(qa, 'photo-check.json');
const results = {
  checked_at: new Date().toISOString(), revision: readJSON('library.json').revision,
  status: 'running', transport: process.env.CAD_REFERENCE_BROWSER_TRANSPORT || 'file', checks: [], browser_errors: [],
  scope: 'Isolated Chromium profile; synthetic PNG fixtures only. Multi-batch imports, durable browser storage, SHA-256 deduplication, paging, metadata, same-plane estimates, export, deletion, invalid files, quota failure, and responsive layout. This is not a 3D reconstruction or real-object accuracy benchmark.',
};
fs.mkdirSync(qa, { recursive: true });
fs.rmSync(qaFile, { force: true });
const record = () => fs.writeFileSync(qaFile, JSON.stringify({ ...results, check_count: results.checks.length }, null, 2) + '\n');
const assert = (value, label) => {
  if (!value) throw new Error(`FAILED: ${label}`);
  results.checks.push(label);
};
let browser;
let served;
try {
  results.transport = browserTransport();
  served = await openTransport(results.transport);
  results.page_url = served.pageUrl;
  browser = await chromium.launch({ headless: true, executablePath: findChrome() });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, acceptDownloads: true });
  const page = await context.newPage();
  const dialogs = [];
  page.on('pageerror', (error) => results.browser_errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') results.browser_errors.push(message.text()); });
  page.on('dialog', async (dialog) => { dialogs.push(dialog.message()); await dialog.dismiss(); });
  const pageUrl = served.pageUrl + '#photos';
  await page.goto(pageUrl);
  await page.waitForFunction(() => window.CadPhotos && document.querySelector('#photos') && !document.querySelector('#photo-input').disabled);
  assert(await page.locator('#photos').isVisible(), 'Photo workspace opens directly from its hash');
  assert(await page.locator('#photo-input').getAttribute('multiple') !== null, 'File chooser accepts multiple photographs');
  const accept = await page.locator('#photo-input').getAttribute('accept');
  assert(/png/i.test(accept) && /jpe?g/i.test(accept) && /webp/i.test(accept), 'File chooser advertises supported raster formats');
  const readList = () => page.evaluate(async () => {
    const store = await window.CadPhotos.createStore();
    try { return await store.list({ page: 0, pageSize: 24 }); } finally { store.close(); }
  });
  const waitCount = async (count) => {
    await page.waitForFunction(async (expected) => {
      const store = await window.CadPhotos.createStore();
      try { return (await store.list({ page: 0, pageSize: 24 })).count === expected; } finally { store.close(); }
    }, count);
    await page.waitForFunction((expected) => !document.querySelector('#photo-input').disabled && document.querySelector('#photo-progress').hidden && new RegExp('^' + expected + '\\s').test(document.querySelector('#photo-count').textContent), count);
  };
  const fixtureBase64 = await page.evaluate(async () => {
    const out = [];
    for (let n = 0; n < 34; n++) {
      const canvas = document.createElement('canvas'); canvas.width = 320; canvas.height = 240;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = `hsl(${n * 37 % 360} 55% 55%)`; ctx.fillRect(0, 0, 320, 240);
      ctx.fillStyle = '#102235'; ctx.fillRect(30 + n, 35, 120, 120);
      ctx.fillStyle = '#fff'; ctx.font = '20px sans-serif'; ctx.fillText(`Synthetic view ${n}`, 24, 218);
      out.push(canvas.toDataURL('image/png').split(',')[1]);
    }
    return out;
  });
  const fixtures = fixtureBase64.map((data, index) => ({ name: `synthetic-view-${String(index).padStart(2, '0')}.png`, mimeType: 'image/png', buffer: Buffer.from(data, 'base64') }));
  await page.locator('#photo-input').setInputFiles(fixtures.slice(0, 30));
  await waitCount(30);
  assert((await readList()).count === 30, 'First batch saves 30 distinct synthetic photographs');
  assert(/30/.test(await page.locator('#photo-count').innerText()), 'Saved-photo count reflects the full collection');
  assert(await page.locator('#photo-grid .photo-card').count() === 24, 'First gallery page renders 24 cards for a larger collection');
  await page.locator('#photo-next').click();
  await page.waitForFunction(() => document.querySelectorAll('#photo-grid .photo-card').length === 6);
  assert(await page.locator('#photo-grid .photo-card').count() === 6, 'Next page reaches the six remaining photographs');
  await page.locator('#photo-prev').click();
  await page.waitForFunction(() => document.querySelectorAll('#photo-grid .photo-card').length === 24);
  await page.locator('#photo-input').setInputFiles([fixtures[30], fixtures[31], fixtures[0], fixtures[1]]);
  await waitCount(32);
  const importStatus = await page.locator('#photo-status').innerText();
  assert(/duplicate/i.test(importStatus) && /2/.test(importStatus), 'Later batches add new photographs and report duplicate content');
  assert((await readList()).count === 32, 'Multiple imports retain earlier photographs across gallery pages');
  await page.reload();
  await waitCount(32);
  assert(/32/.test(await page.locator('#photo-count').innerText()), 'Reload restores all saved photographs');
  const listing = await readList();
  assert(!JSON.stringify(listing).includes('data:image') && listing.items.every((item) => !('original' in item) && !('blob' in item)), 'Collection listing contains metadata without original image payloads');
  const originalRetained = await page.evaluate(async () => {
    const store = await window.CadPhotos.createStore();
    try {
      const listing = await store.list();
      const photo = await store.get(listing.items[0].id);
      const digest = await crypto.subtle.digest('SHA-256', await photo.blob.arrayBuffer());
      const hash = [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
      return photo.blob instanceof Blob && photo.thumbnail instanceof Blob && hash === photo.id && photo.blob.size === photo.size;
    } finally { store.close(); }
  });
  assert(originalRetained, 'Stored original bytes retain their SHA-256 fingerprint separately from the thumbnail');
  await page.locator('#photo-search').fill('synthetic-view-00');
  await page.waitForFunction(() => document.querySelectorAll('#photo-grid .photo-card').length === 1);
  assert(await page.locator('#photo-grid .photo-card').count() === 1, 'Filename search filters the photo collection');
  await page.locator('#photo-grid .photo-card').first().click();
  await page.locator('#photo-detail').waitFor({ state: 'visible' });
  assert(await page.locator('#photo-detail').isVisible(), 'Selecting a photograph opens the metadata and measurement dialog');
  const hostileNotes = '<img src=x onerror="window.__photoInjected = true"> front face synthetic datum';
  await page.locator('#photo-viewpoint').selectOption('front');
  await page.locator('#photo-notes').fill(hostileNotes);
  await page.locator('#photo-known-mm').fill('10');
  await page.locator('#photo-image').evaluate((image) => image.decode());
  const clickImagePoint = async (x, y) => {
    const box = await page.locator('#photo-image').boundingBox();
    await page.locator('#photo-image').click({ position: { x: box.width * x / 320, y: box.height * y / 240 } });
  };
  await page.locator('#photo-reference-points').click();
  await clickImagePoint(20, 20); await clickImagePoint(120, 20);
  await page.locator('#photo-target-points').click();
  await clickImagePoint(20, 50); await clickImagePoint(70, 50);
  const picked = await page.evaluate(() => {
    const ids = ['ref-x1', 'ref-y1', 'ref-x2', 'ref-y2', 'target-x1', 'target-y1', 'target-x2', 'target-y2'];
    const values = ids.map((id) => Number(document.querySelector('#photo-' + id).value));
    const measurement = { reference: [values.slice(0, 2), values.slice(2, 4)], target: [values.slice(4, 6), values.slice(6, 8)], knownMm: 10 };
    return { values, estimatedMm: window.CadPhotos.estimate(measurement, 320, 240).estimatedMm };
  });
  const intended = [20, 20, 120, 20, 20, 50, 70, 50];
  assert(picked.values.every((value, index) => Math.abs(value - intended[index]) < 1.2), 'Four image clicks map rendered positions into original-image pixel coordinates');
  assert(Math.abs(picked.estimatedMm - 5) < 0.1 && await page.locator('#photo-overlay circle').count() === 4, 'Pointer-picked reference and target produce the expected scale estimate and endpoint overlay');
  results.pointer_measurement_mm = picked.estimatedMm;
  await page.screenshot({ path: path.join(qa, 'photos-measurement.png'), fullPage: false });
  await page.locator('#photo-detail .photo-coordinates summary').click();
  for (const [id, value] of Object.entries({ 'ref-x1': 20, 'ref-y1': 20, 'ref-x2': 120, 'ref-y2': 20, 'target-x1': 20, 'target-y1': 50, 'target-x2': 70, 'target-y2': 50 })) {
    await page.locator('#photo-' + id).fill(String(value));
  }
  await page.locator('#photo-target-y2').blur();
  await page.waitForFunction(() => /5(?:\.0+)?\s*mm/.test(document.querySelector('#photo-estimate').textContent));
  assert(/5(?:\.0+)?\s*mm/.test(await page.locator('#photo-estimate').innerText()), 'A 100-pixel reference of 10 mm and 50-pixel target estimate 5 mm');
  await page.locator('#photo-ref-x2').fill('900');
  await page.locator('#photo-ref-x2').blur();
  await page.locator('#photo-save').click();
  assert(await page.locator('#photo-detail').isVisible(), 'Out-of-image coordinates are rejected before saving');
  assert(!/5(?:\.0+)?\s*mm/.test(await page.locator('#photo-estimate').innerText()), 'Invalid coordinates do not leave a usable estimate');
  await page.locator('#photo-ref-x2').fill('120');
  await page.locator('#photo-ref-x2').blur();
  await page.locator('#photo-save').click();
  await page.locator('#photo-detail').waitFor({ state: 'hidden' });
  assert(await page.evaluate(() => !window.__photoInjected), 'Photo notes are treated as text, never executable markup');
  await page.locator('#photo-search').fill('');
  await page.locator('#photo-filter').selectOption('front');
  await page.waitForFunction(() => document.querySelectorAll('#photo-grid .photo-card').length === 1);
  assert(await page.locator('#photo-grid .photo-card').count() === 1, 'Viewpoint labels filter the collection');
  await page.locator('#photo-grid .photo-card').click();
  assert(await page.locator('#photo-notes').inputValue() === hostileNotes && await page.locator('#photo-viewpoint').inputValue() === 'front', 'Labels and notes persist when reopening the photograph');
  await page.locator('#photo-close').click();
  await page.locator('#photo-filter').selectOption('');
  await page.locator('#photo-search').fill('front face synthetic datum');
  await page.waitForFunction(() => document.querySelectorAll('#photo-grid .photo-card').length === 1);
  assert(await page.locator('#photo-grid .photo-card').count() === 1, 'Saved notes are searchable');
  await page.locator('#photo-search').fill('');
  await page.waitForFunction(() => document.querySelectorAll('#photo-grid .photo-card').length === 24);
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#photo-export').click();
  const download = await downloadPromise;
  const downloadPath = await download.path();
  const manifestText = fs.readFileSync(downloadPath, 'utf8');
  const manifest = JSON.parse(manifestText);
  assert(!manifestText.includes('data:image') && !manifestText.includes('"blob"') && !manifestText.includes('"original"'), 'Downloaded manifest excludes original images and thumbnail blobs');
  assert(/[a-f0-9]{64}/.test(manifestText), 'Manifest records SHA-256 photograph identifiers');
  assert(manifestText.includes('front face synthetic datum') && /measurement|reference/i.test(manifestText), 'Manifest includes saved labels, notes, and measurement evidence');
  results.manifest_bytes = Buffer.byteLength(manifestText);
  results.manifest_top_level_keys = Object.keys(manifest);
  await page.screenshot({ path: path.join(qa, 'photos-desktop.png'), fullPage: false });

  // Concurrent insertion and quota failures use the public storage API and the same
  // synthetic browser database. A second store handle exercises cross-client races.
  const storageChecks = await page.evaluate(async ({ concurrentData, quotaData }) => {
    const file = async (data, name) => new File([await (await fetch('data:image/png;base64,' + data)).blob()], name, { type: 'image/png' });
    const storeA = await window.CadPhotos.createStore();
    const storeB = await window.CadPhotos.createStore();
    try {
      const prepared = await window.CadPhotos.prepareFile(await file(concurrentData, 'concurrent.png'));
      const before = await storeA.list({ page: 0, pageSize: 24 });
      const writes = await Promise.all([storeA.put(prepared), storeB.put(prepared)]);
      const after = await storeA.list({ page: 0, pageSize: 24 });
      const quotaPrepared = await window.CadPhotos.prepareFile(await file(quotaData, 'quota.png'));
      const originalAdd = IDBObjectStore.prototype.add;
      const originalPut = IDBObjectStore.prototype.put;
      let rejected = false; let message = '';
      try {
        IDBObjectStore.prototype.add = IDBObjectStore.prototype.put = function () { throw new DOMException('Synthetic quota exhausted', 'QuotaExceededError'); };
        await storeA.put(quotaPrepared);
      } catch (error) { rejected = true; message = error.message; }
      finally { IDBObjectStore.prototype.add = originalAdd; IDBObjectStore.prototype.put = originalPut; }
      const afterQuota = await storeA.list({ page: 0, pageSize: 24 });
      const samePlane = JSON.stringify(await storeA.exportManifest());
      return { beforeCount: before.count, afterCount: after.count, afterQuotaCount: afterQuota.count, added: writes.filter((value) => value.added).length, quotaRejected: rejected, quotaMessage: message, savedMetadataRetained: samePlane.includes('front face synthetic datum') };
    } finally { storeA.close(); storeB.close(); }
  }, { concurrentData: fixtureBase64[32], quotaData: fixtureBase64[33] });
  assert(storageChecks.afterCount === storageChecks.beforeCount + 1 && storageChecks.added === 1, 'Concurrent duplicate imports commit one photograph atomically');
  assert(storageChecks.quotaRejected && storageChecks.afterQuotaCount === storageChecks.afterCount && storageChecks.savedMetadataRetained, 'Simulated quota failure rejects the new photo while retaining saved photos and metadata');
  assert(/storage|space|quota|full/i.test(storageChecks.quotaMessage), 'Quota failure explains the storage problem');
  results.storage_checks = storageChecks;

  await page.reload();
  await waitCount(33);
  await page.locator('#photo-input').setInputFiles([
    { name: 'not-a-photo.txt', mimeType: 'text/plain', buffer: Buffer.from('Synthetic unsupported text fixture') },
    { name: 'broken-photo.png', mimeType: 'image/png', buffer: Buffer.from('Synthetic corrupt image fixture') },
  ]);
  await page.waitForFunction(() => !document.querySelector('#photo-input').disabled && document.querySelector('#photo-progress').hidden && /could not|failed|unsupported|error/i.test(document.querySelector('#photo-status').textContent));
  assert((await readList()).count === 33, 'Unsupported and corrupt inputs leave the existing collection intact');
  const failureText = await page.locator('#photos').innerText();
  assert(/not-a-photo\.txt/.test(failureText) && /broken-photo\.png/.test(failureText), 'Import failures identify each rejected filename');
  assert(/PNG|JPEG|WebP|supported|decode|valid|corrupt/i.test(failureText), 'Import errors provide a usable file-format or decoding explanation');
  await page.screenshot({ path: path.join(qa, 'photos-errors.png'), fullPage: false });
  await page.locator('#photo-search').fill('synthetic-view-00');
  await page.waitForFunction(() => document.querySelectorAll('#photo-grid .photo-card').length === 1);
  await page.locator('#photo-grid .photo-card').click();
  page.removeAllListeners('dialog');
  page.once('dialog', async (dialog) => { assert(dialog.type() === 'confirm', 'Removing a saved photograph asks for explicit confirmation'); await dialog.accept(); });
  await page.locator('#photo-remove').click();
  await page.locator('#photo-detail').waitFor({ state: 'hidden' });
  await waitCount(32);
  assert(await page.locator('#photo-grid .photo-card').count() === 0, 'Deleting one photograph updates the filtered gallery');
  await page.locator('#photo-search').fill('');
  await page.reload();
  await waitCount(32);
  assert((await readList()).count === 32, 'Individual deletion persists across reloads');
  assert(dialogs.length === 0 && await page.evaluate(() => !window.__photoInjected), 'Imports and stored metadata raise no unexpected dialogs or script execution');
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.evaluate(() => { localStorage.removeItem('cad-theme'); delete document.documentElement.dataset.theme; });
  await page.reload();
  await waitCount(32);
  await page.screenshot({ path: path.join(qa, 'photos-dark.png'), fullPage: false });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth <= 1), 'Photo gallery has no horizontal overflow at 390 pixels');
  await page.screenshot({ path: path.join(qa, 'photos-mobile.png'), fullPage: false });
  await page.locator('#photo-grid .photo-card').first().click();
  await page.locator('#photo-detail').waitFor({ state: 'visible' });
  assert(await page.evaluate(() => {
    const dialog = document.querySelector('#photo-detail');
    return document.documentElement.scrollWidth - innerWidth <= 1 && dialog.scrollWidth <= dialog.clientWidth + 1;
  }), 'Photo detail dialog has no horizontal overflow at 390 pixels');
  await page.screenshot({ path: path.join(qa, 'photos-mobile-detail.png'), fullPage: false });

  // A separate ephemeral browser context keeps drag/drop cancellation independent
  // from the main persistence checks and from any real user browser profile.
  const dropContext = await browser.newContext({ viewport: { width: 1200, height: 900 } });
  const dropPage = await dropContext.newPage();
  dropPage.on('pageerror', (error) => results.browser_errors.push(error.message));
  dropPage.on('console', (message) => { if (message.type() === 'error') results.browser_errors.push(message.text()); });
  await dropPage.goto(pageUrl);
  await dropPage.waitForFunction(() => !document.querySelector('#photo-input').disabled);
  await dropPage.locator('#photo-input').setInputFiles(fixtures.slice(0, 2));
  await dropPage.waitForFunction(() => !document.querySelector('#photo-input').disabled && /^2\s/.test(document.querySelector('#photo-count').textContent));
  await dropPage.evaluate(async (data) => {
    const transfer = new DataTransfer();
    data.forEach((base64, index) => {
      const bytes = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
      transfer.items.add(new File([bytes], `dropped-${index}.png`, { type: 'image/png' }));
    });
    document.querySelector('#photo-drop-zone').dispatchEvent(new DragEvent('drop', { dataTransfer: transfer, bubbles: true, cancelable: true }));
    // The import handler starts in a microtask and yields while preparing its
    // first image. Cancel at that deterministic boundary, without timing sleeps.
    await Promise.resolve();
    document.querySelector('#photo-cancel').click();
  }, fixtureBase64.slice(2, 12));
  await dropPage.waitForFunction(() => !document.querySelector('#photo-input').disabled && /cancelled/i.test(document.querySelector('#photo-status').textContent));
  const cancelledCount = await dropPage.evaluate(async () => {
    const store = await window.CadPhotos.createStore();
    try { return (await store.list()).count; } finally { store.close(); }
  });
  assert(cancelledCount > 2 && cancelledCount < 12, 'Dropped batch can be cancelled after the active file while retaining already saved photos');
  assert(/not processed|continue/i.test(await dropPage.locator('#photo-status').innerText()), 'Cancelled import explains how to continue with remaining files');
  await dropPage.locator('#photo-input').setInputFiles(fixtures.slice(2, 12));
  await dropPage.waitForFunction(() => !document.querySelector('#photo-input').disabled && /^12\s/.test(document.querySelector('#photo-count').textContent));
  assert(/duplicate/i.test(await dropPage.locator('#photo-status').innerText()), 'Reselecting a cancelled batch resumes safely and skips previously saved content');
  results.drop_cancel_saved_count = cancelledCount;
  await dropContext.close();

  const blockedContext = await browser.newContext();
  await blockedContext.addInitScript(() => {
    IDBFactory.prototype.open = function () { throw new DOMException('Synthetic browser storage restriction', 'SecurityError'); };
  });
  const blockedPage = await blockedContext.newPage();
  blockedPage.on('pageerror', (error) => results.browser_errors.push(error.message));
  blockedPage.on('console', (message) => { if (message.type() === 'error') results.browser_errors.push(message.text()); });
  await blockedPage.goto(pageUrl);
  await blockedPage.waitForFunction(() => /blocked|unavailable/i.test(document.querySelector('#photo-status').textContent));
  assert(await blockedPage.locator('#photo-input').isDisabled(), 'Browser storage restrictions disable importing before any photos are accepted');
  assert(/storage|localhost|browser/i.test(await blockedPage.locator('#photo-status').innerText()), 'Unavailable storage has visible recovery guidance');
  await blockedContext.close();

  // Hold mutations at the storage boundary to exercise switching photos while a
  // save or removal is pending. This fixture runs the real controller against a
  // tiny synthetic store and does not alter the main IndexedDB acceptance case.
  const racePage = await context.newPage();
  racePage.on('pageerror', (error) => results.browser_errors.push(error.message));
  racePage.on('console', (message) => { if (message.type() === 'error') results.browser_errors.push(message.text()); });
  await racePage.setContent(fs.readFileSync(path.join(ROOT, 'assets/photo-workspace.html'), 'utf8').replace('tabindex="-1" hidden', 'tabindex="-1"'));
  await racePage.evaluate(async () => {
    const canvas = document.createElement('canvas'); canvas.width = 320; canvas.height = 240;
    const blob = await new Promise((resolve) => canvas.toBlob(resolve));
    const rows = ['a', 'b'].map((name) => ({ id: name, name: name + '.png', width: 320, height: 240, size: blob.size, viewpoint: 'unassigned', notes: '', measurement: null, blob }));
    const store = {
      list: async () => ({ items: rows, count: 2, total: 2, bytes: 14, viewpoints: { unassigned: 2 } }),
      get: async (id) => ({ ...rows.find((photo) => photo.id === id) }), thumbnail: async () => blob,
      update: (id, patch) => new Promise((resolve) => { window.pendingMutation = resolve; window.savedSnapshot = patch; }),
      remove: () => new Promise((resolve) => { window.pendingMutation = resolve; }),
    };
    window.CadPhotos = { VIEWPOINTS: ['unassigned', 'front'], createStore: async () => store, estimate: () => ({ estimatedMm: 1, warnings: [] }) };
    window.confirm = () => true;
  });
  // Record every image source and every revoked blob URL. A lazily loaded image whose
  // URL is revoked before its fetch starts logs "Not allowed to load local resource"
  // (timing-dependent; it failed CI). The deterministic invariant: no image may keep,
  // or be given, a URL that has already been revoked.
  await racePage.evaluate(() => {
    const revoked = new Set(); const images = new Set(); window.staleImageSources = [];
    const source = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
    Object.defineProperty(HTMLImageElement.prototype, 'src', {
      configurable: true, get() { return source.get.call(this); },
      set(value) { images.add(this); if (revoked.has(String(value))) window.staleImageSources.push('assigned ' + value); source.set.call(this, value); },
    });
    const revoke = URL.revokeObjectURL.bind(URL);
    URL.revokeObjectURL = (url) => {
      revoked.add(url);
      for (const image of images) if (image.getAttribute('src') === url) window.staleImageSources.push('kept ' + url);
      revoke(url);
    };
  });
  await racePage.addScriptTag({ content: fs.readFileSync(path.join(ROOT, 'assets/js/photo-workspace.js'), 'utf8') });
  await racePage.locator('.photo-card').first().waitFor({ state: 'visible' });
  for (const action of ['photo-save', 'photo-remove']) {
    await racePage.locator('.photo-card').first().click();
    await racePage.locator('#photo-notes').fill('Original draft');
    await racePage.locator('#' + action).click();
    await racePage.waitForFunction(() => !!window.pendingMutation);
    assert(await racePage.locator('#photo-notes').isDisabled() && await racePage.locator('#photo-known-mm').isDisabled(), `${action}: details cannot change while the mutation is pending`);
    await racePage.locator('#photo-close').click();
    await racePage.locator('.photo-card').last().click();
    await racePage.locator('#photo-notes').fill('New draft on B');
    await racePage.evaluate(async () => {
      window.pendingMutation(); window.pendingMutation = null;
      // The controller awaits its store and a refresh; flush that async work.
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    assert(await racePage.locator('#photo-detail').evaluate((dialog) => dialog.open) && await racePage.locator('#photo-notes').inputValue() === 'New draft on B', `${action}: late completion preserves a different photograph's open draft`);
    await racePage.locator('#photo-close').click();
  }
  // Overlapping refreshes: a superseded one must not hand out URLs, and a replaced
  // gallery's thumbnails must let go of theirs before they are revoked.
  await racePage.evaluate(async () => {
    const search = document.querySelector('#photo-search');
    for (let n = 0; n < 4; n++) {
      search.value = 'x'.repeat(n % 2); search.dispatchEvent(new Event('input'));
      for (let tick = 0; tick < n; tick++) await Promise.resolve();
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  });
  await racePage.locator('.photo-card').first().click();
  await racePage.locator('#photo-close').click();
  const stale = await racePage.evaluate(() => window.staleImageSources);
  assert(stale.length === 0, 'Images never keep or receive a revoked blob URL' + (stale.length ? ': ' + stale.slice(0, 3).join('; ') : ''));
  await racePage.close();
  assert(results.browser_errors.length === 0, 'No browser script or console errors');
  results.status = 'passed';
  results.synthetic_images_imported = 33;
  results.desktop_viewport = [1440, 1050];
  results.mobile_viewport = [390, 844];
  record();
  console.log(JSON.stringify({ status: results.status, checks: results.checks.length, evidence: qaFile }, null, 2));
} catch (error) {
  results.status = 'failed'; results.error = error.message;
  record();
  console.error(error);
  process.exitCode = 1;
} finally {
  try {
    if (browser) await browser.close();
  } finally {
    await served?.close();
  }
}
