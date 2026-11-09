/* Local photo intake and review. Originals never leave the browser. */
(function () {
  'use strict';
  const P = window.CadPhotos;
  const $ = (id) => document.getElementById(id);
  if (!P || !$('photos')) return;
  const label = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const node = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  };
  const size = (bytes) => bytes < 1048576 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1048576).toFixed(1)} MB`;
  const report = (message) => { $('photo-status').textContent = message; };
  const fail = (error) => report(error.message || 'This action could not finish. Try again.');
  const run = (action) => (...args) => Promise.resolve().then(() => action(...args)).catch(fail);
  let db, page = 0, importing = false, cancelled = false, renderVersion = 0;
  let galleryURLs = [], detailURL, selected, detailVersion = 0, pointMode = null, pointIndex = 0;
  const coordinateIDs = ['ref-x1', 'ref-y1', 'ref-x2', 'ref-y2', 'target-x1', 'target-y1', 'target-x2', 'target-y2'];
  const coords = coordinateIDs.map((id) => $('photo-' + id));
  const dialog = $('photo-detail');
  const errorsBox = node('ul', undefined, 'photo-errors');
  errorsBox.id = 'photo-errors'; errorsBox.hidden = true;
  $('photo-status').after(errorsBox);

  for (const viewpoint of P.VIEWPOINTS) {
    for (const id of ['photo-filter', 'photo-viewpoint']) {
      const option = node('option', label(viewpoint)); option.value = viewpoint;
      $(id).append(option);
    }
  }

  function setBusy(value) {
    importing = value;
    $('photo-input').disabled = value || !db;
    $('photo-cancel').hidden = !value;
    $('photo-cancel').disabled = false;
    $('photo-progress').hidden = !value;
    $('photo-drop-zone').setAttribute('aria-busy', String(value));
  }

  async function storageInfo(bytes) {
    let text = `${size(bytes)} saved in this browser. Keep your original files.`;
    try {
      const estimate = await navigator.storage?.estimate();
      if (estimate?.quota && Number.isFinite(estimate.usage)) {
        text += ` About ${size(Math.max(0, estimate.quota - estimate.usage))} of browser storage available (shared with this site).`;
      }
    } catch { /* An estimate is optional; committed writes determine success. */ }
    return text;
  }

  function coverage(result) {
    const primary = ['front', 'back', 'left', 'right', 'top', 'bottom'];
    $('photo-coverage').replaceChildren(...primary.map((view) => {
      const count = result.viewpoints[view] || 0;
      const chip = node('span', `${label(view)} · ${count}`, 'photo-badge' + (count ? ' is-covered' : ''));
      return chip;
    }));
    const missing = primary.filter((view) => !result.viewpoints[view]);
    const tips = [];
    if (!result.count) tips.push('Start with clear views around the same object. Include a ruler or a measured feature in the plane you want to measure.');
    else {
      if (result.viewpoints.unassigned) tips.push(`Label the viewpoint of ${result.viewpoints.unassigned} unassigned photo${result.viewpoints.unassigned === 1 ? '' : 's'} to track coverage.`);
      tips.push(missing.length ? `Views still unlabelled: ${missing.map(label).join(', ')}. Add them where the object can be photographed safely.` : 'All six view labels are represented. Check that nearby photos overlap and show the same unchanged object.');
      tips.push('Use overlapping views with steady lighting. Add close-ups of interfaces and hidden geometry; verify critical dimensions on the object.');
    }
    tips.push('Coverage follows your labels. It does not measure camera positions, overlap, or reconstruction accuracy.');
    $('photo-guidance').replaceChildren(...tips.map((tip) => node('p', tip)));
  }

  async function refresh() {
    if (!db) return;
    const version = ++renderVersion;
    const result = await db.list({ query: $('photo-search').value, viewpoint: $('photo-filter').value, page, pageSize: 24 });
    if (version !== renderVersion) return;
    if (page > 0 && page * 24 >= result.total) { page = Math.max(0, Math.ceil(result.total / 24) - 1); return refresh(); }
    $('photo-count').textContent = `${result.count} photo${result.count === 1 ? '' : 's'} saved`;
    $('photo-empty').hidden = result.total !== 0;
    $('photo-empty').textContent = result.count ? 'No photos match these filters. Try another view or a shorter search.' : 'Your reference set starts here. Add photos, then open one to label its view and record a measurement.';
    $('photo-page').textContent = `${result.total ? page * 24 + 1 : 0}–${Math.min((page + 1) * 24, result.total)} of ${result.total} photos`;
    $('photo-prev').disabled = page === 0;
    $('photo-next').disabled = (page + 1) * 24 >= result.total;
    $('photo-export').disabled = result.count === 0;
    coverage(result);
    const fragment = document.createDocumentFragment();
    const urls = [];
    try {
      for (const photo of result.items) {
        const card = node('button', undefined, 'photo-card'); card.type = 'button';
        card.dataset.photoId = photo.id;
        card.setAttribute('aria-label', `Review ${photo.name}`);
        const thumb = node('img', undefined, 'photo-thumb');
        thumb.alt = ''; thumb.loading = 'lazy'; thumb.decoding = 'async';
        const blob = await db.thumbnail(photo.id);
        if (blob) { const url = URL.createObjectURL(blob); urls.push(url); thumb.src = url; }
        const body = node('span', undefined, 'photo-card-body');
        body.append(node('span', photo.name, 'photo-card-name'), node('span', `${photo.width} × ${photo.height} · ${label(photo.viewpoint)}`, 'photo-card-meta'));
        if (photo.measurement) body.append(node('span', 'Dimension estimate saved', 'photo-badge'));
        if (photo.notes) body.append(node('span', photo.notes, 'photo-card-note'));
        card.append(thumb, body);
        card.addEventListener('click', run(() => openDetail(photo.id)));
        fragment.append(card);
      }
    } catch (error) { urls.forEach((url) => URL.revokeObjectURL(url)); throw error; }
    if (version !== renderVersion) { urls.forEach((url) => URL.revokeObjectURL(url)); return; }
    galleryURLs.forEach((url) => URL.revokeObjectURL(url)); galleryURLs = urls;
    $('photo-grid').replaceChildren(fragment);
    const info = await storageInfo(result.bytes);
    if (version === renderVersion) $('photo-storage').textContent = info;
  }

  async function importPhotos(files) {
    if (!db || importing || !files.length) return;
    setBusy(true); cancelled = false;
    errorsBox.replaceChildren(); errorsBox.hidden = true;
    let added = 0, duplicates = 0, failed = 0, processed = 0, storageStopped = false;
    $('photo-progress').max = files.length; $('photo-progress').value = 0;
    try {
      for (const file of files) {
        if (cancelled) break;
        report(`Adding photo ${processed + 1} of ${files.length}: ${file.name}`);
        let prepared;
        try { prepared = await P.prepareFile(file); }
        catch (error) {
          failed++;
          if (errorsBox.childElementCount < 30) errorsBox.append(node('li', `${file.name}: ${error.message}`));
        }
        if (prepared) {
          try {
            const result = await db.put(prepared);
            if (result.added) added++; else duplicates++;
          } catch (error) {
            failed++; storageStopped = true;
            errorsBox.append(node('li', `${file.name}: ${error.message} Import stopped; photos already saved are retained.`));
          }
        }
        processed++; $('photo-progress').value = processed;
        // Yield between files; neither decoded originals nor previews accumulate in memory.
        if (processed % 12 === 0) await refresh();
        await new Promise((resolve) => setTimeout(resolve, 0));
        if (storageStopped) break;
      }
      page = 0;
      await refresh();
      const pending = files.length - processed;
      report(`Added ${added} photos · ${duplicates} duplicates skipped · ${failed} files could not be added.${pending ? ` ${pending} files not processed; select them again to continue.` : ''}${cancelled ? ' Import cancelled.' : ''}`);
      errorsBox.hidden = !failed;
    } finally {
      $('photo-input').value = '';
      setBusy(false);
    }
  }

  function readMeasurement() {
    const values = coords.map((input) => input.value.trim() === '' ? null : Number(input.value));
    const known = $('photo-known-mm').value.trim();
    if (values.every((v) => v === null) && !known) return null;
    if (values.some((v) => v === null) || !known) throw new Error('Mark both endpoints of the reference and target, and enter the known reference length. Or clear the measurement to save only photo details.');
    return { reference: [[values[0], values[1]], [values[2], values[3]]], target: [[values[4], values[5]], [values[6], values[7]]], knownMm: Number(known) };
  }

  function drawPoints() {
    const svg = $('photo-overlay'); svg.replaceChildren();
    if (!selected) return;
    svg.setAttribute('viewBox', `0 0 ${selected.width} ${selected.height}`);
    const radius = Math.max(selected.width, selected.height) / 95;
    for (const [offset, color, prefix] of [[0, '#ea982c', 'R'], [4, '#40b9ba', 'T']]) {
      const points = [];
      for (let n = 0; n < 2; n++) {
        const xInput = coords[offset + n * 2], yInput = coords[offset + n * 2 + 1];
        if (xInput.value === '' || yInput.value === '') continue;
        const x = Number(xInput.value), y = Number(yInput.value);
        if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || y < 0 || x > selected.width || y > selected.height) continue;
        points.push([x, y]);
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        for (const [key, value] of Object.entries({ cx: x, cy: y, r: radius, fill: color, stroke: '#172b37', 'stroke-width': radius / 5 })) circle.setAttribute(key, value);
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        for (const [key, value] of Object.entries({ x: x + radius * 1.3, y: y - radius, fill: color, 'font-size': radius * 2.3, 'font-weight': 'bold', stroke: '#172b37', 'stroke-width': radius / 12, 'paint-order': 'stroke' })) text.setAttribute(key, value);
        text.textContent = prefix + (n + 1); svg.append(circle, text);
      }
      if (points.length === 2) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        for (const [key, value] of Object.entries({ x1: points[0][0], y1: points[0][1], x2: points[1][0], y2: points[1][1], stroke: color, 'stroke-width': radius / 3 })) line.setAttribute(key, value);
        svg.prepend(line);
      }
    }
  }

  function updateEstimate() {
    drawPoints();
    try {
      const measurement = readMeasurement();
      const estimate = measurement && P.estimate(measurement, selected.width, selected.height);
      $('photo-estimate').textContent = estimate ? `Estimated dimension: ${Number(estimate.estimatedMm.toPrecision(6))} mm. ${estimate.warnings.join(' ')}` : 'No dimension estimate yet. Mark a known reference and a target on the same plane.';
      $('photo-estimate').dataset.state = estimate ? 'estimate' : 'empty';
    } catch (error) {
      $('photo-estimate').textContent = error.message;
      $('photo-estimate').dataset.state = 'incomplete';
    }
  }

  function stopMarking() {
    pointMode = null; pointIndex = 0;
    $('photo-image-stage').classList.remove('is-marking');
    $('photo-reference-points').setAttribute('aria-pressed', 'false');
    $('photo-target-points').setAttribute('aria-pressed', 'false');
  }

  function setDetailBusy(value) {
    for (const input of dialog.querySelectorAll('input, select, textarea, #photo-save, #photo-remove, #photo-reference-points, #photo-target-points, #photo-reset-points')) input.disabled = value;
    if (value) stopMarking();
  }

  async function openDetail(id) {
    const version = ++detailVersion;
    const photo = await db.get(id);
    if (!photo || version !== detailVersion) return;
    selected = photo;
    setDetailBusy(false);
    if (detailURL) URL.revokeObjectURL(detailURL);
    detailURL = URL.createObjectURL(photo.blob);
    $('photo-image').src = detailURL; $('photo-image').alt = photo.name;
    $('photo-detail-title').textContent = photo.name;
    $('photo-detail-info').textContent = `${photo.width} × ${photo.height} pixels · ${size(photo.size)} · ${label(photo.viewpoint)}. Save details before closing.`;
    $('photo-viewpoint').value = photo.viewpoint;
    $('photo-notes').value = photo.notes;
    coords.forEach((input, i) => { input.max = i % 2 ? photo.height : photo.width; input.value = ''; });
    $('photo-known-mm').value = '';
    if (photo.measurement) {
      const m = photo.measurement;
      const values = [...m.reference.flat(), ...m.target.flat()];
      coords.forEach((input, i) => { input.value = values[i]; });
      $('photo-known-mm').value = m.knownMm;
    }
    stopMarking();
    $('photo-measure-instruction').textContent = 'Choose a reference or target, then click its two endpoints on the photo. You can also enter pixel coordinates below.';
    updateEstimate();
    if (!dialog.open) dialog.showModal();
  }

  function download(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = node('a'); link.href = url; link.download = filename;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }

  $('photo-input').addEventListener('change', (event) => { run(importPhotos)(Array.from(event.target.files)); });
  const drop = $('photo-drop-zone');
  for (const eventName of ['dragenter', 'dragover']) drop.addEventListener(eventName, (event) => {
    event.preventDefault(); drop.classList.add('is-dragging');
  });
  drop.addEventListener('dragleave', () => drop.classList.remove('is-dragging'));
  drop.addEventListener('drop', (event) => {
    event.preventDefault(); drop.classList.remove('is-dragging');
    if (importing) return report('A batch is still being added. Wait for it to finish, then drop these photos again.');
    run(importPhotos)(Array.from(event.dataTransfer.files));
  });
  // Prevent dropping a photo elsewhere from navigating away and losing an active import.
  for (const name of ['dragover', 'drop']) window.addEventListener(name, (event) => {
    if ([...(event.dataTransfer?.types || [])].includes('Files')) event.preventDefault();
  });
  $('photo-cancel').addEventListener('click', () => { cancelled = true; $('photo-cancel').disabled = true; report('Stopping after the current file finishes. Already saved photos will remain.'); });
  $('photo-search').addEventListener('input', run(() => { page = 0; return refresh(); }));
  $('photo-filter').addEventListener('change', run(() => { page = 0; return refresh(); }));
  $('photo-prev').addEventListener('click', run(() => { page = Math.max(0, page - 1); return refresh(); }));
  $('photo-next').addEventListener('click', run(() => { page++; return refresh(); }));
  $('photo-export').addEventListener('click', run(async () => {
    const manifest = await db.exportManifest();
    download(new Blob([JSON.stringify(manifest, null, 2) + '\n'], { type: 'application/json' }), 'cad-photo-manifest.json');
    report('Photo manifest exported: filenames, fingerprints, viewpoints, notes, and measurements. Keep the original photos separately; this file does not contain images.');
  }));

  $('photo-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    detailVersion++; selected = null; stopMarking();
    $('photo-image').removeAttribute('src');
    if (detailURL) URL.revokeObjectURL(detailURL); detailURL = null;
  });
  for (const [button, mode, offset] of [['photo-reference-points', 'reference', 0], ['photo-target-points', 'target', 4]]) {
    $(button).addEventListener('click', () => {
      stopMarking(); pointMode = mode; pointIndex = 0;
      coords.slice(offset, offset + 4).forEach((input) => { input.value = ''; });
      $(button).setAttribute('aria-pressed', 'true');
      $('photo-image-stage').classList.add('is-marking');
      $('photo-measure-instruction').textContent = `Click the first endpoint of the ${mode}.`;
      updateEstimate();
    });
  }
  $('photo-image').addEventListener('click', (event) => {
    if (!pointMode || !selected) return;
    const rect = event.target.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const offset = (pointMode === 'reference' ? 0 : 4) + pointIndex * 2;
    coords[offset].value = Math.min(selected.width, Math.max(0, (event.clientX - rect.left) * selected.width / rect.width)).toFixed(2);
    coords[offset + 1].value = Math.min(selected.height, Math.max(0, (event.clientY - rect.top) * selected.height / rect.height)).toFixed(2);
    pointIndex++;
    if (pointIndex === 2) { stopMarking(); $('photo-measure-instruction').textContent = 'Endpoints marked. Check the reference length and estimated dimension, then save photo details.'; }
    else $('photo-measure-instruction').textContent = `Click the second endpoint of the ${pointMode}.`;
    updateEstimate();
  });
  for (const input of [...coords, $('photo-known-mm')]) input.addEventListener('input', updateEstimate);
  $('photo-reset-points').addEventListener('click', () => {
    coords.forEach((input) => { input.value = ''; }); $('photo-known-mm').value = '';
    stopMarking(); updateEstimate();
  });
  $('photo-save').addEventListener('click', async () => {
    if (!selected) return;
    const version = detailVersion, id = selected.id;
    setDetailBusy(true);
    try {
      const measurement = readMeasurement();
      if (measurement) P.estimate(measurement, selected.width, selected.height);
      await db.update(id, { viewpoint: $('photo-viewpoint').value, notes: $('photo-notes').value, measurement });
      if (version === detailVersion) dialog.close();
      await refresh(); report('Photo details saved locally.');
    } catch (error) {
      if (version === detailVersion) $('photo-estimate').textContent = error.message;
      else fail(error);
    } finally { if (version === detailVersion) setDetailBusy(false); }
  });
  $('photo-download').addEventListener('click', () => { if (selected) download(selected.blob, selected.name); });
  $('photo-remove').addEventListener('click', async () => {
    if (!selected || !window.confirm(`Remove ${selected.name} from this browser's photo set? Your original file stays unchanged.`)) return;
    const version = detailVersion, id = selected.id;
    setDetailBusy(true);
    try {
      await db.remove(id);
      if (version === detailVersion) dialog.close();
      await refresh(); report('Photo removed from this browser’s reference set.');
    } catch (error) {
      if (version === detailVersion) $('photo-detail-info').textContent = error.message;
      else fail(error);
    } finally { if (version === detailVersion) setDetailBusy(false); }
  });
  window.addEventListener('beforeunload', (event) => { if (importing) { event.preventDefault(); event.returnValue = ''; } });
  window.addEventListener('focus', run(() => !importing && refresh()));
  setBusy(false);
  run(async () => {
    db = await P.createStore(); setBusy(false); await refresh();
    report('Ready to add photos. Images stay in this browser on this device.');
  })();
})();
