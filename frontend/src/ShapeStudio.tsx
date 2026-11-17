import { useEffect, useRef, useState } from 'react';
import {
  ArrowClockwise,
  ArrowCounterClockwise,
  ArrowRight,
  Circle,
  Copy,
  DownloadSimple,
  FloppyDisk,
  Hexagon,
  Rectangle,
  Trash,
  Triangle,
  UploadSimple,
} from '@phosphor-icons/react';
import AppHeader from './AppHeader';
import ModelViewer from './ModelViewer';
import ShapeCanvas from './ShapeCanvas';
import { useStudioActive } from './StudioActivity';
import { onTemporaryExportsCleared, temporaryExportGeneration } from './temporaryExports';
import { handOff } from './handoff';
import { newShape, parseShapeDraft, shapeDraftIssue, shapeTemplate, SHAPE_LABELS } from './shapes';
import type { DesignShape, ShapeDraft, ShapeKind } from './shapes';
import type { ModelResult } from './types';
import './ShapeStudio.css';

async function requestJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : 'The CAD service could not complete this request.',
    );
  return data as T;
}
function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob),
    link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function release(id: string) {
  void fetch(`/api/models/${encodeURIComponent(id)}`, { method: 'DELETE', keepalive: true }).catch(
    () => {},
  );
}
const icons = {
  rectangle: Rectangle,
  rounded_rectangle: Rectangle,
  circle: Circle,
  slot: Rectangle,
  triangle: Triangle,
  hexagon: Hexagon,
};

export default function ShapeStudio() {
  const active = useStudioActive();
  const [draft, setDraft] = useState<ShapeDraft>(() => shapeTemplate('plate'));
  const [selectedId, setSelectedId] = useState('');
  const [operation, setOperation] = useState<'add' | 'cut'>('add');
  const [snap, setSnap] = useState(true);
  const [undo, setUndo] = useState<ShapeDraft[]>([]);
  const [redo, setRedo] = useState<ShapeDraft[]>([]);
  const [model, setModel] = useState<ModelResult | null>(null);
  const [readyKey, setReadyKey] = useState('');
  const [pending, setPending] = useState(false);
  const [failedKey, setFailedKey] = useState('');
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const owned = useRef<ModelResult | null>(null);
  const mounted = useRef(true);
  const sequence = useRef(0);
  const importSequence = useRef(0);
  const dragGroup = useRef(false);
  const dragRecorded = useRef(false);
  const input = useRef<HTMLInputElement>(null);
  const key = JSON.stringify(draft);
  const currentKey = useRef(key);
  currentKey.current = key;
  const issue = shapeDraftIssue(draft);
  const selected = draft.shapes.find((shape) => shape.id === selectedId) ?? draft.shapes[0];
  const ready = !!model && readyKey === key && !issue;

  function change(next: ShapeDraft) {
    if (JSON.stringify(next) === key) return;
    if (!dragGroup.current || !dragRecorded.current) {
      setUndo((history) => [...history.slice(-39), draft]);
      dragRecorded.current = dragGroup.current;
    }
    setRedo([]);
    setDraft(next);
    setError('');
  }
  function patch(id: string, values: Partial<DesignShape>) {
    change({
      ...draft,
      shapes: draft.shapes.map((shape) => (shape.id === id ? { ...shape, ...values } : shape)),
    });
  }
  function add(kind: ShapeKind) {
    const shape = newShape(kind, operation);
    change({ ...draft, shapes: [...draft.shapes, shape] });
    setSelectedId(shape.id);
  }
  function travel(direction: 'undo' | 'redo') {
    const source = direction === 'undo' ? undo : redo,
      previous = source.at(-1);
    if (!previous) return;
    if (direction === 'undo') {
      setUndo(source.slice(0, -1));
      setRedo((history) => [...history, draft]);
    } else {
      setRedo(source.slice(0, -1));
      setUndo((history) => [...history, draft]);
    }
    setDraft(previous);
    setError('');
  }

  useEffect(() => {
    if (!active || pending || issue || readyKey === key || failedKey === key) return;
    const timer = window.setTimeout(() => {
      const requestKey = key,
        generation = temporaryExportGeneration();
      const abort = new AbortController();
      controller.current = abort;
      const timeout = window.setTimeout(() => abort.abort(), 75000);
      setPending(true);
      setError('');
      void requestJSON<ModelResult>('/api/designer/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abort.signal,
        body: JSON.stringify({ ...draft, revision: String(++sequence.current) }),
      })
        .then((result) => {
          if (
            !mounted.current ||
            currentKey.current !== requestKey ||
            generation !== temporaryExportGeneration()
          ) {
            release(result.id);
            return;
          }
          const previous = owned.current;
          owned.current = result;
          setModel(result);
          setReadyKey(requestKey);
          setFailedKey('');
          if (previous && previous.id !== result.id) release(previous.id);
        })
        .catch((err) => {
          if (!mounted.current || currentKey.current !== requestKey) return;
          setFailedKey(requestKey);
          setError(
            err instanceof Error && !(err instanceof TypeError) && err.name !== 'AbortError'
              ? err.message
              : 'The preview could not update. Your shapes are still here. Retry when the CAD service is available.',
          );
        })
        .finally(() => {
          window.clearTimeout(timeout);
          if (controller.current === abort) controller.current = null;
          if (mounted.current) setPending(false);
        });
    }, 550);
    return () => window.clearTimeout(timer);
  }, [key, active, pending, issue, readyKey, failedKey, refreshToken]);

  useEffect(() => {
    mounted.current = true;
    const clear = () => {
      owned.current = null;
      setModel(null);
      setReadyKey('');
      setFailedKey('');
      setRefreshToken((token) => token + 1);
    };
    const unsubscribe = onTemporaryExportsCleared(clear);
    const leave = () => {
      const previous = owned.current;
      owned.current = null;
      if (previous) release(previous.id);
    };
    const restore = (event: PageTransitionEvent) => {
      if (event.persisted) clear();
    };
    window.addEventListener('pagehide', leave);
    window.addEventListener('pageshow', restore);
    return () => {
      mounted.current = false;
      importSequence.current++;
      controller.current?.abort();
      leave();
      unsubscribe();
      window.removeEventListener('pagehide', leave);
      window.removeEventListener('pageshow', restore);
    };
  }, []);

  async function download(kind: 'step' | 'stl' | 'dxf' | 'project', openWorkbench = false) {
    if (!model || !ready || downloading) return;
    const requestKey = key,
      id = model.id,
      generation = temporaryExportGeneration();
    setDownloading(true);
    setError('');
    try {
      const response = await fetch(model.downloads[kind]);
      if (!response.ok)
        throw new Error(
          response.status === 404
            ? 'These files expired. Select Retry preview to rebuild them.'
            : 'Could not download this file. Try again.',
        );
      const blob = await response.blob();
      if (
        !mounted.current ||
        currentKey.current !== requestKey ||
        owned.current?.id !== id ||
        generation !== temporaryExportGeneration()
      )
        return;
      if (openWorkbench)
        handOff(
          'workbench',
          new File([blob], 'shape-design.cad-project.json', { type: 'application/json' }),
        );
      else saveBlob(blob, `shape-design.${kind === 'project' ? 'cad-project.json' : kind}`);
    } catch (err) {
      if (currentKey.current === requestKey)
        setError(err instanceof Error ? err.message : 'Could not download.');
    } finally {
      if (mounted.current) setDownloading(false);
    }
  }
  async function importDesign(file?: File) {
    if (!file) return;
    const ticket = ++importSequence.current,
      before = currentKey.current;
    try {
      if (file.size > 100000) throw new Error('Choose a shape design smaller than 100 KB.');
      const parsed = parseShapeDraft(JSON.parse(await file.text()));
      if (ticket !== importSequence.current || !mounted.current) return;
      if (before !== currentKey.current)
        throw new Error(
          'Your design changed while opening the file. Open it again when you are ready.',
        );
      change(parsed);
      setSelectedId(parsed.shapes[0].id);
    } catch (err) {
      if (mounted.current)
        setError(err instanceof Error ? err.message : 'Could not open this design.');
    }
  }

  return (
    <div className="app-shell shape-shell">
      <AppHeader
        studio="designer"
        projectName="Common shapes → CAD"
        actions={
          <>
            <button className="text-button" onClick={() => input.current?.click()}>
              <UploadSimple size={19} />
              <span className="label-long">Open design</span>
              <span className="label-short">Open</span>
            </button>
            <button
              className="outlined-button"
              disabled={!!issue}
              onClick={() =>
                saveBlob(
                  new Blob(
                    [
                      JSON.stringify(
                        { format: 'pictures-to-cad-shapes', version: 1, design: draft },
                        null,
                        2,
                      ),
                    ],
                    { type: 'application/json' },
                  ),
                  'shape-design.json',
                )
              }
            >
              <FloppyDisk size={19} />
              <span className="label-long">Save design</span>
              <span className="label-short">Save</span>
            </button>
          </>
        }
      />
      <input
        ref={input}
        className="sr-only"
        tabIndex={-1}
        type="file"
        accept=".json,application/json"
        aria-label="Open saved shape design"
        onChange={(event) => {
          void importDesign(event.target.files?.[0]);
          event.target.value = '';
        }}
      />
      <main className="shape-main">
        <div className="shape-heading">
          <div>
            <p className="shape-eyebrow">SHAPE DESIGNER</p>
            <h1>Simple shapes. A solid start.</h1>
            <p>Add shapes, cut holes, set a thickness. Your CAD preview follows along.</p>
          </div>
          <a href="#workbench">
            Start from a photo instead <ArrowRight size={18} />
          </a>
        </div>
        <div className="shape-templates" aria-label="Starter designs">
          <span>Start with</span>
          {[
            ['plate', 'Mounting plate'],
            ['washer', 'Washer'],
            ['tab', 'Slotted tab'],
            ['blank', 'Blank plate'],
          ].map(([id, label]) => (
            <button
              key={id}
              onClick={() => {
                const next = shapeTemplate(id);
                change(next);
                setSelectedId(next.shapes[0].id);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="shape-layout">
          <section className="shape-panel shape-controls" aria-labelledby="shape-controls-title">
            <h2 id="shape-controls-title">Build your outline</h2>
            <label htmlFor="shape-name">Design name</label>
            <input
              id="shape-name"
              value={draft.name}
              maxLength={100}
              onChange={(event) => change({ ...draft, name: event.target.value })}
            />
            <div className="shape-operation" aria-label="New shape operation">
              <button aria-pressed={operation === 'add'} onClick={() => setOperation('add')}>
                Add material
              </button>
              <button aria-pressed={operation === 'cut'} onClick={() => setOperation('cut')}>
                Cut through
              </button>
            </div>
            <div className="shape-palette">
              {(Object.keys(SHAPE_LABELS) as ShapeKind[]).map((kind) => {
                const Icon = icons[kind];
                return (
                  <button
                    key={kind}
                    disabled={draft.shapes.length >= 16}
                    aria-label={`${operation === 'add' ? 'Add' : 'Cut'} ${SHAPE_LABELS[kind].toLowerCase()}`}
                    onClick={() => add(kind)}
                  >
                    <Icon size={23} />
                    <span>{SHAPE_LABELS[kind]}</span>
                  </button>
                );
              })}
            </div>
            <div className="shape-list" aria-label="Shapes in this design">
              {draft.shapes.map((shape, index) => (
                <button
                  key={shape.id}
                  aria-pressed={selected?.id === shape.id}
                  onClick={() => setSelectedId(shape.id)}
                >
                  <span className={`shape-dot ${shape.operation}`} />
                  {SHAPE_LABELS[shape.kind]} {index + 1}
                  <small>{shape.operation === 'cut' ? 'Cutout' : 'Material'}</small>
                </button>
              ))}
            </div>
            {selected && (
              <fieldset className="shape-properties">
                <legend>Selected {SHAPE_LABELS[selected.kind].toLowerCase()}</legend>
                <label>
                  Operation
                  <select
                    aria-label="Selected shape operation"
                    value={selected.operation}
                    onChange={(event) =>
                      patch(selected.id, { operation: event.target.value as 'add' | 'cut' })
                    }
                  >
                    <option value="add">Add material</option>
                    <option value="cut">Cut through</option>
                  </select>
                </label>
                <div className="shape-fields">
                  {(
                    [
                      [
                        'width_mm',
                        selected.kind === 'circle' ? 'Diameter (mm)' : 'Width (mm)',
                        0.5,
                        1000,
                      ],
                      ...(selected.kind === 'circle'
                        ? []
                        : [['height_mm', 'Height (mm)', 0.5, 1000]]),
                      ['x_mm', 'Center X (mm)', -1000, 1000],
                      ['y_mm', 'Center Y (mm)', -1000, 1000],
                      ['rotation_deg', 'Rotation (°)', -180, 180],
                      ...(selected.kind === 'rounded_rectangle'
                        ? [['corner_mm', 'Corner radius (mm)', 0, 500]]
                        : []),
                    ] as [keyof DesignShape, string, number, number][]
                  ).map(([field, label, min, max]) => (
                    <label key={field}>
                      {label}
                      <input
                        type="number"
                        aria-label={label}
                        min={min}
                        max={max}
                        step={field === 'rotation_deg' ? 1 : 0.5}
                        value={selected[field]}
                        onChange={(event) =>
                          patch(selected.id, { [field]: Number(event.target.value) })
                        }
                      />
                    </label>
                  ))}
                </div>
                <div className="shape-row">
                  <button
                    disabled={draft.shapes.length >= 16}
                    onClick={() => {
                      const clone = {
                        ...selected,
                        id: crypto.randomUUID(),
                        x_mm: Math.min(1000, selected.x_mm + 10),
                      };
                      change({ ...draft, shapes: [...draft.shapes, clone] });
                      setSelectedId(clone.id);
                    }}
                  >
                    <Copy size={17} />
                    Duplicate
                  </button>
                  <button
                    disabled={draft.shapes.length === 1}
                    onClick={() =>
                      change({
                        ...draft,
                        shapes: draft.shapes.filter((shape) => shape.id !== selected.id),
                      })
                    }
                  >
                    <Trash size={17} />
                    Remove
                  </button>
                </div>
              </fieldset>
            )}
          </section>
          <div className="shape-workspace">
            <section className="shape-panel" aria-labelledby="shape-outline-title">
              <div className="shape-section-heading">
                <h2 id="shape-outline-title">
                  2D outline <span>Millimeters</span>
                </h2>
                <div className="shape-row">
                  <button
                    aria-label="Undo shape edit"
                    disabled={!undo.length}
                    onClick={() => travel('undo')}
                  >
                    <ArrowCounterClockwise size={18} />
                  </button>
                  <button
                    aria-label="Redo shape edit"
                    disabled={!redo.length}
                    onClick={() => travel('redo')}
                  >
                    <ArrowClockwise size={18} />
                  </button>
                </div>
              </div>
              <ShapeCanvas
                shapes={draft.shapes}
                selected={selected?.id ?? ''}
                snap={snap}
                onSelect={setSelectedId}
                onMoveStart={() => {
                  dragGroup.current = true;
                  dragRecorded.current = false;
                }}
                onMoveEnd={() => {
                  dragGroup.current = false;
                }}
                onMove={(id, x, y) =>
                  patch(id, {
                    x_mm: Math.max(-1000, Math.min(1000, x)),
                    y_mm: Math.max(-1000, Math.min(1000, y)),
                  })
                }
              />
              <div className="shape-canvas-footer">
                <span>Drag to move · X right, Y down · overlapping material joins</span>
                <label>
                  <input
                    type="checkbox"
                    checked={snap}
                    onChange={(event) => setSnap(event.target.checked)}
                  />
                  Snap to 1 mm
                </label>
              </div>
            </section>
            <section className="shape-panel" aria-labelledby="shape-preview-title">
              <div className="shape-section-heading">
                <h2 id="shape-preview-title">CAD preview</h2>
                <label className="shape-thickness">
                  Thickness (mm)
                  <input
                    type="number"
                    min={0.1}
                    max={500}
                    step={0.5}
                    value={draft.thickness_mm}
                    onChange={(event) =>
                      change({ ...draft, thickness_mm: Number(event.target.value) })
                    }
                  />
                </label>
              </div>
              <div className="shape-preview">
                <ModelViewer
                  mesh={model?.mesh ?? null}
                  resetKey={0}
                  loading={pending}
                  emptyMessage={false}
                  color="#69b9c7"
                />
              </div>
              <p className="shape-build-status" role="status">
                {issue ||
                  (ready
                    ? `Preview up to date · ${model!.dimensions.width.toFixed(2)} × ${model!.dimensions.height.toFixed(2)} × ${model!.dimensions.thickness.toFixed(2)} mm · ${model!.hole_count} ${model!.hole_count === 1 ? 'cutout' : 'cutouts'}`
                    : pending
                      ? 'Updating the CAD solid… Your latest changes will follow.'
                      : failedKey === key
                        ? 'Preview needs attention.'
                        : 'Your changes will update the CAD preview automatically.')}
              </p>
              {(error || issue) && (
                <p className="shape-error" role="alert">
                  {error || issue}
                </p>
              )}
              <div className="shape-exports">
                {(['step', 'stl', 'dxf'] as const).map((kind) => (
                  <button
                    key={kind}
                    disabled={!ready || downloading}
                    onClick={() => void download(kind)}
                  >
                    <DownloadSimple size={17} />
                    {kind.toUpperCase()}
                  </button>
                ))}
                <button
                  disabled={pending || !!issue}
                  onClick={() => {
                    setReadyKey('');
                    setFailedKey('');
                    setRefreshToken((token) => token + 1);
                  }}
                >
                  <ArrowClockwise size={17} />
                  Retry preview
                </button>
                <button
                  disabled={!ready || downloading}
                  onClick={() => void download('project', true)}
                >
                  Open in flat-part workbench <ArrowRight size={17} />
                </button>
              </div>
              {model?.warnings.map((warning) => (
                <p className="shape-help" key={warning}>
                  {warning}
                </p>
              ))}
              <p className="shape-help">
                One connected, constant-thickness part. Cutouts go all the way through. CAD preview
                and exports use exact curves; test dimensions and fit before making.
              </p>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
