import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent } from 'react';
import {
  ArrowCounterClockwise,
  ArrowLeft,
  ArrowSquareOut,
  CheckCircle,
  Cube,
  DownloadSimple,
  Flask,
  Image as ImageIcon,
  Lamp,
  Mountains,
  SpinnerGap,
  UploadSimple,
  WarningCircle,
  X,
} from '@phosphor-icons/react';
import ModelViewer from './ModelViewer';
import { MODE_DEFAULTS, filenameFor, fmt, lithophaneRange, wedgeThicknesses } from './relief';
import type {
  BlenderStatus,
  CalibrationFit,
  ReliefDownload,
  ReliefMaterial,
  ReliefMode,
  ReliefResult,
  ReliefSettings,
} from './relief';
import './ReliefStudio.css';

const MAX_FILE = 10 * 1024 * 1024;
const SAMPLE = '/relief-sample.png';

type Draft = {
  name: string;
  mode: ReliefMode;
  source: 'photo' | 'depth';
  width: string;
  min: string;
  max: string;
  frame: string;
  invert: boolean;
  gamma: string;
  denoise: 'off' | 'light' | 'strong';
  nozzle: string;
  nozzleFilter: boolean;
  pitch: string;
  halfValue: string;
  autoLevels: boolean;
  material: ReliefMaterial;
  color: string;
};

const initialDraft: Draft = {
  name: 'Moon relief',
  mode: 'relief',
  source: 'photo',
  width: '100',
  min: MODE_DEFAULTS.relief.min,
  max: MODE_DEFAULTS.relief.max,
  frame: MODE_DEFAULTS.relief.frame,
  invert: false,
  gamma: '1',
  denoise: 'light',
  nozzle: '0.4',
  nozzleFilter: true,
  pitch: '',
  halfValue: '0.5',
  autoLevels: true,
  material: 'pla',
  color: '#e8e4da',
};

function number(value: string, low: number, high: number) {
  const parsed = Number(value);
  return value.trim() !== '' && Number.isFinite(parsed) && parsed >= low && parsed <= high
    ? parsed
    : null;
}

/** Validate the on-screen draft. Returns settings or a message naming the first problem. */
function toSettings(draft: Draft, revision: number): ReliefSettings | string {
  const width = number(draft.width, 10, 400);
  const min = number(draft.min, 0.2, 20);
  const max = number(draft.max, 0.4, 40);
  const frame = number(draft.frame, 0, 20);
  const gamma = number(draft.gamma, 0.25, 4);
  const nozzle = number(draft.nozzle, 0.1, 1.2);
  const halfValue = number(draft.halfValue, 0.05, 10);
  const pitch = draft.pitch.trim() === '' ? null : number(draft.pitch, 0.05, 5);
  if (width === null) return 'Width must be between 10 and 400 mm.';
  if (min === null) return 'Thinnest wall must be between 0.2 and 20 mm.';
  if (max === null) return 'Thickest wall must be between 0.4 and 40 mm.';
  if (max - min < 0.1) return 'Thickest wall must exceed the thinnest by at least 0.1 mm.';
  if (frame === null) return 'Frame must be between 0 and 20 mm.';
  if (gamma === null) return 'Tone curve must be between 0.25 and 4.';
  if (nozzle === null) return 'Nozzle width must be between 0.1 and 1.2 mm.';
  if (halfValue === null) return 'Half-value thickness must be between 0.05 and 10 mm.';
  if (draft.pitch.trim() !== '' && pitch === null)
    return 'Sample spacing must be blank (automatic) or between 0.05 and 5 mm.';
  return {
    name: draft.name.trim() || 'Relief',
    revision,
    mode: draft.mode,
    source: draft.source,
    width_mm: width,
    min_mm: min,
    max_mm: max,
    invert: draft.invert,
    gamma,
    denoise: draft.denoise,
    nozzle_mm: nozzle,
    nozzle_filter: draft.nozzleFilter,
    pitch_mm: pitch,
    frame_mm: frame,
    half_value_mm: halfValue,
    auto_levels: draft.autoLevels,
    material: draft.material,
    color: draft.color,
  };
}

function geometryKey(settings: ReliefSettings) {
  // Everything except the revision changes the generated geometry or its records.
  const { revision: _revision, ...rest } = settings;
  return JSON.stringify(rest);
}

async function errorFrom(response: Response) {
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') return body.detail;
  } catch {
    // Fall through to the status text.
  }
  return `The request failed (${response.status}).`;
}

function NumberInput({
  id,
  label,
  value,
  onChange,
  unit = 'mm',
  hint,
  disabled,
  step = 'any',
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  unit?: string;
  hint?: string;
  disabled?: boolean;
  step?: string;
}) {
  return (
    <div className="relief-field">
      <label htmlFor={id}>{label}</label>
      <div className="number-field">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          step={step}
          value={value}
          disabled={disabled}
          aria-describedby={hint ? `${id}-hint` : undefined}
          onChange={(e) => onChange(e.target.value)}
        />
        {unit && <span>{unit}</span>}
      </div>
      {hint && (
        <span id={`${id}-hint`} className="relief-hint">
          {hint}
        </span>
      )}
    </div>
  );
}

function Check({ ok, children }: { ok: boolean; children: string }) {
  return (
    <li className={ok ? 'check-ok' : 'check-bad'}>
      {ok ? <CheckCircle size={17} weight="fill" /> : <WarningCircle size={17} weight="fill" />}
      {children}
    </li>
  );
}

export default function ReliefStudio() {
  const [draft, setDraft] = useState<Draft>(initialDraft);
  const [file, setFile] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState('');
  const [result, setResult] = useState<ReliefResult | null>(null);
  const [builtKey, setBuiltKey] = useState('');
  const [builtFile, setBuiltFile] = useState<File | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [view, setView] = useState<'photo' | 'preview'>('photo');
  const [resetKey, setResetKey] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [blender, setBlender] = useState<BlenderStatus | null>(null);
  const [blenderMessage, setBlenderMessage] = useState('');
  const [readings, setReadings] = useState<string[]>(() => Array(8).fill(''));
  const [readingScale, setReadingScale] = useState<'srgb8' | 'linear'>('srgb8');
  const [fit, setFit] = useState<CalibrationFit | null>(null);
  const [fitError, setFitError] = useState('');
  const revision = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);

  const settings = toSettings(draft, revision.current);
  const invalid = typeof settings === 'string' ? settings : '';
  const stale =
    !!result &&
    (typeof settings === 'string' || geometryKey(settings) !== builtKey || file !== builtFile);
  const lithophane = draft.mode === 'lithophane';

  useEffect(() => {
    fetch('/api/blender')
      .then((r) => (r.ok ? r.json() : null))
      .then((status) => status && setBlender(status))
      .catch(() => setBlender(null));
  }, []);

  useEffect(
    () => () => {
      if (sourceUrl) URL.revokeObjectURL(sourceUrl);
    },
    [sourceUrl],
  );

  function update<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function build(nextFile = file, nextDraft = draft) {
    if (!nextFile) return;
    revision.current += 1;
    const request = toSettings(nextDraft, revision.current);
    if (typeof request === 'string') {
      setError(request);
      return;
    }
    const mine = revision.current;
    setBusy(request.mode === 'lithophane' ? 'Computing lithophane…' : 'Computing relief…');
    setError('');
    try {
      const body = new FormData();
      body.append('file', nextFile);
      body.append('settings', JSON.stringify(request));
      const response = await fetch('/api/relief', { method: 'POST', body });
      if (!response.ok) throw new Error(await errorFrom(response));
      const built: ReliefResult = await response.json();
      if (mine !== revision.current) return; // A newer build superseded this one.
      setResult(built);
      setBuiltKey(geometryKey(request));
      setBuiltFile(nextFile);
      setView('preview');
      setResetKey((v) => v + 1);
      setFit(null);
    } catch (caught) {
      if (mine === revision.current)
        setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      if (mine === revision.current) setBusy('');
    }
  }

  function choose(next: File, name?: string) {
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(next.type)) {
      setError('Choose a PNG, JPEG, or WebP image.');
      return;
    }
    if (next.size > MAX_FILE) {
      setError('Choose an image under 10 MiB.');
      return;
    }
    setFile(next);
    setSourceUrl(URL.createObjectURL(next));
    setView('photo');
    const nextDraft = name ? { ...draft, name } : draft;
    if (name) setDraft(nextDraft);
    void build(next, nextDraft);
  }

  async function loadSample() {
    setBusy('Loading the sample…');
    try {
      const response = await fetch(SAMPLE);
      if (!response.ok) throw new Error('The sample image could not be loaded.');
      const blob = await response.blob();
      choose(new File([blob], 'moon.png', { type: 'image/png' }), 'Moon relief');
    } catch (caught) {
      setBusy('');
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  function switchMode(mode: ReliefMode) {
    if (mode === draft.mode) return;
    const defaults = MODE_DEFAULTS[mode];
    const nextDraft = {
      ...draft,
      mode,
      min: defaults.min,
      max: defaults.max,
      frame: defaults.frame,
      name: draft.name.replace(/relief|lithophane/i, mode === 'relief' ? 'relief' : 'lithophane'),
    };
    setDraft(nextDraft);
    if (file) void build(file, nextDraft);
  }

  async function download(kind: ReliefDownload) {
    const url = result?.downloads[kind];
    if (!result || !url) return;
    setError('');
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(await errorFrom(response));
      const blob = await response.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filenameFor(kind, result.settings.name);
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(link.href), 10_000);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  async function openBlender() {
    if (!result) return;
    setBlenderMessage('');
    try {
      const response = await fetch(`/api/models/${result.id}/blender`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      if (!response.ok) throw new Error(await errorFrom(response));
      const body = await response.json();
      setBlenderMessage(body.detail);
    } catch (caught) {
      setBlenderMessage(caught instanceof Error ? caught.message : String(caught));
    }
  }

  async function calibrate() {
    setFit(null);
    setFitError('');
    const min = Number(draft.min);
    const max = Number(draft.max);
    const steps = wedgeThicknesses(min, max);
    const pairs = readings
      .map((value, index) => ({ value: value.trim(), thickness: steps[index] }))
      .filter((pair) => pair.value !== '');
    if (pairs.length < 3 || pairs.some((pair) => !Number.isFinite(Number(pair.value)))) {
      setFitError('Enter a number for at least three steps.');
      return;
    }
    try {
      const response = await fetch('/api/relief/calibrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thickness_mm: pairs.map((p) => p.thickness),
          readings: pairs.map((p) => Number(p.value)),
          scale: readingScale,
        }),
      });
      if (!response.ok) throw new Error(await errorFrom(response));
      setFit(await response.json());
    } catch (caught) {
      setFitError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped) choose(dropped, dropped.name.replace(/\.[^.]+$/, ''));
  }

  const stats = result?.stats;
  const optics = stats?.optics;
  const plan =
    typeof settings === 'string'
      ? null
      : lithophaneRange(settings.min_mm, settings.max_mm, settings.half_value_mm);
  const wedge = wedgeThicknesses(Number(draft.min) || 0, Number(draft.max) || 0);

  return (
    <div className="app-shell relief-studio">
      <header className="topbar">
        <a className="brand" href="#workbench" aria-label="Pictures to CAD flat-part workbench">
          <Cube size={35} weight="light" />
          <span>Pictures to CAD</span>
        </a>
        <div className="project-name">
          <input
            aria-label="Project name"
            value={draft.name}
            maxLength={100}
            onChange={(e) => update('name', e.target.value)}
            style={{ width: `${Math.min(Math.max(draft.name.length, 10), 24)}ch` }}
          />
        </div>
        <div className="header-actions">
          <a
            className="text-button guide-button"
            href="#workbench"
            aria-label="Flat-part workbench"
          >
            <ArrowLeft size={22} />
            <span>Flat-part workbench</span>
          </a>
        </div>
      </header>

      <main
        id="relief"
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <div className="relief-modes" role="radiogroup" aria-label="What to make">
          <button
            role="radio"
            aria-checked={draft.mode === 'relief'}
            aria-label="Relief: raised picture that prints flat"
            className="relief-mode"
            disabled={!!busy}
            onClick={() => switchMode('relief')}
          >
            <Mountains size={34} />
            <span>
              <strong>Relief</strong>
              <small>Raised picture you can see and touch. Prints flat.</small>
            </span>
          </button>
          <button
            role="radio"
            aria-checked={draft.mode === 'lithophane'}
            aria-label="Lithophane: thin panel that shows the picture when backlit"
            className="relief-mode"
            disabled={!!busy}
            onClick={() => switchMode('lithophane')}
          >
            <Lamp size={34} />
            <span>
              <strong>Lithophane</strong>
              <small>Thin panel that shows the photo when lit from behind.</small>
            </span>
          </button>
        </div>

        {error && (
          <div className="message error-message" role="alert">
            <WarningCircle size={23} />
            <div>
              <strong>We couldn’t complete that step.</strong>
              <span>{error}</span>
            </div>
            <button className="icon-button" aria-label="Dismiss error" onClick={() => setError('')}>
              <X size={19} />
            </button>
          </div>
        )}
        <div className="sr-only" role="status" aria-live="polite">
          {busy || (result && !stale ? `${result.kind} model ready.` : '')}
        </div>

        <section className="viewports relief-viewports" aria-label="Image and 3D preview">
          <section className="viewport-panel">
            <div className="panel-toolbar">
              <h1>
                <ImageIcon size={25} />
                {view === 'photo'
                  ? 'Your picture'
                  : lithophane
                    ? 'Backlit prediction'
                    : 'Height map'}
              </h1>
              <div className="panel-actions">
                {result && (
                  <div className="unit-toggle" aria-label="Image view">
                    <button aria-pressed={view === 'photo'} onClick={() => setView('photo')}>
                      Photo
                    </button>
                    <button aria-pressed={view === 'preview'} onClick={() => setView('preview')}>
                      {lithophane ? 'Backlit' : 'Heights'}
                    </button>
                  </div>
                )}
                <button
                  className="text-button"
                  disabled={!!busy}
                  onClick={() => fileInput.current?.click()}
                >
                  <UploadSimple size={21} />
                  Choose image
                </button>
                <input
                  ref={fileInput}
                  type="file"
                  hidden
                  accept="image/png,image/jpeg,image/webp"
                  aria-label="Choose an image"
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    const chosen = e.target.files?.[0];
                    if (chosen) choose(chosen, chosen.name.replace(/\.[^.]+$/, ''));
                    e.target.value = '';
                  }}
                />
              </div>
            </div>
            <div className={`canvas-stage relief-image-stage ${dragging ? 'dragging' : ''}`}>
              {sourceUrl ? (
                <img
                  className="relief-image"
                  src={view === 'preview' && result ? result.preview_image : sourceUrl}
                  alt={
                    view === 'preview'
                      ? lithophane
                        ? 'Predicted appearance of the lithophane when backlit'
                        : 'Height map: lighter is taller'
                      : 'Chosen source image'
                  }
                />
              ) : (
                <div className="model-empty">
                  <ImageIcon size={45} weight="light" />
                  <h3>Drop a picture here.</h3>
                  <p>PNG, JPEG or WebP up to 10 MiB. A 16-bit grayscale depth map also works.</p>
                  <div className="relief-start">
                    <button
                      className="primary-button"
                      disabled={!!busy}
                      onClick={() => fileInput.current?.click()}
                    >
                      <UploadSimple size={20} />
                      Choose image
                    </button>
                    <button className="outlined-button" disabled={!!busy} onClick={loadSample}>
                      Try the moon sample
                    </button>
                  </div>
                </div>
              )}
            </div>
          </section>
          <section className="viewport-panel model-panel" aria-label="3D preview">
            <div className="panel-toolbar">
              <h2>
                <Cube size={29} weight="light" />
                3D preview
              </h2>
              <button
                className="text-button"
                onClick={() => setResetKey((v) => v + 1)}
                disabled={!result}
              >
                <ArrowCounterClockwise size={23} />
                Reset view
              </button>
            </div>
            <div className="canvas-stage model-stage">
              <ModelViewer
                mesh={result?.mesh ?? null}
                resetKey={resetKey}
                loading={!!busy}
                color={draft.color}
                material={draft.material}
                lighting="raking"
              />
              {busy && (
                <div className="processing-status" role="status">
                  <SpinnerGap size={20} className="spinner" />
                  {busy}
                </div>
              )}
              {stale && !busy && (
                <div className="stale-status">
                  <WarningCircle size={19} />
                  <span>Previous model · press Update model to apply your changes</span>
                </div>
              )}
              {!result && !busy && (
                <div className="model-empty">
                  <Cube size={45} weight="light" />
                  <h3>Your 3D model appears here.</h3>
                  <p>Choose a picture; the model builds automatically.</p>
                </div>
              )}
            </div>
          </section>
        </section>

        <section className="relief-controls" aria-label="Size and thickness">
          <NumberInput
            id="relief-width"
            label="Picture width"
            value={draft.width}
            onChange={(v) => update('width', v)}
            hint="Height follows the picture’s shape"
          />
          <NumberInput
            id="relief-min"
            label="Thinnest"
            value={draft.min}
            onChange={(v) => update('min', v)}
            hint={lithophane ? 'Brightest areas' : 'Lowest areas (base)'}
          />
          <NumberInput
            id="relief-max"
            label="Thickest"
            value={draft.max}
            onChange={(v) => update('max', v)}
            hint={lithophane ? 'Darkest areas' : 'Highest areas'}
          />
          <NumberInput
            id="relief-frame"
            label="Frame"
            value={draft.frame}
            onChange={(v) => update('frame', v)}
            hint="Solid border, added outside the picture"
          />
          {lithophane ? (
            <NumberInput
              id="relief-hvl"
              label="Half-value thickness"
              value={draft.halfValue}
              onChange={(v) => update('halfValue', v)}
              hint="Extra plastic that halves the light"
            />
          ) : (
            <div className="relief-field">
              <span className="relief-label" id="relief-bright-label">
                Bright areas are
              </span>
              <div className="relief-toggle" role="group" aria-labelledby="relief-bright-label">
                <button aria-pressed={!draft.invert} onClick={() => update('invert', false)}>
                  Raised
                </button>
                <button aria-pressed={draft.invert} onClick={() => update('invert', true)}>
                  Sunken
                </button>
              </div>
              <span className="relief-hint">
                {draft.source === 'depth' ? 'Depth map: white = nearest' : 'From photo lightness'}
              </span>
            </div>
          )}
          <div className="relief-build">
            <button
              className="primary-button"
              disabled={!file || !!busy || !!invalid}
              onClick={() => void build()}
            >
              {busy ? <SpinnerGap size={20} className="spinner" /> : <Cube size={20} />}
              {result ? 'Update model' : 'Make 3D model'}
            </button>
            {invalid && <span className="validation-message">{invalid}</span>}
            {lithophane && plan && !invalid && (
              <span className="relief-hint">
                Range: {fmt(plan.stops, 1)} stops · {fmt(plan.ratio, 0)}:1 contrast
              </span>
            )}
          </div>
        </section>

        <details className="relief-panel">
          <summary>Fine-tune (optional)</summary>
          <div className="relief-advanced">
            {!lithophane && (
              <>
                <div className="relief-field">
                  <label htmlFor="relief-source">Picture type</label>
                  <select
                    id="relief-source"
                    value={draft.source}
                    onChange={(e) => update('source', e.target.value as Draft['source'])}
                  >
                    <option value="photo">Photo (height from lightness, CIE L*)</option>
                    <option value="depth">Depth map (stored values, white = near)</option>
                  </select>
                </div>
                <NumberInput
                  id="relief-gamma"
                  label="Tone curve (γ)"
                  value={draft.gamma}
                  unit=""
                  onChange={(v) => update('gamma', v)}
                  hint="Below 1 lifts shadows, above 1 deepens them"
                />
              </>
            )}
            <label className="check-field">
              <input
                type="checkbox"
                checked={draft.autoLevels}
                onChange={(e) => update('autoLevels', e.target.checked)}
              />
              {lithophane
                ? 'Auto exposure (99.5th-percentile white)'
                : 'Auto levels (stretch 0.5–99.5% tones to the full range)'}
            </label>
            <div className="relief-field">
              <label htmlFor="relief-denoise">Noise smoothing</label>
              <select
                id="relief-denoise"
                value={draft.denoise}
                onChange={(e) => update('denoise', e.target.value as Draft['denoise'])}
              >
                <option value="off">Off</option>
                <option value="light">Light (edge-preserving)</option>
                <option value="strong">Strong (edge-preserving)</option>
              </select>
            </div>
            <NumberInput
              id="relief-nozzle"
              label="Nozzle width"
              value={draft.nozzle}
              onChange={(v) => update('nozzle', v)}
              hint="Sets automatic sampling and the detail filter"
            />
            <label className="check-field">
              <input
                type="checkbox"
                checked={draft.nozzleFilter}
                onChange={(e) => update('nozzleFilter', e.target.checked)}
              />
              Remove detail finer than the nozzle (Gaussian, FWHM = nozzle)
            </label>
            <NumberInput
              id="relief-pitch"
              label="Sample spacing"
              value={draft.pitch}
              onChange={(v) => update('pitch', v)}
              hint="Blank = half the nozzle width"
            />
            <div className="relief-field">
              <label htmlFor="relief-material">Material (for mass)</label>
              <select
                id="relief-material"
                value={draft.material}
                onChange={(e) => update('material', e.target.value as ReliefMaterial)}
              >
                {(['pla', 'petg', 'abs', 'asa', 'tpu', 'nylon'] as const).map((m) => (
                  <option key={m} value={m}>
                    {m.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
            <div className="relief-field">
              <label htmlFor="relief-color">Preview colour</label>
              <input
                id="relief-color"
                type="color"
                value={draft.color}
                onChange={(e) => update('color', e.target.value)}
              />
            </div>
          </div>
        </details>

        {result && stats && (
          <section className="relief-results" aria-label="Results">
            <div className="relief-card">
              <h2>{result.kind === 'lithophane' ? 'Your lithophane' : 'Your relief'}</h2>
              <dl className="relief-facts">
                <dt>Size</dt>
                <dd>
                  {fmt(result.dimensions.width, 1)} × {fmt(result.dimensions.height, 1)} ×{' '}
                  {fmt(result.dimensions.thickness, 2)} mm
                </dd>
                <dt>Thickness range</dt>
                <dd>
                  {fmt(result.dimensions.min_thickness, 2)} – {fmt(result.dimensions.thickness, 2)}{' '}
                  mm
                </dd>
                <dt>Volume</dt>
                <dd>{fmt(result.volume_mm3 / 1000, 2)} cm³</dd>
                <dt>Approx. mass</dt>
                <dd>
                  {fmt(stats.mass_g, 1)} g{' '}
                  <small>
                    ({result.settings.material.toUpperCase()}, {fmt(stats.density_g_cm3, 2)} g/cm³
                    typical, 100% infill)
                  </small>
                </dd>
              </dl>
              <div className="relief-downloads">
                {(
                  [
                    ['stl', 'STL', 'Mesh for any slicer'],
                    ['3mf', '3MF', 'Millimetre mesh for slicers'],
                    ['blender', 'Blender ZIP', 'Editable scene + script'],
                    ['heightmap', 'Height map', '16-bit PNG, 1 px per point'],
                    ['project', 'Settings', 'JSON recipe (no photo)'],
                    ['wedge', 'Calibration wedge', '8-step STL for your filament'],
                  ] as [ReliefDownload, string, string][]
                )
                  .filter(([kind]) => result.downloads[kind])
                  .map(([kind, label, detail]) => (
                    <button
                      key={kind}
                      className="outlined-button relief-download"
                      disabled={stale}
                      onClick={() => void download(kind)}
                    >
                      <DownloadSimple size={20} />
                      <span>
                        {label}
                        <small>{detail}</small>
                      </span>
                    </button>
                  ))}
              </div>
              {stale && <p className="relief-hint">Update the model to download current files.</p>}
            </div>

            <div className="relief-card">
              <h2>
                <Flask size={22} /> The science check
              </h2>
              <ul className="relief-checks">
                <Check ok={stats.mesh.closed_and_oriented}>
                  Watertight: every edge is shared by exactly two faces
                </Check>
                <Check ok={stats.mesh.euler_characteristic === 2}>
                  {`Euler characteristic V − E + F = ${stats.mesh.vertices.toLocaleString()} − ${stats.mesh.edges.toLocaleString()} + ${stats.mesh.triangles.toLocaleString()} = ${stats.mesh.euler_characteristic} (one solid, no holes)`}
                </Check>
                <Check
                  ok={
                    Math.abs(stats.mesh.volume_mm3 - stats.volume_cross_check_mm3) <=
                    1e-6 * stats.mesh.volume_mm3
                  }
                >
                  {`Volume by two independent methods agrees: ${fmt(stats.mesh.volume_mm3, 3)} vs ${fmt(stats.volume_cross_check_mm3, 3)} mm³`}
                </Check>
              </ul>
              <dl className="relief-facts">
                <dt>Sampling</dt>
                <dd>
                  {stats.grid.columns} × {stats.grid.rows} points, every{' '}
                  {fmt(stats.grid.pitch_x_mm, 3)} mm (photo pixel ={' '}
                  {fmt(stats.grid.image_pixel_mm, 3)} mm)
                </dd>
                <dt>Nozzle filter</dt>
                <dd>
                  {stats.nozzle_filter.enabled
                    ? `σ = ${fmt(stats.nozzle_filter.sigma_mm, 3)} mm removed ${fmt(stats.nozzle_filter.removed_rms_mm, 3)} mm RMS (max ${fmt(stats.nozzle_filter.removed_max_mm, 2)} mm) of unprintable detail`
                    : 'Off: detail finer than the nozzle is kept but may not print'}
                </dd>
                <dt>Steepest slope</dt>
                <dd>
                  {fmt(stats.slope_deg.max, 0)}° (95% of the surface under{' '}
                  {fmt(stats.slope_deg.p95, 0)}°)
                </dd>
                <dt>Height precision</dt>
                <dd>16-bit steps of {fmt(stats.quantization_step_mm * 1000, 3)} µm</dd>
                {optics && (
                  <>
                    <dt>Light range</dt>
                    <dd>
                      {fmt(optics.dynamic_range_stops, 1)} stops ({fmt(optics.contrast_ratio, 0)}
                      :1), μ = {fmt(optics.mu_per_mm, 3)} /mm
                    </dd>
                    <dt>Clipped shadows</dt>
                    <dd>{fmt(optics.clipped_fraction * 100, 1)}% of the picture</dd>
                    <dt>Tone accuracy</dt>
                    <dd>
                      ΔL* mean {fmt(optics.tone_error_lstar_mean, 2)}, 95th percentile{' '}
                      {fmt(optics.tone_error_lstar_p95, 2)} where the panel can show the tone{' '}
                      <small>(about 1 is barely visible)</small>
                    </dd>
                  </>
                )}
              </dl>
              <details className="relief-explain">
                <summary>How these numbers are computed</summary>
                <p>
                  Photo pixels are decoded from sRGB to linear light (IEC 61966-2-1) and combined
                  into luminance Y = 0.2126 R + 0.7152 G + 0.0722 B.{' '}
                  {lithophane
                    ? 'A lithophane targets linear light: by the Beer–Lambert law a wall of thickness t passes exp(−μ t) of the light, so each point gets t = t_min − ln(Y) / μ, with μ = ln 2 / half-value thickness.'
                    : 'A relief maps perceived lightness (CIE 1976 L*) to height, so equal height steps look like equal tone steps.'}{' '}
                  Detail finer than the nozzle is removed with a Gaussian whose full width at half
                  maximum equals the nozzle width. The surface is triangulated along the diagonal
                  with the smaller height change, closed with vertical walls and a flat base, then
                  checked: every directed edge must appear once with its reverse, V − E + F must
                  equal 2, and the divergence-theorem volume must match the sum of the top
                  triangles’ projected area × mean height.
                </p>
              </details>
            </div>

            <div className="relief-card">
              <h2>Open in Blender</h2>
              <p className="relief-text">
                The Blender ZIP rebuilds this exact solid as an editable scene: the surface is a
                Displace modifier reading the 16-bit height map, so you can change its strength
                live, sculpt, or render it.
                {lithophane &&
                  ' The lithophane scene uses a Volume Absorption material with density μ and a backlight, so a Cycles render shows the Beer–Lambert prediction.'}
              </p>
              {blender?.launch_available ? (
                <button className="outlined-button" disabled={stale} onClick={openBlender}>
                  <ArrowSquareOut size={20} />
                  Open in Blender
                </button>
              ) : (
                <ol className="relief-steps">
                  <li>Download the Blender ZIP above and extract it.</li>
                  <li>
                    In that folder run <code>blender --python build_relief.py</code>, or open the
                    script in Blender’s Scripting tab and press Run Script.
                  </li>
                </ol>
              )}
              <p className="relief-hint">
                {blender
                  ? `${blender.detected ? 'Blender found on this computer.' : 'Blender not found on this computer.'} ${blender.launch_available ? '' : blender.launch_reason} Tested with Blender ${blender.tested_version}; written for ${blender.minimum_version} or later.`
                  : 'Blender availability could not be checked.'}
              </p>
              {blenderMessage && <p className="relief-hint">{blenderMessage}</p>}
            </div>

            {lithophane && (
              <div className="relief-card">
                <h2>Calibrate your filament</h2>
                <p className="relief-text">
                  Every filament passes light differently. Print the calibration wedge (8 steps from
                  thinnest to thickest), hold it in front of your lamp and photograph it with
                  exposure locked. Enter each step’s brightness. The app fits ln(Y) = a − μ t by
                  least squares and gives your half-value thickness.
                </p>
                <div className="relief-wedge">
                  <div className="relief-field">
                    <label htmlFor="relief-scale">Readings are</label>
                    <select
                      id="relief-scale"
                      value={readingScale}
                      onChange={(e) => setReadingScale(e.target.value as 'srgb8' | 'linear')}
                    >
                      <option value="srgb8">Photo pixel values (0–255)</option>
                      <option value="linear">Light meter (any unit)</option>
                    </select>
                  </div>
                  <table>
                    <thead>
                      <tr>
                        <th scope="col">Step</th>
                        <th scope="col">Thickness</th>
                        <th scope="col">Reading</th>
                      </tr>
                    </thead>
                    <tbody>
                      {wedge.map((thickness, index) => (
                        <tr key={index}>
                          <td>{index + 1}</td>
                          <td>{fmt(thickness, 2)} mm</td>
                          <td>
                            <input
                              aria-label={`Step ${index + 1} reading`}
                              type="number"
                              inputMode="decimal"
                              value={readings[index]}
                              onChange={(e) =>
                                setReadings((current) =>
                                  current.map((v, i) => (i === index ? e.target.value : v)),
                                )
                              }
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <button className="outlined-button" onClick={calibrate}>
                    Fit half-value thickness
                  </button>
                  {fitError && <span className="validation-message">{fitError}</span>}
                  {fit && (
                    <div className="relief-fit" role="status">
                      <strong>
                        Half-value thickness {fmt(fit.half_value_mm, 3)} mm
                        {fit.half_value_se_mm !== null &&
                          ` ± ${fmt(fit.half_value_se_mm, 3)} (standard error)`}
                      </strong>
                      <span>
                        μ = {fmt(fit.mu_per_mm, 3)} /mm · R² = {fmt(fit.r_squared, 4)} ·{' '}
                        {fit.used_points} steps used
                        {fit.excluded_steps.length > 0 &&
                          ` · skipped step ${fit.excluded_steps.map((i) => i + 1).join(', ')} (black or saturated)`}
                      </span>
                      <button
                        className="primary-button"
                        onClick={() => update('halfValue', fit.half_value_mm.toFixed(3))}
                      >
                        Use this value
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {result.warnings.length > 0 && (
              <div className="relief-card relief-notes">
                <h2>Notes</h2>
                <ul>
                  {result.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
