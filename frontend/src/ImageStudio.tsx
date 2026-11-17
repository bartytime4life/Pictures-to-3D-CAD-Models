import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowsCounterClockwise, DownloadSimple, Scan, Trash } from '@phosphor-icons/react';
import AppHeader from './AppHeader';
import { useStudioActive } from './StudioActivity';
import { handOff, takeHandoff } from './handoff';
import { saveStudioJson } from './studioFiles';
import {
  analyzeImage,
  compareImages,
  FULL_IMAGE,
  IMAGE_METHOD,
  SAMPLE_SIDE,
  SOBEL_MAXIMUM,
} from './imageAnalysis';
import type { Raster, Region } from './imageAnalysis';
import './ImageStudio.css';

type Slot = 'A' | 'B';
type Frame = {
  file: File;
  original: { width: number; height: number };
  raster: Raster;
  url: string;
};

async function sampleFile(file: File): Promise<Frame> {
  if (!file.size || file.size > 32 * 1024 * 1024)
    throw new Error('Choose an image between 1 byte and 32 MiB.');
  if (!/\.(png|jpe?g|webp|avif)$/i.test(file.name))
    throw new Error(
      'Choose PNG, JPEG, WebP or AVIF. Convert HEIC to one of these formats for image inspection.',
    );
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    throw new Error('This browser could not decode the image. Try a PNG or JPEG copy.');
  }
  try {
    if (bitmap.width * bitmap.height > 40_000_000)
      throw new Error('Choose an image with at most 40 megapixels.');
    const scale = Math.min(1, SAMPLE_SIDE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext('2d', { alpha: false });
    if (!context) throw new Error('Image sampling is unavailable in this browser.');
    context.fillStyle = '#ffffff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return {
      file,
      original: { width: bitmap.width, height: bitmap.height },
      raster: context.getImageData(0, 0, canvas.width, canvas.height),
      url: canvas.toDataURL('image/png'),
    };
  } finally {
    bitmap.close();
  }
}

const percent = (n: number) => (n > 0 && n < 0.1 ? '<0.1%' : `${n.toFixed(1)}%`);

export default function ImageStudio() {
  const active = useStudioActive();
  const [frames, setFrames] = useState<Partial<Record<Slot, Frame>>>({});
  const [selected, setSelected] = useState<Slot>('A');
  const [loading, setLoading] = useState<Partial<Record<Slot, boolean>>>({});
  const [errors, setErrors] = useState<Partial<Record<Slot, string>>>({});
  const tokens = useRef({ A: 0, B: 0 });
  const [region, setRegion] = useState<Region>(FULL_IMAGE);
  const [drag, setDrag] = useState<{
    start: { x: number; y: number };
    end: { x: number; y: number };
  } | null>(null);
  const gesture = useRef<typeof drag>(null);
  const inputA = useRef<HTMLInputElement>(null),
    inputB = useRef<HTMLInputElement>(null);

  const load = useCallback(async (slot: Slot, file: File) => {
    const token = ++tokens.current[slot];
    setLoading((old) => ({ ...old, [slot]: true }));
    setErrors((old) => ({ ...old, [slot]: '' }));
    try {
      const frame = await sampleFile(file);
      if (tokens.current[slot] !== token) return;
      gesture.current = null;
      setDrag(null);
      setFrames((old) => ({ ...old, [slot]: frame }));
    } catch (error) {
      if (tokens.current[slot] === token)
        setErrors((old) => ({
          ...old,
          [slot]: error instanceof Error ? error.message : 'Could not read this image.',
        }));
    } finally {
      if (tokens.current[slot] === token) setLoading((old) => ({ ...old, [slot]: false }));
    }
  }, []);

  useEffect(() => {
    if (!active) {
      gesture.current = null;
      setDrag(null);
      return;
    }
    const file = takeHandoff('image');
    if (file) {
      setSelected('A');
      setRegion(FULL_IMAGE);
      void load('A', file);
    }
  }, [active, load]);
  useEffect(
    () => () => {
      tokens.current.A++;
      tokens.current.B++;
    },
    [],
  );
  const frame = frames[selected];
  const stats = useMemo(() => (frame ? analyzeImage(frame.raster, region) : null), [frame, region]);
  const difference = useMemo(
    () => (frames.A && frames.B ? compareImages(frames.A.raster, frames.B.raster, region) : null),
    [frames, region],
  );
  const dragRegion = drag
    ? {
        x: Math.min(drag.start.x, drag.end.x),
        y: Math.min(drag.start.y, drag.end.y),
        width: Math.abs(drag.end.x - drag.start.x),
        height: Math.abs(drag.end.y - drag.start.y),
      }
    : region;

  function clear(slot: Slot) {
    tokens.current[slot]++;
    setFrames((old) => ({ ...old, [slot]: undefined }));
    setErrors((old) => ({ ...old, [slot]: '' }));
    setLoading((old) => ({ ...old, [slot]: false }));
    gesture.current = null;
    setDrag(null);
  }
  function editRegion(key: keyof Region, value: number) {
    if (!Number.isFinite(value)) return;
    gesture.current = null;
    setDrag(null);
    setRegion((old) => {
      const next = {
        ...old,
        [key]: Math.max(key === 'x' || key === 'y' ? 0 : 0.001, Math.min(value / 100, 1)),
      };
      next.x = Math.min(next.x, 0.999);
      next.y = Math.min(next.y, 0.999);
      next.width = Math.min(next.width, 1 - next.x);
      next.height = Math.min(next.height, 1 - next.y);
      return next;
    });
  }
  function exportMetrics() {
    if (!frame || !stats) return;
    const describe = (item: Frame | undefined) =>
      item
        ? {
            name: item.file.name,
            original: item.original,
            sampled: { width: item.raster.width, height: item.raster.height },
          }
        : null;
    saveStudioJson(
      {
        schema: 'pictures-to-cad-image-inspection-v1',
        createdAt: new Date().toISOString(),
        selected,
        sources: { A: describe(frames.A), B: describe(frames.B) },
        region,
        metrics: stats,
        difference,
        processing: {
          method: IMAGE_METHOD,
          maximumSide: SAMPLE_SIDE,
          alphaBacking: 'white',
          sobelMaximum: SOBEL_MAXIMUM,
          edgeSupport: 'interior-only, no padding',
          differenceThreshold: 24,
          alignment: 'none; identical sampled dimensions required',
        },
      },
      'image-inspection.json',
    );
  }

  return (
    <div className="app-shell image-studio">
      <AppHeader
        studio="image"
        projectName="Image inspection"
        actions={
          <button
            className="outlined-button"
            disabled={!stats || Object.values(loading).some(Boolean)}
            onClick={exportMetrics}
          >
            <DownloadSimple size={18} aria-hidden /> Save readings
          </button>
        }
      />
      <main className="image-main" id="image" tabIndex={-1}>
        <div className="image-intro">
          <span className="eyebrow">LOOK BEFORE YOU TRACE</span>
          <h1>Understand your source image.</h1>
          <p>
            Check contrast and exposure, isolate a region, or compare two images before making a
            part. Analysis stays in this browser.
          </p>
        </div>
        <div className="image-layout">
          <section className="image-panel image-source" aria-labelledby="image-source-title">
            <h2 id="image-source-title">Source images</h2>
            <p className="image-muted">
              PNG, JPEG, WebP or AVIF · up to 32 MiB / 40 MP. Originals stay unchanged.
            </p>
            {(['A', 'B'] as Slot[]).map((slot) => (
              <div className="image-file" key={slot}>
                <div className="image-file-heading">
                  <button
                    className={selected === slot ? 'image-choice selected' : 'image-choice'}
                    aria-pressed={selected === slot}
                    onClick={() => {
                      setSelected(slot);
                      gesture.current = null;
                      setDrag(null);
                    }}
                  >
                    Image {slot}
                  </button>
                  <button
                    className="icon-button"
                    aria-label={`Clear image ${slot}`}
                    disabled={!frames[slot] && !loading[slot] && !errors[slot]}
                    onClick={() => clear(slot)}
                  >
                    <Trash size={18} aria-hidden />
                  </button>
                </div>
                <p className="image-filename">
                  {frames[slot]?.file.name ??
                    (slot === 'B' ? 'Optional comparison image' : 'Choose your source image')}
                </p>
                <input
                  ref={slot === 'A' ? inputA : inputB}
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,.avif"
                  tabIndex={-1}
                  className="sr-only"
                  aria-label={`Choose image ${slot}`}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    event.target.value = '';
                    if (file) {
                      setSelected(slot);
                      gesture.current = null;
                      setDrag(null);
                      void load(slot, file);
                    }
                  }}
                />
                <button
                  className="outlined-button"
                  onClick={() => (slot === 'A' ? inputA : inputB).current?.click()}
                >
                  {frames[slot] ? 'Replace' : 'Open'} image {slot}
                </button>
                {loading[slot] && <p role="status">Reading image {slot}…</p>}
                {errors[slot] && (
                  <p className="image-error" role="alert">
                    {errors[slot]} {frames[slot] ? 'The previous image is retained.' : ''}
                  </p>
                )}
              </div>
            ))}
            <h3>Selected region</h3>
            <p className="image-muted">
              Drag on the image or enter percentages. Escape cancels a drag.
            </p>
            <div className="image-region">
              {(['x', 'y', 'width', 'height'] as const).map((key) => (
                <label key={key}>
                  {{ x: 'Left', y: 'Top', width: 'Width', height: 'Height' }[key]} (%)
                  <input
                    type="number"
                    min={key === 'x' || key === 'y' ? 0 : 0.1}
                    max="100"
                    step="0.1"
                    disabled={!frame}
                    value={Number((region[key] * 100).toFixed(3))}
                    onChange={(event) => {
                      if (event.target.value !== '') editRegion(key, event.target.valueAsNumber);
                    }}
                  />
                </label>
              ))}
            </div>
            <button
              className="text-button"
              disabled={!frame}
              onClick={() => {
                gesture.current = null;
                setDrag(null);
                setRegion(FULL_IMAGE);
              }}
            >
              <ArrowsCounterClockwise size={17} aria-hidden /> Full image
            </button>
          </section>
          <section className="image-panel image-preview" aria-labelledby="image-preview-title">
            <div className="image-panel-heading">
              <h2 id="image-preview-title">Image {selected}</h2>
              {frame && (
                <span>
                  {frame.raster.width} × {frame.raster.height} sampled px
                </span>
              )}
            </div>
            {frame ? (
              <>
                <div
                  className="image-canvas"
                  style={{ aspectRatio: `${frame.raster.width} / ${frame.raster.height}` }}
                >
                  <img
                    src={frame.url}
                    alt={`Sampled image ${selected}: ${frame.file.name}`}
                    draggable={false}
                  />
                  <svg
                    viewBox="0 0 1 1"
                    preserveAspectRatio="none"
                    aria-label="Drag to select an image region; numeric controls are beside the image"
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === 'Escape') {
                        gesture.current = null;
                        setDrag(null);
                      }
                    }}
                    onPointerDown={(event) => {
                      if (event.button !== 0 || !event.isPrimary) return;
                      const box = event.currentTarget.getBoundingClientRect();
                      const point = {
                        x: Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)),
                        y: Math.max(0, Math.min(1, (event.clientY - box.top) / box.height)),
                      };
                      gesture.current = { start: point, end: point };
                      setDrag(gesture.current);
                      event.currentTarget.setPointerCapture(event.pointerId);
                    }}
                    onPointerMove={(event) => {
                      if (!gesture.current) return;
                      const box = event.currentTarget.getBoundingClientRect();
                      gesture.current = {
                        ...gesture.current,
                        end: {
                          x: Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)),
                          y: Math.max(0, Math.min(1, (event.clientY - box.top) / box.height)),
                        },
                      };
                      setDrag(gesture.current);
                    }}
                    onPointerUp={(event) => {
                      const current = gesture.current;
                      gesture.current = null;
                      setDrag(null);
                      if (current) {
                        const width = Math.abs(current.end.x - current.start.x),
                          height = Math.abs(current.end.y - current.start.y);
                        if (width >= 1 / frame.raster.width && height >= 1 / frame.raster.height)
                          setRegion({
                            x: Math.min(current.start.x, current.end.x),
                            y: Math.min(current.start.y, current.end.y),
                            width,
                            height,
                          });
                      }
                      if (event.currentTarget.hasPointerCapture(event.pointerId))
                        event.currentTarget.releasePointerCapture(event.pointerId);
                    }}
                    onPointerCancel={() => {
                      gesture.current = null;
                      setDrag(null);
                    }}
                    onLostPointerCapture={() => {
                      gesture.current = null;
                      setDrag(null);
                    }}
                  >
                    <rect
                      x={dragRegion.x}
                      y={dragRegion.y}
                      width={dragRegion.width}
                      height={dragRegion.height}
                      fill="rgba(21,117,96,.12)"
                      stroke="#087e65"
                      strokeWidth="2"
                      vectorEffect="non-scaling-stroke"
                    />
                  </svg>
                </div>
                <p className="image-muted">
                  Original: {frame.original.width} × {frame.original.height} px. Sampling and white
                  transparency backing affect these readings.
                </p>
                <div className="image-handoff">
                  <button
                    className="primary-button"
                    disabled={!!loading[selected]}
                    onClick={() => handOff('workbench', frame.file)}
                  >
                    Open original in Flat part
                  </button>
                  <button
                    className="outlined-button"
                    disabled={!!loading[selected]}
                    onClick={() => handOff('relief', frame.file)}
                  >
                    Open original in Relief
                  </button>
                </div>
                <p className="image-muted">
                  The full original is sent to the selected studio; this region does not crop or
                  resize your CAD source.
                </p>
              </>
            ) : (
              <div className="image-empty">
                <Scan size={48} weight="light" aria-hidden />
                <h3>Open an image to inspect it</h3>
                <p>
                  Use image A for your source. Add image B to compare an edited version or another
                  capture.
                </p>
              </div>
            )}
          </section>
          <section className="image-panel image-readings" aria-labelledby="image-readings-title">
            <h2 id="image-readings-title">Region readings</h2>
            {stats ? (
              <>
                <p className="image-muted">
                  {stats.width} × {stats.height} sampled pixels · {stats.pixels.toLocaleString()}{' '}
                  total
                </p>
                <dl>
                  <dt>Mean brightness</dt>
                  <dd>
                    {stats.mean.toFixed(1)} <small>/ 255</small>
                  </dd>
                  <dt>Tonal spread (P05–P95)</dt>
                  <dd>
                    {stats.low}–{stats.high}
                  </dd>
                  <dt>Dark tones ≤15</dt>
                  <dd>{percent(stats.shadows)}</dd>
                  <dt>Bright tones ≥240</dt>
                  <dd>{percent(stats.highlights)}</dd>
                  <dt>Edge strength</dt>
                  <dd>
                    {stats.edgeStrength === null ? 'Unavailable' : percent(stats.edgeStrength)}
                  </dd>
                  <dt>Edge sample support</dt>
                  <dd>{stats.edgeSamples.toLocaleString()} pixels</dd>
                </dl>
                {stats.edgeStrength === null && (
                  <p className="image-notice">
                    Enlarge the region to at least 3 × 3 sampled pixels for an edge reading.
                  </p>
                )}
                <div
                  className="image-histogram"
                  role="img"
                  aria-label={`16-bin brightness histogram for image ${selected}, from dark to bright`}
                >
                  {stats.histogram.map((value, i) => (
                    <span
                      key={i}
                      style={{ height: `${(value / Math.max(...stats.histogram, 1)) * 100}%` }}
                      title={`${i * 16}–${i * 16 + 15}: ${value} pixels`}
                    />
                  ))}
                </div>
                <div className="image-histogram-axis">
                  <span>Dark</span>
                  <span>Bright</span>
                </div>
                <p className="image-muted">
                  Brightness is displayed sRGB luma. Edge strength is a texture/contrast proxy; it
                  is not focus quality, physical scale or a percentage of edge pixels.
                </p>
                <h3>A / B comparison</h3>
                {difference ? (
                  <>
                    <dl>
                      <dt>Mean absolute difference</dt>
                      <dd>
                        {difference.meanAbsoluteDifference.toFixed(2)} <small>/ 255</small>
                      </dd>
                      <dt>Pixels differing ≥24</dt>
                      <dd>{percent(difference.changedPercent)}</dd>
                    </dl>
                    <p className="image-muted">
                      Same region, pixel-aligned only. Lighting and movement also create
                      differences.
                    </p>
                  </>
                ) : (
                  <p className="image-notice">
                    {frames.A && frames.B
                      ? 'Sample sizes differ. Use matching image dimensions to compare; no automatic alignment is applied.'
                      : 'Open both images to compare their sampled pixels.'}
                  </p>
                )}
              </>
            ) : (
              <p className="image-muted">Readings appear after you open an image.</p>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
