import { useEffect, useRef, useState } from 'react';
import {
  ArrowCounterClockwise,
  DownloadSimple,
  UploadSimple,
  Ruler,
  Stack,
  CirclesThree,
  ArrowUpRight,
} from '@phosphor-icons/react';
import AppHeader from './AppHeader';
import {
  LAB_DEFAULTS,
  experimentFromHash,
  fitScenario,
  layerBands,
  layerScenario,
  parseLabScenario,
  scaleScenario,
} from './science';
import type { LabScenario, LabTool } from './science';
import { readStudioJson, saveStudioJson } from './studioFiles';
import './ScienceStudio.css';

const TOOLS = [
  {
    id: 'scale' as const,
    title: 'Pixel scale',
    subtitle: 'Length from a known reference',
    icon: Ruler,
  },
  {
    id: 'layers' as const,
    title: 'Layer stack',
    subtitle: 'Height in discrete steps',
    icon: Stack,
  },
  {
    id: 'fit' as const,
    title: 'Measured fit',
    subtitle: 'Learn from a test coupon',
    icon: CirclesThree,
  },
];
const FIELDS: Record<
  LabTool,
  { key: string; label: string; min: number; max: number; step: string }[]
> = {
  scale: [
    { key: 'knownMm', label: 'Known reference length (mm)', min: 0.001, max: 2000, step: 'any' },
    {
      key: 'referencePx',
      label: 'Marked reference span (px)',
      min: 1,
      max: 1_000_000,
      step: 'any',
    },
    { key: 'outlinePx', label: 'Part outline span (px)', min: 1, max: 1_000_000, step: 'any' },
    { key: 'endpointShiftPx', label: 'Shift per endpoint (px)', min: 0, max: 1000, step: 'any' },
  ],
  layers: [
    { key: 'heightMm', label: 'Part height (mm)', min: 0.01, max: 2000, step: 'any' },
    { key: 'layerMm', label: 'Regular layer height (mm)', min: 0.01, max: 2, step: 'any' },
    { key: 'firstLayerMm', label: 'First layer height (mm)', min: 0.01, max: 2, step: 'any' },
    { key: 'nozzleMm', label: 'Nozzle diameter (mm)', min: 0.1, max: 2, step: 'any' },
  ],
  fit: [
    { key: 'cadHoleMm', label: 'Coupon CAD hole diameter (mm)', min: 0.1, max: 1000, step: 'any' },
    { key: 'measuredHoleMm', label: 'Measured coupon hole (mm)', min: 0.1, max: 1000, step: 'any' },
    { key: 'shaftMm', label: 'Measured mating shaft (mm)', min: 0.1, max: 1000, step: 'any' },
    { key: 'clearanceMm', label: 'Desired diametral clearance (mm)', min: -5, max: 5, step: 'any' },
  ],
};
type Drafts = Record<LabTool, Record<string, string>>;
function toDrafts(scenario: LabScenario): Drafts {
  return Object.fromEntries(
    TOOLS.map(({ id }) => [
      id,
      Object.fromEntries(Object.entries(scenario[id]).map(([key, value]) => [key, String(value)])),
    ]),
  ) as Drafts;
}
function numbers<T>(draft: Record<string, string>): T {
  return Object.fromEntries(
    Object.entries(draft).map(([key, value]) => [key, value.trim() ? Number(value) : NaN]),
  ) as T;
}
function attempt<T>(calculate: () => T) {
  try {
    return { value: calculate(), error: '' };
  } catch (reason) {
    return { value: null, error: reason instanceof Error ? reason.message : 'Check the inputs.' };
  }
}
const format = (value: number, places = 3) =>
  value.toLocaleString('en-US', { minimumFractionDigits: places, maximumFractionDigits: places });
const SCIENCE_KEY = 'pictures-to-cad.science.v1';
const endpointExplorationMax = (shift: number) => Math.min(1000, Math.max(5, shift));
function loadScenario() {
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(SCIENCE_KEY);
    return {
      scenario: raw ? parseLabScenario(JSON.parse(raw)) : LAB_DEFAULTS,
      error: '',
      recovery: null,
    };
  } catch {
    return {
      scenario: LAB_DEFAULTS,
      error: raw
        ? 'Saved scenarios could not be read. Export recovery data before replacing them.'
        : 'Browser storage is unavailable. Export scenarios to retain your work.',
      recovery: raw,
    };
  }
}

export default function ScienceStudio() {
  const [initial] = useState(loadScenario);
  const [active, setActive] = useState<LabTool>(
    () => experimentFromHash(window.location.hash) ?? initial.scenario.active,
  );
  const [drafts, setDrafts] = useState(() => toDrafts(initial.scenario));
  // Numeric edits/imports choose the exploration range; moving the slider must
  // not shrink its own maximum and prevent returning to the starting value.
  const [endpointMax, setEndpointMax] = useState(() =>
    endpointExplorationMax(initial.scenario.scale.endpointShiftPx),
  );
  const [dirty, setDirty] = useState(false);
  const [recovery, setRecovery] = useState(initial.recovery);
  const [persistence, setPersistence] = useState(
    initial.error || 'Valid scenarios save locally in this browser. Export a portable backup.',
  );
  const [message, setMessage] = useState('');
  const [fileError, setFileError] = useState('');
  const [importing, setImporting] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const importSequence = useRef(0);
  const pendingExperiment = useRef<LabTool | null>(null);
  useEffect(
    () => () => {
      importSequence.current += 1;
    },
    [],
  );
  useEffect(() => {
    const selectRequested = (requested: LabTool) => {
      setActive(requested);
      setDirty(true);
    };
    if (!importing && pendingExperiment.current) {
      selectRequested(pendingExperiment.current);
      pendingExperiment.current = null;
    }
    const update = () => {
      const requested = experimentFromHash(window.location.hash);
      if (!requested) return;
      if (importing) pendingExperiment.current = requested;
      else selectRequested(requested);
    };
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, [importing]);
  const scaleInput = numbers<LabScenario['scale']>(drafts.scale);
  const layerInput = numbers<LabScenario['layers']>(drafts.layers);
  const fitInput = numbers<LabScenario['fit']>(drafts.fit);
  const scale = attempt(() => scaleScenario(scaleInput));
  const layers = attempt(() => layerScenario(layerInput));
  const fit = attempt(() => fitScenario(fitInput));
  const issue = { scale, layers, fit }[active].error;
  const selected = TOOLS.find((item) => item.id === active)!;
  useEffect(() => {
    if (!dirty || recovery) return;
    try {
      const scenario = parseLabScenario({
        format: LAB_DEFAULTS.format,
        version: 1,
        active,
        scale: numbers(drafts.scale),
        layers: numbers(drafts.layers),
        fit: numbers(drafts.fit),
      });
      try {
        localStorage.setItem(SCIENCE_KEY, JSON.stringify(scenario));
        setPersistence(
          'Valid scenarios saved locally in this browser. Export a backup before clearing site data.',
        );
      } catch {
        setPersistence(
          'Browser storage could not save these scenarios. Export now to retain the current values.',
        );
      }
    } catch {
      setPersistence(
        'An experiment has invalid inputs. The last valid saved scenarios are preserved; complete the values before leaving.',
      );
    }
  }, [drafts, active, dirty, recovery]);
  function change(key: string, value: string) {
    setDirty(true);
    setDrafts((old) => ({ ...old, [active]: { ...old[active], [key]: value } }));
    setMessage('');
    setFileError('');
  }
  function exportScenario() {
    try {
      const scenario = parseLabScenario({
        format: LAB_DEFAULTS.format,
        version: 1,
        active,
        scale: scaleInput,
        layers: layerInput,
        fit: fitInput,
      });
      saveStudioJson(scenario, 'pictures-to-cad-science.json');
      setMessage('Scenario download started. All three experiments are included.');
      setFileError('');
    } catch (reason) {
      setFileError(
        reason instanceof Error ? reason.message : 'Check all experiment inputs before exporting.',
      );
    }
  }
  async function importScenario(file?: File) {
    if (!file) return;
    const sequence = ++importSequence.current;
    setImporting(true);
    setFileError('');
    try {
      const scenario = parseLabScenario(await readStudioJson(file));
      if (sequence !== importSequence.current) return;
      setRecovery(null);
      setDirty(true);
      setDrafts(toDrafts(scenario));
      setEndpointMax(endpointExplorationMax(scenario.scale.endpointShiftPx));
      setActive(scenario.active);
      setMessage('Scenario imported. These values do not change your CAD model.');
    } catch (reason) {
      if (sequence !== importSequence.current) return;
      setFileError(
        reason instanceof Error ? reason.message : 'The scenario could not be imported.',
      );
    } finally {
      if (sequence === importSequence.current) setImporting(false);
    }
  }
  return (
    <div className="app-shell science-studio">
      <AppHeader
        studio="science"
        projectName={<span className="studio-project-label">Science lab</span>}
      />
      <main id="science" className="lab-main">
        <div className="lab-heading">
          <div>
            <p className="lab-eyebrow">Explore · compare · understand</p>
            <h1>Science lab</h1>
            <p>Change a variable. See the consequence. Keep the assumptions in view.</p>
          </div>
          <div className="lab-file-actions">
            <button className="outlined-button" onClick={exportScenario} disabled={importing}>
              <DownloadSimple size={18} />
              Export scenarios
            </button>
            <button
              className="outlined-button"
              onClick={() => fileInput.current?.click()}
              disabled={importing}
            >
              <UploadSimple size={18} />
              {importing ? 'Importing…' : 'Import scenarios'}
            </button>
            <input
              ref={fileInput}
              className="sr-only"
              type="file"
              tabIndex={-1}
              disabled={importing}
              accept=".json,application/json"
              aria-label="Import science scenario JSON"
              onChange={(event) => {
                void importScenario(event.target.files?.[0]);
                event.target.value = '';
              }}
            />
          </div>
        </div>
        <p className="lab-status" role="status">
          {message ||
            'Exploration only · These scenarios do not change your model or slicer settings.'}
        </p>
        <p className="lab-status" role="status">
          {persistence}
        </p>
        {recovery && (
          <div className="lab-file-actions">
            <button
              className="outlined-button"
              onClick={() =>
                saveStudioJson(
                  { format: 'unreadable-science-recovery', raw: recovery },
                  'pictures-to-cad-science-recovery.json',
                )
              }
            >
              Export recovery data
            </button>
            <button
              className="text-button"
              disabled={importing}
              onClick={() => {
                setRecovery(null);
                setDirty(true);
              }}
            >
              Replace unreadable saved scenarios
            </button>
          </div>
        )}
        {fileError && (
          <p className="lab-error" role="alert">
            {fileError}
          </p>
        )}
        <div className="lab-workspace">
          <aside className="lab-index" aria-label="Experiments">
            {TOOLS.map(({ id, title, subtitle, icon: Icon }, index) => (
              <button
                key={id}
                aria-pressed={id === active}
                disabled={importing}
                onClick={() => {
                  setDirty(true);
                  setActive(id);
                  setFileError('');
                }}
              >
                <span className="lab-index-number">0{index + 1}</span>{' '}
                <Icon size={23} aria-hidden="true" />
                <span>
                  <strong>{title}</strong> <small>{subtitle}</small>
                </span>
              </button>
            ))}
            <div className="lab-index-note">
              <strong>Keep a test record</strong>
              <p>
                Valid scenarios save in this browser. Export your inputs to keep an independent
                record or move between devices.
              </p>
              <a href="#knowledge?search=measurement">
                Read the measurement guide <ArrowUpRight size={16} />
              </a>
            </div>
          </aside>
          <section className="lab-experiment" aria-label={selected.title}>
            <div className="lab-experiment-heading">
              <div>
                <p className="lab-eyebrow">Interactive experiment</p>
                <h2>{selected.title}</h2>
              </div>
              <button
                className="text-button"
                disabled={importing}
                onClick={() => {
                  setDirty(true);
                  setDrafts((old) => ({ ...old, [active]: toDrafts(LAB_DEFAULTS)[active] }));
                  if (active === 'scale')
                    setEndpointMax(endpointExplorationMax(LAB_DEFAULTS.scale.endpointShiftPx));
                  setMessage(`${selected.title} reset to example values.`);
                  setFileError('');
                }}
              >
                <ArrowCounterClockwise size={18} />
                Reset experiment
              </button>
            </div>
            <div className="lab-body">
              <div className="lab-inputs">
                <h3>Your inputs</h3>
                {FIELDS[active].map((field) => (
                  <label key={field.key}>
                    {field.label}
                    <input
                      type="number"
                      disabled={importing}
                      inputMode="decimal"
                      min={field.min}
                      max={field.max}
                      step={field.step}
                      value={drafts[active][field.key]}
                      onChange={(event) => {
                        change(field.key, event.target.value);
                        if (active === 'scale' && field.key === 'endpointShiftPx') {
                          const shift = event.target.valueAsNumber;
                          if (Number.isFinite(shift) && shift >= 0 && shift <= 1000)
                            setEndpointMax(endpointExplorationMax(shift));
                        }
                      }}
                    />
                  </label>
                ))}
                {active === 'scale' && (
                  <label className="lab-range">
                    Explore endpoint movement
                    <input
                      type="range"
                      disabled={importing}
                      min="0"
                      max={endpointMax}
                      step="0.25"
                      value={
                        Number.isFinite(scaleInput.endpointShiftPx) ? scaleInput.endpointShiftPx : 0
                      }
                      onChange={(event) => change('endpointShiftPx', event.target.value)}
                    />
                  </label>
                )}
                {issue && (
                  <p className="lab-error" role="alert">
                    {issue}
                  </p>
                )}
              </div>
              <div className="lab-output" aria-live="polite">
                {issue ? (
                  <div className="lab-empty">
                    <selected.icon size={42} />
                    <h3>Complete the experiment</h3>
                    <p>Enter valid values to see a result and diagram.</p>
                  </div>
                ) : active === 'scale' && scale.value ? (
                  <>
                    <p className="lab-output-label">Calculated part width</p>
                    <div className="lab-big-number">
                      {format(scale.value.widthMm)}
                      <span>mm</span>
                    </div>
                    <svg
                      className="lab-diagram"
                      viewBox="0 0 520 210"
                      role="img"
                      aria-label={`Endpoint sensitivity from ${format(scale.value.lowMm)} to ${format(scale.value.highMm)} millimeters; current ${format(scale.value.widthMm)}.`}
                    >
                      <defs>
                        <pattern
                          id="lab-scale-grid"
                          width="20"
                          height="20"
                          patternUnits="userSpaceOnUse"
                        >
                          <path
                            d="M 20 0 L 0 0 0 20"
                            fill="none"
                            stroke="currentColor"
                            opacity=".1"
                          />
                        </pattern>
                      </defs>
                      <rect width="520" height="210" fill="url(#lab-scale-grid)" />
                      <text x="32" y="35">
                        Endpoint movement scenario
                      </text>
                      <line x1="48" x2="472" y1="104" y2="104" className="lab-range-line" />
                      <line x1="48" x2="48" y1="84" y2="124" />
                      <line x1="472" x2="472" y1="84" y2="124" />
                      <circle
                        cx={
                          scale.value.highMm === scale.value.lowMm
                            ? 260
                            : 48 +
                              (424 * (scale.value.widthMm - scale.value.lowMm)) /
                                (scale.value.highMm - scale.value.lowMm)
                        }
                        cy="104"
                        r="8"
                      />
                      <text x="48" y="155">
                        {format(scale.value.lowMm)} mm
                      </text>
                      <text x="472" y="155" textAnchor="end">
                        {format(scale.value.highMm)} mm
                      </text>
                      <text x="260" y="191" textAnchor="middle">
                        Longer marked span → smaller calculated part
                      </text>
                    </svg>
                    <dl className="lab-readings">
                      <div>
                        <dt>Scale</dt>
                        <dd>{format(scale.value.mmPerPixel, 6)} mm/px</dd>
                      </div>
                      <div>
                        <dt>Scenario width range</dt>
                        <dd>{format(scale.value.highMm - scale.value.lowMm)} mm</dd>
                      </div>
                    </dl>
                    <div className="lab-formula">
                      <strong>W = P × L / S</strong>
                      <span>
                        W: part width · P: outline pixels · L: known length · S: reference pixels
                      </span>
                      <code>
                        Low = P × L / (S + 2δ)
                        <br />
                        High = P × L / (S − 2δ)
                      </code>
                    </div>
                  </>
                ) : active === 'layers' && layers.value ? (
                  <>
                    <p className="lab-output-label">Whole layers to cover the height</p>
                    <div className="lab-big-number">
                      {format(layers.value.count, 0)}
                      <span>layers</span>
                    </div>
                    <svg
                      className="lab-diagram"
                      viewBox="0 0 520 210"
                      role="img"
                      aria-label={`${layers.value.count} conceptual layers. Stack height ${format(layers.value.stackMm)} millimeters, excess ${format(layers.value.excessMm)} millimeters.`}
                    >
                      {layerBands(layers.value.count).map((band, i) => (
                        <rect
                          key={i}
                          x="80"
                          y={band.y}
                          width="260"
                          height={band.height}
                          className={band.first ? 'lab-first-layer' : 'lab-stack-layer'}
                        />
                      ))}
                      <line x1="60" x2="360" y1="185" y2="185" />
                      <text x="380" y="65">
                        {format(layers.value.stackMm)} mm
                      </text>
                      <text x="380" y="90">
                        stack height
                      </text>
                      <text x="80" y="207">
                        {layers.value.count > 26
                          ? 'Schematic: up to 26 representative bands'
                          : 'Schematic: first layer highlighted'}
                      </text>
                    </svg>
                    <dl className="lab-readings">
                      <div>
                        <dt>Excess over target</dt>
                        <dd>{format(layers.value.excessMm)} mm</dd>
                      </div>
                      <div>
                        <dt>Layer / nozzle ratio</dt>
                        <dd>{format(layers.value.nozzleRatio * 100, 1)}%</dd>
                      </div>
                    </dl>
                    <div className="lab-formula">
                      <strong>N = 1 + ceil(max(0, H − h₀) / h)</strong>
                      <span>
                        Stack = h₀ + (N − 1) × h<br />
                        H: part height · h₀: first layer · h: regular layer
                      </span>
                    </div>
                    {layers.value.profileReview && (
                      <p className="lab-caution">
                        Review the native profile: a layer reaches 80% of nozzle diameter or more.
                        This threshold is guidance, not a printer validation.
                      </p>
                    )}
                  </>
                ) : active === 'fit' && fit.value ? (
                  <>
                    <p className="lab-output-label">Next coupon CAD hole</p>
                    <div className="lab-big-number">
                      {format(fit.value.nextCadHoleMm)}
                      <span>mm</span>
                    </div>
                    <svg
                      className="lab-diagram"
                      viewBox="0 0 520 210"
                      role="img"
                      aria-label={`Target hole ${format(fit.value.targetHoleMm)} mm around shaft ${format(fitInput.shaftMm)} mm; desired diametral clearance ${format(fitInput.clearanceMm)} mm.`}
                    >
                      <circle cx="150" cy="103" r="76" className="lab-hole" />
                      <circle
                        cx="150"
                        cy="103"
                        r={76 * Math.min(1.2, fitInput.shaftMm / fit.value.targetHoleMm)}
                        className="lab-shaft"
                      />
                      <line x1="74" x2="226" y1="103" y2="103" />
                      <text x="270" y="74">
                        Target hole: {format(fit.value.targetHoleMm)} mm
                      </text>
                      <text x="270" y="105">
                        Shaft: {format(fitInput.shaftMm)} mm
                      </text>
                      <text x="270" y="136">
                        {fitInput.clearanceMm >= 0 ? 'Clearance' : 'Interference'}:{' '}
                        {format(Math.abs(fitInput.clearanceMm))} mm
                      </text>
                      <text x="150" y="204" textAnchor="middle">
                        Concentric cross-section schematic
                      </text>
                    </svg>
                    <dl className="lab-readings">
                      <div>
                        <dt>Observed hole bias</dt>
                        <dd>
                          {fit.value.biasMm >= 0 ? '+' : ''}
                          {format(fit.value.biasMm)} mm
                        </dd>
                      </div>
                      <div>
                        <dt>Radial clearance</dt>
                        <dd>{format(fit.value.radialClearanceMm)} mm</dd>
                      </div>
                    </dl>
                    <div className="lab-formula">
                      <strong>Next CAD = shaft + clearance − bias</strong>
                      <span>
                        Bias = measured coupon hole − coupon CAD hole.
                        <br />
                        Clearance is diametral; radial clearance is half.
                      </span>
                    </div>
                  </>
                ) : null}
              </div>
            </div>
            <div className="lab-assumptions">
              <h3>What this assumes</h3>
              {active === 'scale' ? (
                <>
                  <p>
                    Reference and outline share one image plane and a near front-on view. The two
                    endpoints move along the reference by δ in opposite directions. Perspective,
                    lens distortion, tracing errors and reference-length error are excluded.
                  </p>
                  <p>
                    This is a sensitivity scenario, not measurement uncertainty or a confidence
                    interval. Longer references usually reduce the effect of the same pixel shift.
                  </p>
                  <a
                    href="https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html"
                    target="_blank"
                    rel="noreferrer"
                  >
                    OpenCV camera model ↗
                  </a>
                  <a
                    href="https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-law-propagation-uncertainty"
                    target="_blank"
                    rel="noreferrer"
                  >
                    NIST uncertainty propagation ↗
                  </a>
                </>
              ) : active === 'layers' ? (
                <>
                  <p>
                    A flat base, one specified first layer and a constant regular layer height. The
                    count rounds up to cover the target height. Real slicers can use adaptive layers
                    and different top-surface decisions; this is not a toolpath or time estimate.
                  </p>
                  <a
                    href="https://help.prusa3d.com/article/layers-and-perimeters_1748"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Prusa layer and perimeter guidance ↗
                  </a>
                </>
              ) : (
                <>
                  <p>
                    A single coupon suggests a repeatable additive hole-diameter bias under the same
                    printer, material, orientation and settings. That assumption needs another
                    measured coupon. It does not establish fit, shrinkage across sizes, or
                    mechanical strength.
                  </p>
                  <p>
                    Negative clearance represents interference; the calculation cannot determine
                    whether an assembly will be possible or safe.
                  </p>
                  <a href="/reference-library/index.html#cad" target="_blank" rel="noreferrer">
                    Open the fit-coupon workspace ↗
                  </a>
                </>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
