/* Export image-derived estimates to the existing measurement-register format.
 * This is a review handoff, not an instrument reading or a CAD parameter import.
 */
(function (root) {
  'use strict';

  const P = typeof module !== 'undefined' && module.exports ? require('./photos.js') : root.CadPhotos;
  if (!P || typeof P.estimate !== 'function') throw new Error('Load the photo workspace before exporting its measurement register.');

  const COLUMNS = Object.freeze([
    'feature_id', 'description', 'evidence_class', 'nominal_mm',
    'reading_1_mm', 'reading_2_mm', 'reading_3_mm', 'instrument', 'datum',
    'standard_uncertainty_mm', 'acceptance_criterion', 'source_file', 'notes',
  ]);

  // Quoting handles CSV separators; the apostrophe separately prevents spreadsheet
  // formula interpretation. Retain original text after the protective prefix.
  function cell(value) {
    if (value === '') return '';
    if (typeof value === 'number') return String(value);
    let text = value;
    if (/^\s*[=+\-@]/u.test(text) || /^\s*[\t\r\n]/u.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  }

  function toCSV(manifest) {
    if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest) || !Array.isArray(manifest.photos)) {
      throw new TypeError('Choose a photo manifest with a photos array.');
    }
    const ids = new Set();
    const rows = [COLUMNS.join(',')];
    for (const photo of manifest.photos) {
      if (!photo || typeof photo !== 'object' || Array.isArray(photo) || typeof photo.id !== 'string' || !/^[a-f0-9]{64}$/.test(photo.id)) {
        throw new RangeError('Every photo in the measurement export needs its full SHA-256 fingerprint.');
      }
      if (ids.has(photo.id)) throw new RangeError('The photo manifest contains duplicate fingerprints. Export each photo only once.');
      ids.add(photo.id);
      if (photo.measurement === null || photo.measurement === undefined) continue;
      if (typeof photo.name !== 'string' || !photo.name || typeof photo.notes !== 'string' || !P.VIEWPOINTS.includes(photo.viewpoint)) {
        throw new TypeError('A measured photo needs a filename, text notes, and a valid viewpoint.');
      }

      let result;
      try { result = P.estimate(photo.measurement, photo.width, photo.height); }
      catch (error) { throw new RangeError(`Cannot export the measurement for ${photo.name}: ${error.message}`); }
      const measurement = photo.measurement;
      const notes = [
        `SHA-256: ${photo.id}.`,
        `Known reference: ${measurement.knownMm} mm (user-entered, not independently verified).`,
        `Reference endpoints (full-size image pixels): ${JSON.stringify(measurement.reference)}.`,
        `Target endpoints (full-size image pixels): ${JSON.stringify(measurement.target)}.`,
        `Viewpoint: ${photo.viewpoint}.`,
        ...result.warnings,
        'Independent physical measurement is required before accepting a critical dimension. Instrument readings, uncertainty, and acceptance criterion are unknown; blank fields are not zero. This row does not automatically become a CAD parameter.',
        ...(photo.notes ? [`Original photo notes: ${photo.notes}`] : []),
      ].join(' ');
      rows.push([
        `PHOTO_${photo.id}`,
        `Image-derived target length from ${photo.name}`,
        'image-derived',
        result.estimatedMm,
        '', '', '',
        'Photo pixel ratio (unverified)',
        'Reference and target assumed in the same plane, photographed front-on',
        '', '',
        photo.name,
        notes,
      ].map(cell).join(','));
    }
    return rows.join('\r\n') + '\r\n';
  }

  const api = Object.freeze({ COLUMNS, toCSV });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CadPhotoRegister = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
