import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';

const require = createRequire(import.meta.url);
const R = require('../../assets/js/photo-register.js');
const P = require('../../assets/js/photos.js');
const source = fs.readFileSync(new URL('../../assets/js/photo-register.js', import.meta.url), 'utf8');
const measurement = { reference: [[10, 20], [410, 20]], target: [[30, 40], [30, 240]], knownMm: 100 };
const photo = (patch = {}) => ({
  id: 'a'.repeat(64), name: 'front-face.png', width: 800, height: 600,
  viewpoint: 'front', notes: 'Check the mounting slot with calipers.',
  measurement: structuredClone(measurement), ...patch,
});
const manifest = (...photos) => ({ schema: 'cad-photo-workspace', version: 1, photos });

// Parse the actual serialized CSV, including quoted newlines and doubled quotes.
// This checks the handoff consumed by a spreadsheet, not just a matching string.
function parseCSV(csv) {
  const rows = [];
  let row = [], value = '', quoted = false;
  for (let i = 0; i < csv.length; i++) {
    const ch = csv[i];
    if (ch === '"') {
      if (quoted && csv[i + 1] === '"') { value += '"'; i++; }
      else quoted = !quoted;
    } else if (ch === ',' && !quoted) { row.push(value); value = ''; }
    else if ((ch === '\r' || ch === '\n') && !quoted) {
      if (ch === '\r' && csv[i + 1] === '\n') i++;
      row.push(value); rows.push(row); row = []; value = '';
    } else value += ch;
  }
  assert.equal(quoted, false, 'CSV quoted field closes');
  if (row.length || value) { row.push(value); rows.push(row); }
  return rows;
}
const record = (csv) => {
  const [header, values] = parseCSV(csv);
  assert.equal(values.length, header.length);
  return Object.fromEntries(header.map((key, i) => [key, values[i]]));
};

test('measurement export matches the template and keeps unknown instrument evidence blank', () => {
  const input = manifest(photo());
  const before = structuredClone(input);
  const csv = R.toCSV(input);
  const template = fs.readFileSync(new URL('../../templates/measurement-register.csv', import.meta.url), 'utf8').split(/\r?\n/)[0];
  assert.equal(csv.split('\r\n')[0], template);
  const row = record(csv);
  assert.equal(row.feature_id, 'PHOTO_' + 'a'.repeat(64));
  assert.equal(row.evidence_class, 'image-derived');
  assert.equal(Number(row.nominal_mm), 50);
  assert.equal(row.instrument, 'Photo pixel ratio (unverified)');
  for (const key of ['reading_1_mm', 'reading_2_mm', 'reading_3_mm', 'standard_uncertainty_mm', 'acceptance_criterion']) assert.equal(row[key], '', key);
  assert.equal(row.source_file, 'front-face.png');
  assert.match(row.datum, /same plane.*front-on/);
  assert.match(row.notes, /Known reference: 100 mm.*not independently verified/);
  assert.match(row.notes, /\[\[10,20\],\[410,20\]\]/);
  assert.match(row.notes, /\[\[30,40\],\[30,240\]\]/);
  assert.match(row.notes, /Independent physical measurement is required/);
  assert.match(row.notes, /blank fields are not zero/);
  assert.match(row.notes, /does not automatically become a CAD parameter/);
  assert.match(row.notes, /Check the mounting slot with calipers/);
  assert.deepEqual(input, before);
});

test('CSV preserves commas, quotes, multiline notes, and filenames without extra records', () => {
  const name = 'part, "front".png';
  const notes = 'First line, with commas\nSecond line has "quotes"\r\nThird line.';
  const csv = R.toCSV(manifest(photo({ name, notes })));
  assert.equal(parseCSV(csv).length, 2);
  const row = record(csv);
  assert.equal(row.source_file, name);
  assert.ok(row.notes.endsWith(notes));
  assert.match(csv, /""front""/);
});

test('spreadsheet formula prefixes in filenames are neutralized even after whitespace', () => {
  for (const name of ['=1+1.png', '+SUM(1).png', '-3.png', '@SUM(1).png', '  =1+1.png', '\tformula.png', '\rformula.png', ' \tplain.png', '\n=1+1.png', ' \u00a0@SUM(1).png']) {
    const row = record(R.toCSV(manifest(photo({ name }))));
    assert.equal(row.source_file, "'" + name);
    assert.equal(row.description, `Image-derived target length from ${name}`);
  }
  assert.equal(record(R.toCSV(manifest(photo({ name: 'ordinary-name.png' })))).source_file, 'ordinary-name.png');
});

test('only saved measurements produce rows and each full photo fingerprint stays unique', () => {
  assert.deepEqual(parseCSV(R.toCSV(manifest())), [R.COLUMNS]);
  const input = manifest(photo({ id: 'b'.repeat(64), measurement: null }), photo(), photo({ id: 'c'.repeat(64), measurement: undefined }));
  const rows = parseCSV(R.toCSV(input));
  assert.equal(rows.length, 2);
  assert.equal(rows[1][0], 'PHOTO_' + 'a'.repeat(64));
  assert.throws(() => R.toCSV(manifest(photo(), photo())), /duplicate fingerprints/);
  assert.throws(() => R.toCSV(manifest(photo({ measurement: null }), photo())), /duplicate fingerprints/);
});

test('invalid metadata and invalid saved measurements fail instead of being silently dropped', () => {
  for (const value of [null, [], {}, { photos: {} }]) assert.throws(() => R.toCSV(value), /photos array/);
  for (const row of [null, {}, photo({ id: 'a'.repeat(12) }), photo({ id: 'A'.repeat(64) })]) assert.throws(() => R.toCSV(manifest(row)), /SHA-256/);
  for (const patch of [{ name: '' }, { name: null }, { notes: null }, { viewpoint: 'sideways' }]) assert.throws(() => R.toCSV(manifest(photo(patch))), /filename.*notes.*viewpoint/);
  for (const bad of [false, 0, {}, { ...measurement, knownMm: 0 }, { ...measurement, knownMm: Infinity }, { ...measurement, target: [[0, 0], [900, 0]] }]) {
    assert.throws(() => R.toCSV(manifest(photo({ measurement: bad }))), /Cannot export the measurement/);
  }
  assert.throws(() => R.toCSV(manifest(photo({ width: 0 }))), /Cannot export the measurement/);
});

test('browser global exports the same helper and requires the photo arithmetic module', () => {
  const browser = { CadPhotos: P };
  vm.runInNewContext(source, browser);
  assert.equal(browser.CadPhotoRegister.toCSV(manifest(photo())), R.toCSV(manifest(photo())));
  assert.throws(() => vm.runInNewContext(source, {}), /Load the photo workspace/);
});
