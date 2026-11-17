import { useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, ReactNode } from 'react';
import {
  ArrowCounterClockwise,
  ArrowSquareOut,
  ArrowsHorizontal,
  ArrowsOut,
  Camera,
  CheckCircle,
  Cube,
  DownloadSimple,
  Eye,
  EyeSlash,
  FloppyDisk,
  Image as ImageIcon,
  Info,
  Minus,
  PencilSimple,
  Polygon,
  Plus,
  Question,
  Ruler,
  SpinnerGap,
  Stack,
  UploadSimple,
  WarningCircle,
  X,
} from '@phosphor-icons/react';
import AppHeader from './AppHeader';
import { useStudioActive } from './StudioActivity';
import { publishTemporaryExportsCleared, temporaryExportGeneration } from './temporaryExports';
import { takeHandoff } from './handoff';
import ModelViewer from './ModelViewer';
import LocalAssistant from './LocalAssistant';
import PrintSettings from './PrintSettings';
import QuickEdit from './QuickEdit';
import PrintPreparation from './PrintPreparation';
import BackgroundRemoval, { type BackgroundPreview } from './BackgroundRemoval';
import {
  createDesignHistory,
  sameDesign,
  recordDesignChange,
  undoDesignChange,
  redoDesignChange,
} from './designHistory';
import ReferenceCalibration from './ReferenceCalibration';
import SheetReference from './SheetReference';
import SlicerHandoff from './SlicerHandoff';
import ExportFormats from './ExportFormats';
import { calibrationError, measuredHeightError, referenceWidth } from './calibration';
import { heightCheckDraft, heightCheckSettingsError } from './heightCheck';
import { workflowState } from './workflow';
import { DEFAULT_DESIGN, designError, designFromProposal, parseDesign } from './design';
import {
  NO_SHEET,
  appendSheetFields,
  fitCounts,
  primitivesShapeError,
  sheetChoiceError,
  sheetLabel,
  sheetWidthMm,
} from './sheet';
import type {
  AssistantProposal,
  DesignSettings,
  Detail,
  ExportKind,
  ModelResult,
  Point,
  Profile,
  ProjectRecipe,
  ReferenceCalibration as Calibration,
  SheetChoice,
  SlicerId,
  SlicerLaunch,
  TraceResult,
} from './types';

type ModalName = 'photo' | 'trace' | 'guide' | 'export' | null;
type Unit = 'mm' | 'in';
// What "Try again" repeats. It names the failed operation rather than capturing it, so a retry
// always runs with the inputs on screen when it is clicked, never with an earlier render's.
type RetryAction =
  | { kind: 'sample' }
  | { kind: 'photo'; file: File; isSample: boolean }
  | { kind: 'build'; openExport: boolean }
  | {
      kind: 'retrace';
      detail: Detail;
      threshold: number;
      inverted: boolean;
      sheet: SheetChoice;
      snap: boolean;
    }
  | { kind: 'proposal'; proposal: AssistantProposal }
  | { kind: 'restore'; file: File }
  | { kind: 'clear' };
const MAX_PHOTO = 32 * 1024 * 1024;
const MAX_PROJECT = 10 * 1024 * 1024;
// HEIC is the default photo format of recent phones. Some browsers report no type for
// it, so the file name is accepted as well.
const PHOTO_TYPES = [
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/heic',
  'image/heif',
  'image/avif',
];
const PHOTO_NAME = /\.(heic|heif|avif)$/i;

/** The backend's project-name rule: no control characters, no surrounding space, nonempty. */
function cleanName(value: string) {
  return value.replace(/[\u0000-\u001f\u007f]/g, '').trim() || 'Untitled part';
}

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 85000);
  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const reason =
        typeof data.detail === 'string'
          ? data.detail
          : 'The request could not be completed. Check your inputs and try again.';
      throw new Error(reason);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw new Error('This request took too long. Your inputs are still here; try again.');
    if (error instanceof TypeError)
      throw new Error('Could not reach the CAD service. Check the connection and try again.');
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Try again.';
}

function downloadJson(recipe: ProjectRecipe) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(recipe, null, 2)], { type: 'application/json' }),
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = `${recipe.name.replace(/[^a-zA-Z0-9_-]+/g, '-').slice(0, 60) || 'part'}.cad-project.json`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function parseRecipe(value: unknown): ProjectRecipe {
  const recipe = value as Partial<ProjectRecipe> | null;
  if (
    !recipe ||
    recipe.format !== 'pictures-to-cad' ||
    (recipe.version !== 1 && recipe.version !== 2 && recipe.version !== 3) ||
    typeof recipe.name !== 'string' ||
    recipe.name.length > 100
  )
    throw new Error(
      'This is not a supported Pictures to CAD project. Choose a version 1, 2 or 3 project JSON file.',
    );
  if (
    !Number.isFinite(recipe.width_mm) ||
    !Number.isFinite(recipe.thickness_mm) ||
    recipe.width_mm! < 0.1 ||
    recipe.width_mm! > 2000 ||
    recipe.thickness_mm! < 0.1 ||
    recipe.thickness_mm! > 500
  )
    throw new Error(
      'This project has invalid dimensions. Reference width must be 0.1–2000 mm and thickness 0.1–500 mm.',
    );
  const profile = recipe.profile;
  const validLoop = (loop: unknown): loop is Point[] =>
    Array.isArray(loop) &&
    loop.length >= 3 &&
    loop.every(
      (p) =>
        Array.isArray(p) &&
        p.length === 2 &&
        p.every((v) => typeof v === 'number' && Number.isFinite(v) && Math.abs(v) <= 100000),
    );
  if (
    !profile ||
    !validLoop(profile.outer) ||
    !Array.isArray(profile.holes) ||
    profile.holes.length > 32 ||
    !profile.holes.every(validLoop) ||
    profile.outer.length + profile.holes.reduce((n, h) => n + h.length, 0) > 2000
  )
    throw new Error('This project contains an invalid or overly complex outline.');
  const fittedIssue = primitivesShapeError(profile);
  if (fittedIssue) throw new Error(fittedIssue);
  if (
    profile.reference !== undefined &&
    (typeof profile.reference !== 'object' ||
      !(Number.isFinite(profile.reference?.mm_per_px) && profile.reference.mm_per_px > 0))
  )
    throw new Error('This project has an invalid reference-sheet record.');
  if (recipe.reference_calibration !== undefined) {
    const evidence = recipe.reference_calibration;
    const issue = calibrationError(evidence);
    if (issue) throw new Error(`This project has invalid reference measurements. ${issue}`);
    const frame = evidence.image_size;
    if (
      [profile.outer, ...profile.holes].some((loop) =>
        loop.some(([x, y]) => x < 0 || y < 0 || x > frame.width || y > frame.height),
      )
    )
      throw new Error('This project outline is outside its reference working image.');
    const calculated = referenceWidth(evidence, getBounds(profile).width);
    if (
      !Number.isFinite(calculated) ||
      Math.abs(calculated - recipe.width_mm!) > Math.max(1e-6, recipe.width_mm! * 1e-8)
    )
      throw new Error('This project reference scale does not match its saved outside width.');
    // Keep only the supported measurement notes, never unrelated fields from an imported file.
    recipe.reference_calibration = {
      known_length_mm: evidence.known_length_mm,
      reference_points: evidence.reference_points.map(([x, y]) => [x, y]) as [Point, Point],
      image_size: { width: frame.width, height: frame.height },
    };
  }
  if (
    recipe.measured_height_mm !== undefined &&
    (typeof recipe.measured_height_mm !== 'number' ||
      measuredHeightError(String(recipe.measured_height_mm), 1))
  )
    throw new Error('This project has an invalid independent height measurement.');
  if (recipe.height_check !== undefined) {
    const issue = heightCheckSettingsError(recipe.height_check);
    if (issue || recipe.measured_height_mm === undefined)
      throw new Error(
        `This project has an invalid height check. ${issue ?? 'An independent height measurement is required.'}`,
      );
    recipe.height_check = {
      allowance_mm: recipe.height_check.allowance_mm,
      measurement_bound_mm: recipe.height_check.measurement_bound_mm,
    };
  }
  if (recipe.version !== 1) recipe.design = parseDesign(recipe.design);
  return recipe as ProjectRecipe;
}

function getBounds(profile: Profile) {
  const xs = profile.outer.map((p) => p[0]);
  const ys = profile.outer.map((p) => p[1]);
  const x = Math.min(...xs),
    y = Math.min(...ys);
  return { x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y };
}

function Modal({
  title,
  eyebrow,
  children,
  onClose,
  onFocusLost,
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  onClose: () => void;
  /** Receives the opener when closing into busy work left it disabled and unfocusable. */
  onFocusLost: (opener: HTMLElement) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    const previousFocus = document.activeElement as HTMLElement | null;
    dialog?.showModal();
    return () => {
      dialog?.close();
      if (!previousFocus || previousFocus === document.body || !previousFocus.isConnected) return;
      previousFocus.focus();
      // onFocusLost only records the element in a ref, so the first render's callback suffices.
      if (document.activeElement !== previousFocus) onFocusLost(previousFocus);
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby="modal-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="modal-header">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h2 id="modal-title">{title}</h2>
        </div>
        <button className="icon-button close-button" aria-label="Close dialog" onClick={onClose}>
          <X size={24} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

function SourceCanvas({
  trace,
  showOutline,
  widthLabel,
  imageUrl,
}: {
  trace: TraceResult | null;
  showOutline: boolean;
  widthLabel: string;
  imageUrl?: string;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const container = useRef<HTMLDivElement>(null);
  const active = useStudioActive();
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const sourceImage = useMemo(() => {
    const image = new window.Image();
    if (trace?.image.data_url) image.src = imageUrl ?? trace.image.data_url;
    return image;
  }, [trace, imageUrl]);
  const fit = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  const changeZoom = (factor: number) =>
    setZoom((value) => Math.min(8, Math.max(0.5, value * factor)));
  useEffect(fit, [trace]);
  useEffect(() => {
    if (!active || !trace || !canvas.current || !container.current) return;
    const image = sourceImage;
    let disposed = false;
    const draw = () => {
      if (disposed || !canvas.current || !container.current) return;
      const el = canvas.current;
      const ctx = el.getContext('2d');
      if (!ctx) return;
      const width = container.current.clientWidth,
        height = container.current.clientHeight;
      if (!width || !height) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      el.width = width * dpr;
      el.height = height * dpr;
      ctx.scale(dpr, dpr);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, width, height);
      if (imageUrl) {
        const cell = 16;
        ctx.fillStyle = '#d4dce0';
        for (let y = 0; y < height; y += cell)
          for (let x = 0; x < width; x += cell)
            if ((x / cell + y / cell) % 2 === 0) ctx.fillRect(x, y, cell, cell);
      }
      const b = trace.bounds;
      const marginX = b.width * 0.09;
      const marginY = Math.max(b.height * 0.48, b.width * 0.17);
      const crop = {
        x: b.x - marginX,
        y: b.y - marginY,
        width: b.width + marginX * 2,
        height: b.height + marginY * 2,
      };
      // Fit the outline and its ruler into the space left by the actual controls.
      // The filename strip and inspection hint overlay this canvas, so the canvas
      // edge alone is not a safe lower bound, especially on a phone.
      const tools = container.current.querySelector<HTMLElement>('.source-inspection-tools');
      const hint = container.current.querySelector<HTMLElement>('.source-inspection-hint');
      const caption =
        container.current.parentElement?.querySelector<HTMLElement>('.source-caption');
      const contentTop = width < 480 && tools ? tools.offsetTop + tools.offsetHeight + 12 : 12;
      const contentBottom = Math.min(
        height - 12,
        hint?.offsetHeight ? hint.offsetTop - 12 : height,
        caption?.offsetHeight ? caption.offsetTop - 12 : height,
      );
      const profileBottom = Math.max(contentTop + 1, contentBottom - (widthLabel ? 60 : 0));
      const fitScale = Math.min(
        width / crop.width,
        height / crop.height,
        Math.max(1, width - 32) / b.width,
        (profileBottom - contentTop) / b.height,
      );
      const fittedHalfHeight = (b.height * fitScale) / 2;
      const centerY = Math.min(
        Math.max(height / 2, contentTop + fittedHalfHeight),
        profileBottom - fittedHalfHeight,
      );
      const scale = fitScale * zoom;
      const ox = width / 2 - (b.x + b.width / 2) * scale + pan.x;
      const oy = centerY - (b.y + b.height / 2) * scale + pan.y;
      if (trace.image.data_url && image.complete && image.naturalWidth) {
        ctx.drawImage(image, ox, oy, trace.image.width * scale, trace.image.height * scale);
      }
      const point = (p: Point): Point => [ox + p[0] * scale, oy + p[1] * scale];
      if (showOutline || !trace.image.data_url) {
        for (const loop of [trace.profile.outer, ...trace.profile.holes]) {
          ctx.beginPath();
          loop.forEach((p, index) => {
            const [x, y] = point(p);
            if (!index) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          });
          ctx.closePath();
          ctx.strokeStyle = '#00b9e8';
          ctx.lineWidth = 2;
          ctx.stroke();
          const count = Math.min(loop.length, 8);
          for (let n = 0; n < count; n++) {
            const p = loop[Math.floor((n * loop.length) / count)];
            const [x, y] = point(p);
            ctx.beginPath();
            ctx.arc(x, y, 3.7, 0, Math.PI * 2);
            ctx.fillStyle = '#fff';
            ctx.fill();
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
        }
      }
      const x1 = ox + b.x * scale,
        x2 = ox + (b.x + b.width) * scale;
      const bottom = oy + (b.y + b.height) * scale;
      const y = Math.min(contentBottom - 16, bottom + 44);
      if (widthLabel && y > bottom + 12) {
        ctx.strokeStyle = '#00b9e8';
        ctx.lineWidth = 1.3;
        ctx.beginPath();
        ctx.moveTo(x1, bottom + 8);
        ctx.lineTo(x1, y + 12);
        ctx.moveTo(x2, bottom + 8);
        ctx.lineTo(x2, y + 12);
        ctx.moveTo(x1, y);
        ctx.lineTo(x2, y);
        ctx.stroke();
        for (const [x, d] of [
          [x1, 1],
          [x2, -1],
        ]) {
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(x + d * 11, y - 5);
          ctx.lineTo(x + d * 11, y + 5);
          ctx.closePath();
          ctx.fillStyle = '#00b9e8';
          ctx.fill();
        }
        ctx.font = '500 17px "JetBrains Mono Variable",monospace';
        const textWidth = ctx.measureText(widthLabel).width;
        ctx.fillStyle = '#f9fafb';
        const labelX = (x1 + x2) / 2;
        ctx.fillRect(labelX - textWidth / 2 - 13, y - 16, textWidth + 26, 32);
        ctx.strokeStyle = '#00b9e8';
        ctx.strokeRect(labelX - textWidth / 2 - 13, y - 16, textWidth + 26, 32);
        ctx.fillStyle = '#202a30';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(widthLabel, labelX, y + 1);
      }
    };
    const observer = new ResizeObserver(draw);
    observer.observe(container.current);
    image.onload = draw;
    draw();
    return () => {
      disposed = true;
      image.onload = null;
      observer.disconnect();
    };
  }, [trace, showOutline, widthLabel, imageUrl, zoom, pan, active, sourceImage]);
  return (
    <div
      className="source-canvas"
      ref={container}
      data-background={imageUrl ? 'removed' : 'original'}
      data-source-zoom={zoom.toFixed(2)}
      role="region"
      aria-label="Source inspection. Drag to pan; arrow keys to move, plus or minus to zoom, zero to fit."
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        const moves: Record<string, [number, number]> = {
          ArrowLeft: [-30, 0],
          ArrowRight: [30, 0],
          ArrowUp: [0, -30],
          ArrowDown: [0, 30],
        };
        if (moves[event.key]) {
          event.preventDefault();
          const [x, y] = moves[event.key];
          setPan((value) => ({ x: value.x + x, y: value.y + y }));
        } else if (['+', '=', '-', '0'].includes(event.key)) {
          event.preventDefault();
          if (event.key === '0') fit();
          else changeZoom(event.key === '-' ? 1 / 1.25 : 1.25);
        }
      }}
    >
      <canvas
        ref={canvas}
        onPointerDown={(event) => {
          event.currentTarget.setPointerCapture(event.pointerId);
          drag.current = { x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y };
        }}
        onPointerMove={(event) => {
          if (drag.current)
            setPan({
              x: drag.current.panX + event.clientX - drag.current.x,
              y: drag.current.panY + event.clientY - drag.current.y,
            });
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
        role="img"
        aria-label={
          trace
            ? `Source outline with ${trace.profile.holes.length} through holes. Reference width ${widthLabel || 'not set'}.`
            : 'No source photo loaded'
        }
      />
      <div className="source-inspection-tools" role="group" aria-label="Source zoom">
        <button
          type="button"
          aria-label="Zoom source out"
          onClick={() => changeZoom(1 / 1.25)}
          disabled={zoom <= 0.5}
        >
          <Minus size={18} />
        </button>
        <output aria-live="polite">{Math.round(zoom * 100)}%</output>
        <button
          type="button"
          aria-label="Zoom source in"
          onClick={() => changeZoom(1.25)}
          disabled={zoom >= 8}
        >
          <Plus size={18} />
        </button>
        <button type="button" aria-label="Fit source image" onClick={fit}>
          <ArrowsOut size={18} />
        </button>
      </div>
      <span className="source-inspection-hint">Drag to inspect · dimensions stay unchanged</span>
    </div>
  );
}

export default function App() {
  const active = useStudioActive();
  const activeRef = useRef(active);
  activeRef.current = active;
  const [name, setName] = useState('Mounting plate');
  const [editingName, setEditingName] = useState(false);
  const [trace, setTrace] = useState<TraceResult | null>(null);
  const [backgroundPreview, setBackgroundPreview] = useState<BackgroundPreview | null>(null);
  const [prepareOpen, setPrepareOpen] = useState(false);
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [model, setModel] = useState<ModelResult | null>(null);
  const modelRef = useRef<ModelResult | null>(null);
  const [width, setWidth] = useState('80.00');
  const [thickness, setThickness] = useState('4.00');
  const [unit, setUnit] = useState<Unit>('mm');
  const [widthMm, setWidthMm] = useState(80);
  const [thicknessMm, setThicknessMm] = useState(4);
  const [referenceCalibration, setReferenceCalibration] = useState<Calibration | null>(null);
  const [measuredHeight, setMeasuredHeight] = useState('');
  const [heightAllowance, setHeightAllowance] = useState('');
  const [heightBound, setHeightBound] = useState('');
  const [measurementReset, setMeasurementReset] = useState(0);
  const [measurementReview, setMeasurementReview] = useState<{
    request: number;
    target: 'height' | 'decision';
  }>({ request: 0, target: 'height' });
  const [designReview, setDesignReview] = useState(0);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [exportError, setExportError] = useState('');
  const [selectedSlicer, setSelectedSlicer] = useState<SlicerId>('bambu');
  const [detail, setDetail] = useState<Detail>('standard');
  const [threshold, setThreshold] = useState(-1);
  const [inverted, setInverted] = useState(false);
  // The reference-sheet choice and snapping persist across photos: a user who measures on
  // a sheet usually keeps doing so. The bundled sample is always traced without one.
  const [sheetChoice, setSheetChoice] = useState<SheetChoice>(NO_SHEET);
  const [snap, setSnap] = useState(true);
  const [draftSheet, setDraftSheet] = useState<SheetChoice>(NO_SHEET);
  const [draftSnap, setDraftSnap] = useState(true);
  const [design, setDesign] = useState<DesignSettings>({ ...DEFAULT_DESIGN });
  const [designHistory, setDesignHistory] = useState(createDesignHistory);
  const lastValidDesign = useRef(design);
  const historyEditKey = useRef<string | undefined>(undefined);
  const [assistantUndo, setAssistantUndo] = useState<{
    trace: TraceResult | null;
    detail: Detail;
    threshold: number;
    inverted: boolean;
    design: DesignSettings;
    preview: ModelResult | null;
    width: string;
    unit: Unit;
    widthMm: number;
    referenceCalibration: Calibration | null;
  } | null>(null);
  const [draftThreshold, setDraftThreshold] = useState(150);
  const [draftAuto, setDraftAuto] = useState(true);
  const [draftInverted, setDraftInverted] = useState(false);
  const [revision, setRevision] = useState(0);
  const [sample, setSample] = useState(true);
  const [busy, setBusy] = useState<string | null>('Loading sample…');
  const [error, setErrorMessage] = useState('');
  const [retry, setRetry] = useState<RetryAction | null>(null);
  const [notice, setNotice] = useState('');
  const [modal, setModal] = useState<ModalName>(null);
  const [outline, setOutline] = useState(true);
  const [resetKey, setResetKey] = useState(0);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const widthInput = useRef<HTMLInputElement>(null);
  const thicknessInput = useRef<HTMLInputElement>(null);
  const measurementTools = useRef<HTMLDivElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);
  const revisionRef = useRef(0);
  const sequenceRef = useRef(0);
  // An element that lost focus because busy work disabled it, or a dialog that closed into busy
  // work could not return focus to its disabled opener. Restored once the work finishes.
  const pendingFocusRef = useRef<HTMLElement | null>(null);
  const unitFactor = unit === 'in' ? 25.4 : 1;

  const validWidth =
    width.trim() !== '' && Number.isFinite(widthMm) && widthMm >= 0.1 && widthMm <= 2000;
  const validThickness =
    thickness.trim() !== '' &&
    Number.isFinite(thicknessMm) &&
    thicknessMm >= 0.1 &&
    thicknessMm <= 500;
  const dimensionsValid = validWidth && validThickness;
  const sourceSize =
    trace && dimensionsValid
      ? {
          width: widthMm,
          height: (trace.bounds.height / trace.bounds.width) * widthMm,
          thickness: thicknessMm,
        }
      : null;
  const designIssue = designError(design, sourceSize);
  useEffect(() => {
    if (!designIssue) lastValidDesign.current = design;
  }, [design, designIssue]);
  const buildReady = dimensionsValid && !designIssue;
  const current = !!model && model.revision === String(revision);
  const stale = !!model && !current;
  const nextStep = workflowState({
    hasTrace: !!trace,
    hasModel: !!model,
    current,
    validWidth,
    validThickness,
    designIssue,
    busy,
  });
  const activeStage = busy
    ? null
    : modal === 'photo'
      ? 'photo'
      : modal === 'trace'
        ? 'trace'
        : modal === 'export'
          ? 'export'
          : nextStep.stage;
  useEffect(() => {
    if (!measurementReview.request) return;
    const check = measurementTools.current?.querySelector('.height-check')?.closest('details');
    if (!check) return;
    check.open = true;
    const inputs = Array.from(check.querySelectorAll('input'));
    const candidates = measurementReview.target === 'height' ? inputs.slice(0, 1) : inputs.slice(1);
    const target =
      candidates.find((input) => !input.validity.valid) ??
      candidates.find((input) => !input.value.trim()) ??
      candidates.find((input) => input.getAttribute('aria-invalid') === 'true') ??
      candidates[0];
    target?.focus();
  }, [measurementReview]);
  const displayNumber = (millimeters: number) =>
    (millimeters / unitFactor).toFixed(unit === 'in' ? 3 : 2);
  const widthLabel = validWidth ? `${displayNumber(widthMm)} ${unit}` : '';

  function releaseModel(id: string) {
    void fetch(`/api/models/${encodeURIComponent(id)}`, { method: 'DELETE' }).catch(() => {});
  }
  function installModel(result: ModelResult) {
    const previous = modelRef.current;
    modelRef.current = result;
    setModel(result);
    if (result.design) {
      if (!sameDesign(design, result.design)) setDesignHistory(createDesignHistory());
      setDesign(result.design);
    }
    if (previous && previous.id !== result.id) releaseModel(previous.id);
  }
  function projectName() {
    return cleanName(name);
  }
  function invalidate(clearHistory = true) {
    if (clearHistory) {
      setDesignHistory(createDesignHistory());
      historyEditKey.current = undefined;
    }
    setAssistantUndo(null);
    const next = ++revisionRef.current;
    setRevision(next);
    setNotice('');
    return String(next);
  }
  function changeDesign(next: DesignSettings, editKey?: string) {
    if (busy || sameDesign(design, next)) return;
    // A numeric replacement is one edit, even when intermediate keystrokes are
    // invalid or happen to form a valid number. Never put a draft in history.
    if (!designError(next, sourceSize)) {
      const previous = lastValidDesign.current;
      const changed = !sameDesign(previous, next);
      if (designError(previous, sourceSize)) setDesignHistory(createDesignHistory());
      else if (changed && (!editKey || historyEditKey.current !== editKey))
        setDesignHistory((history) => recordDesignChange(history, previous, next));
      lastValidDesign.current = next;
      if (changed || !editKey) historyEditKey.current = editKey;
    }
    setDesign(next);
    invalidate(false);
    setError('');
  }
  function travelDesign(direction: 'undo' | 'redo') {
    if (busy) return;
    historyEditKey.current = undefined;
    const valid = lastValidDesign.current;
    const result =
      direction === 'undo'
        ? undoDesignChange(designHistory, valid)
        : redoDesignChange(designHistory, valid);
    if (!result) return;
    setDesign(result.design);
    setDesignHistory(result.history);
    invalidate(false);
    setError('');
    setNotice('Design settings restored. Update the preview before exporting.');
  }
  /** Show (or clear) an error. Only an error given its own retry action offers "Try again". */
  function setError(message: string, retryAction: RetryAction | null = null) {
    setErrorMessage(message);
    setRetry(message ? retryAction : null);
  }
  function retryFailed() {
    if (!retry || busy) return;
    switch (retry.kind) {
      case 'sample':
        return void loadSample();
      case 'photo':
        return void loadPhoto(retry.file, retry.isSample);
      case 'build':
        return void buildModel(retry.openExport);
      case 'retrace':
        return void retrace(retry.detail, retry.threshold, retry.inverted, retry.sheet, retry.snap);
      case 'proposal':
        return void applyAssistantProposal(retry.proposal);
      case 'restore':
        return void restoreProject(retry.file);
      case 'clear':
        return void clearTemporaryExports();
    }
  }
  function rememberFocus(element: Element | null) {
    if (
      !pendingFocusRef.current &&
      element instanceof HTMLElement &&
      element !== document.body &&
      element.isConnected &&
      !element.closest('dialog')
    )
      pendingFocusRef.current = element;
  }
  /** Start busy work, first noting the focused control that disabling it would strand. */
  function startBusy(label: string) {
    rememberFocus(document.activeElement);
    setBusy(label);
  }

  async function requestTrace(
    file: File,
    newDetail: Detail,
    newThreshold: number,
    newInverted: boolean,
    sheet: SheetChoice = NO_SHEET,
    sheetThickness: number | null = null,
    snapIntent = true,
    fallback = false,
  ) {
    const body = new FormData();
    body.append('file', file);
    body.append('detail', newDetail);
    body.append('threshold', String(newThreshold));
    body.append('inverted', String(newInverted));
    appendSheetFields(body, sheet, sheetThickness, snapIntent, fallback);
    return api<TraceResult>('/api/trace', { method: 'POST', body });
  }
  /** Keep scale evidence visible before routine next-step guidance. */
  function sheetCalibrationNotice(result: TraceResult) {
    return (
      result.warnings.find((w) => w.includes('proportions in the photo differ')) ??
      result.warnings.find((w) => w.startsWith('Sheet orientation uses')) ??
      result.warnings.find((w) => w.startsWith("Perspective makes the sheet's long edges")) ??
      ''
    );
  }
  /** Use the sheet scale of a reference-sheet trace as the outside width. */
  function applySheetWidth(result: TraceResult) {
    const fromSheet = sheetWidthMm(result.profile);
    if (fromSheet === null) return false;
    setReferenceCalibration(null);
    setWidthMm(fromSheet);
    setWidth((fromSheet / unitFactor).toFixed(unit === 'in' ? 6 : 4));
    return true;
  }
  async function requestModel(
    profile: Profile,
    w: number,
    t: number,
    projectName: string,
    rev: string,
    settings: DesignSettings = design,
  ) {
    return api<ModelResult>('/api/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile,
        width_mm: w,
        thickness_mm: t,
        name: projectName || 'Untitled part',
        revision: rev,
        design: settings,
      }),
    });
  }

  async function loadPhoto(file: File, isSample = false) {
    // A photo handed over from the library opens while the initial "Loading sample…" state is
    // still set, so a refusal here must end it rather than leave every control disabled.
    if (file.size > MAX_PHOTO) {
      setError('This photo is too large. Choose an image smaller than 32 MiB.');
      setBusy(null);
      return;
    }
    const sheetIssue = isSample ? null : sheetChoiceError(sheetChoice);
    if (sheetIssue) {
      setError(sheetIssue);
      setBusy(null);
      return;
    }
    const sequence = ++sequenceRef.current;
    setError('');
    setNotice('');
    setModal(null);
    startBusy('Finding the outline…');
    try {
      const sheet = isSample ? NO_SHEET : sheetChoice;
      const result = await requestTrace(file, 'standard', -1, false, sheet, null, snap, true);
      if (sequence !== sequenceRef.current) return;
      const projectName = isSample
        ? 'Mounting plate'
        : cleanName(file.name.replace(/\.[^.]+$/, '').slice(0, 100));
      const rev = invalidate();
      setTrace(result);
      setSourceFile(file);
      setReferenceCalibration(null);
      setMeasuredHeight('');
      setHeightAllowance('');
      setHeightBound('');
      setMeasurementReset((previous) => previous + 1);
      setModel(null);
      setSample(isSample);
      setName(projectName);
      setDetail('standard');
      setThreshold(-1);
      setInverted(false);
      setDesign({ ...DEFAULT_DESIGN });
      setUnit('mm');
      setWidth(isSample ? '80.00' : '');
      setThickness(isSample ? '4.00' : '');
      setWidthMm(isSample ? 80 : 0);
      setThicknessMm(isSample ? 4 : 0);
      setOutline(true);
      if (isSample) {
        setBusy('Building the CAD solid…');
        const built = await requestModel(result.profile, 80, 4, projectName, rev, DEFAULT_DESIGN);
        if (sequence === sequenceRef.current && String(revisionRef.current) === rev)
          installModel(built);
        else releaseModel(built.id);
      } else if (result.profile.reference) {
        const fromSheet = sheetWidthMm(result.profile)!;
        setWidth(fromSheet.toFixed(4));
        setWidthMm(fromSheet);
        setNotice(
          sheetCalibrationNotice(result) ||
            `Outline traced on the ${sheetLabel(result.profile.reference.kind)}; the width comes from the sheet. Enter the measured thickness, then build.`,
        );
        window.setTimeout(() => document.getElementById('thickness')?.focus(), 0);
      } else {
        setNotice('Outline ready. Enter the full measured width and thickness of your part.');
        window.setTimeout(() => widthInput.current?.focus(), 0);
      }
    } catch (err) {
      const message = errorText(err);
      if (sequence === sequenceRef.current)
        setError(
          !isSample && sheetChoice.kind === 'none' && message.includes('touches the image edge')
            ? `${message} If the part lies on a sheet of paper, choose that sheet under Scale reference and load the photo again.`
            : message,
          { kind: 'photo', file, isSample },
        );
    } finally {
      if (sequence === sequenceRef.current) setBusy(null);
    }
  }

  async function loadSample() {
    startBusy('Loading sample…');
    setError('');
    // Leaving the workbench while the sample downloads must not start a trace and build whose
    // model nobody would own or release.
    const sequence = ++sequenceRef.current;
    try {
      const response = await fetch('/sample.png');
      if (!response.ok)
        throw new Error(
          'The sample image could not be loaded. Upload your own photo to get started.',
        );
      const blob = await response.blob();
      if (sequence !== sequenceRef.current) return;
      await loadPhoto(new File([blob], 'mounting-plate.png', { type: 'image/png' }), true);
    } catch (err) {
      if (sequence !== sequenceRef.current) return;
      setError(errorText(err), { kind: 'sample' });
      setBusy(null);
    }
  }

  useEffect(() => {
    // A photo sent from the photo library opens instead of the sample.
    const handed = takeHandoff('workbench');
    void (handed ? loadPhoto(handed) : loadSample());
    return () => {
      sequenceRef.current++;
    };
  }, []);
  useEffect(() => {
    if (!active) {
      setModal(null);
      return;
    }
    if (busy) return;
    const handed = takeHandoff('workbench');
    if (handed) void loadPhoto(handed);
  }, [active, busy]);
  useEffect(() => {
    // Release this tab's temporary model files when the page goes away, so reloads and closed
    // tabs do not fill the service's job limit. A page restored from the back/forward cache has
    // lost those files, so it needs a rebuild before exporting.
    const release = () => {
      const owned = modelRef.current;
      if (!owned) return;
      modelRef.current = null;
      void fetch(`/api/models/${encodeURIComponent(owned.id)}`, {
        method: 'DELETE',
        keepalive: true,
      }).catch(() => {});
    };
    const restored = (event: PageTransitionEvent) => {
      if (event.persisted) invalidate();
    };
    window.addEventListener('pagehide', release);
    window.addEventListener('pageshow', restored);
    return () => {
      window.removeEventListener('pagehide', release);
      window.removeEventListener('pageshow', restored);
      // If the workbench is ever unmounted without the page going away, its model would
      // otherwise hold a temporary-storage slot until it expires.
      release();
    };
  }, []);
  useEffect(() => {
    if (editingName) nameInput.current?.focus();
  }, [editingName]);
  useEffect(() => {
    // Disabling a focused control during busy work drops focus to the page body. Return it once
    // the work and any dialog it opened are finished, unless the user has focused something else.
    if (busy || modal || !active) return;
    const target = pendingFocusRef.current;
    pendingFocusRef.current = null;
    const focused = document.activeElement;
    if (
      target?.isConnected &&
      !target.matches(':disabled') &&
      (!focused || focused === document.body)
    )
      target.focus();
  }, [busy, modal, active]);

  async function buildModel(openExport = false) {
    if (!trace || !buildReady || busy) return;
    const sequence = ++sequenceRef.current;
    let rev = String(revisionRef.current);
    let profile = trace.profile;
    let width = widthMm;
    let afterBuild = '';
    startBusy('Building the CAD solid…');
    setError('');
    setNotice('');
    try {
      const reference = trace.profile.reference;
      if (reference && reference.thickness_mm !== thicknessMm) {
        if (sourceFile) {
          // The visible side walls depend on thickness: trace again for the entered value.
          setBusy('Correcting the outline for thickness…');
          const sheet: SheetChoice =
            reference.kind === 'custom'
              ? {
                  kind: 'custom',
                  width: String(reference.sheet_mm[0]),
                  height: String(reference.sheet_mm[1]),
                }
              : { kind: reference.kind, width: '', height: '' };
          const corrected = await requestTrace(
            sourceFile,
            detail,
            threshold,
            inverted,
            sheet,
            thicknessMm,
            snap,
          );
          if (sequence !== sequenceRef.current || String(revisionRef.current) !== rev) return;
          const usedSheetScale = Math.abs((sheetWidthMm(trace.profile) ?? NaN) - widthMm) < 1e-9;
          rev = invalidate();
          setTrace(corrected);
          profile = corrected.profile;
          if (usedSheetScale && applySheetWidth(corrected)) width = sheetWidthMm(profile)!;
          setBusy('Building the CAD solid…');
        } else
          afterBuild = reference.thickness_mm
            ? `This outline was corrected for a ${reference.thickness_mm} mm thickness. Upload the photo again to correct it for the entered thickness.`
            : 'This outline was not corrected for thickness. Upload the photo again to correct it for the entered thickness.';
      }
      const result = await requestModel(profile, width, thicknessMm, projectName(), rev);
      if (sequence === sequenceRef.current && String(revisionRef.current) === rev) {
        installModel(result);
        if (openExport && activeRef.current) {
          setExportError('');
          setModal('export');
        } else
          setNotice(
            afterBuild || 'Model updated. The preview and downloads now use these dimensions.',
          );
        if (openExport && afterBuild) setNotice(afterBuild);
      } else releaseModel(result.id);
    } catch (err) {
      if (sequence === sequenceRef.current) setError(errorText(err), { kind: 'build', openExport });
    } finally {
      if (sequence === sequenceRef.current) setBusy(null);
    }
  }

  async function retrace(
    newDetail: Detail,
    newThreshold = threshold,
    newInverted = inverted,
    newSheet = sheetChoice,
    newSnap = snap,
  ) {
    if (!sourceFile || busy) return false;
    const sheetIssue = sheetChoiceError(newSheet);
    if (sheetIssue) {
      setError(sheetIssue);
      return false;
    }
    const sequence = ++sequenceRef.current;
    startBusy('Finding the outline…');
    setError('');
    setModal(null);
    try {
      const result = await requestTrace(
        sourceFile,
        newDetail,
        newThreshold,
        newInverted,
        newSheet,
        validThickness ? thicknessMm : null,
        newSnap,
      );
      if (sequence !== sequenceRef.current) return false;
      // Only a new outline makes the model outdated; a failed trace leaves it current.
      invalidate();
      setTrace(result);
      setDetail(newDetail);
      setThreshold(newThreshold);
      setInverted(newInverted);
      setSheetChoice(newSheet);
      setSnap(newSnap);
      if (result.profile.reference) {
        applySheetWidth(result);
        setNotice(
          sheetCalibrationNotice(result) ||
            `Outline traced on the ${sheetLabel(result.profile.reference.kind)}. The width comes from the sheet; your own width measurement is now an independent check.`,
        );
      } else if (referenceCalibration) {
        const frame = referenceCalibration.image_size;
        if (frame.width === result.image.width && frame.height === result.image.height) {
          const nextWidth = referenceWidth(referenceCalibration, result.bounds.width);
          setWidthMm(nextWidth);
          setWidth((nextWidth / unitFactor).toFixed(unit === 'in' ? 6 : 4));
          setNotice(
            'Outline updated. The measured feature scale is retained; review the recalculated outside width, then build.',
          );
        } else {
          setReferenceCalibration(null);
          setNotice(
            'Outline updated with a different working-image size. Reapply the feature reference or verify the outside width before building.',
          );
        }
      } else setNotice('Outline updated. Build the model to apply this trace.');
      return true;
    } catch (err) {
      if (sequence === sequenceRef.current)
        setError(errorText(err), {
          kind: 'retrace',
          detail: newDetail,
          threshold: newThreshold,
          inverted: newInverted,
          sheet: newSheet,
          snap: newSnap,
        });
      return false;
    } finally {
      if (sequence === sequenceRef.current) setBusy(null);
    }
  }

  async function applyAssistantProposal(proposal: AssistantProposal) {
    if (busy) return false;
    const nextDesign = designFromProposal(design, proposal);
    const invalid = designError(nextDesign, sourceSize);
    if (invalid) {
      setError(`This suggestion could not be applied. ${invalid}`);
      return false;
    }
    const previous = {
      trace,
      detail,
      threshold,
      inverted,
      design,
      preview: current ? model : null,
      width,
      unit,
      widthMm,
      referenceCalibration,
    };
    const changesTrace =
      (proposal.detail !== undefined && proposal.detail !== detail) ||
      (proposal.threshold !== undefined && proposal.threshold !== threshold) ||
      (proposal.inverted !== undefined && proposal.inverted !== inverted);
    if (changesTrace) {
      if (!sourceFile) return false;
      const success = await retrace(
        proposal.detail ?? detail,
        proposal.threshold ?? threshold,
        proposal.inverted ?? inverted,
      );
      if (!success) {
        // If the trace failed with a retryable error, retry the whole suggestion, not the trace.
        setRetry((failed) => (failed ? { kind: 'proposal', proposal } : failed));
        return false;
      }
    } else invalidate();
    setDesign(nextDesign);
    setAssistantUndo(previous);
    setNotice('AI suggestion applied. Review your settings, then build when you are ready.');
    return true;
  }

  function undoAssistantProposal() {
    if (!assistantUndo || busy) return;
    const previous = assistantUndo;
    const ownedModel = modelRef.current;
    // Every other edit clears the undo, so if no build replaced the model since the suggestion
    // was applied, the restored settings are exactly the ones it was built from: keep it current.
    const unchanged = !!ownedModel && ownedModel.id === previous.preview?.id;
    if (!unchanged) {
      // A generated replacement may already have released the old export files.
      // Restore only the previous preview, and rebuild before allowing downloads.
      modelRef.current = null;
      if (ownedModel) releaseModel(ownedModel.id);
    }
    const rev = invalidate();
    setTrace(previous.trace);
    setDetail(previous.detail);
    setThreshold(previous.threshold);
    setInverted(previous.inverted);
    setDesign(previous.design);
    setWidth(
      previous.unit === unit || !previous.width.trim() || !Number.isFinite(previous.widthMm)
        ? previous.width
        : String(previous.widthMm / unitFactor),
    );
    setWidthMm(previous.widthMm);
    setReferenceCalibration(previous.referenceCalibration);
    if (unchanged) {
      const restored = { ...ownedModel, revision: rev };
      modelRef.current = restored;
      setModel(restored);
    } else setModel(previous.preview);
    setError('');
    setNotice(
      unchanged
        ? 'Previous outline and design settings restored. The model and its downloads match them again.'
        : previous.preview
          ? 'Previous preview, outline and design settings restored. Your previous source scale is restored. Rebuild to refresh exports.'
          : 'Previous outline and design settings restored. Your previous source scale is restored. Build to create a fresh preview and exports.',
    );
  }

  async function restoreProject(file: File) {
    if (file.size > MAX_PROJECT) {
      setError('This project is too large. Choose a project smaller than 10 MiB.');
      return;
    }
    setError('');
    setModal(null);
    startBusy('Opening project…');
    const sequence = ++sequenceRef.current;
    // Retrying cannot fix an invalid file, only a failed build of a valid one.
    let retryable = false;
    try {
      const recipe = parseRecipe(JSON.parse(await file.text()));
      // Saved names may predate, or bypass, the rule the service enforces.
      const restoredName = cleanName(recipe.name);
      const restoredDesign = recipe.version !== 1 ? recipe.design! : { ...DEFAULT_DESIGN };
      const bounds = getBounds(recipe.profile);
      if (bounds.width <= 0 || bounds.height <= 0)
        throw new Error('The project outline has no area.');
      const restoredError = designError(restoredDesign, {
        width: recipe.width_mm,
        height: (bounds.height / bounds.width) * recipe.width_mm,
        thickness: recipe.thickness_mm,
      });
      if (restoredError) throw new Error(`This project could not be opened. ${restoredError}`);
      // Validate and build before replacing the current project. A service failure or
      // invalid polygon must leave the user's editable work and exports available.
      const previousRevision = revisionRef.current;
      const rev = String(previousRevision + 1);
      setBusy('Building the CAD solid…');
      retryable = true;
      const built = await requestModel(
        recipe.profile,
        recipe.width_mm,
        recipe.thickness_mm,
        restoredName,
        rev,
        restoredDesign,
      );
      if (sequence !== sequenceRef.current || revisionRef.current !== previousRevision) {
        releaseModel(built.id);
        return;
      }
      invalidate();
      setName(restoredName);
      setWidth(recipe.width_mm.toFixed(4));
      setThickness(recipe.thickness_mm.toFixed(4));
      setUnit('mm');
      setWidthMm(recipe.width_mm);
      setThicknessMm(recipe.thickness_mm);
      setSourceFile(null);
      setReferenceCalibration(recipe.reference_calibration ?? null);
      setMeasuredHeight(
        recipe.measured_height_mm === undefined ? '' : String(recipe.measured_height_mm),
      );
      setHeightAllowance(recipe.height_check ? String(recipe.height_check.allowance_mm) : '');
      setHeightBound(recipe.height_check ? String(recipe.height_check.measurement_bound_mm) : '');
      setMeasurementReset((previous) => previous + 1);
      setSample(false);
      setModel(null);
      setDetail('standard');
      setThreshold(-1);
      setInverted(false);
      setDesign(restoredDesign);
      setTrace({
        profile: recipe.profile,
        bounds,
        image: {
          width:
            recipe.reference_calibration?.image_size.width ?? Math.ceil(bounds.x + bounds.width),
          height:
            recipe.reference_calibration?.image_size.height ?? Math.ceil(bounds.y + bounds.height),
          data_url: '',
        },
        threshold: 0,
        warnings: [
          'Restored project: the source photo was not included. Upload a photo to trace again.',
        ],
      });
      installModel(built);
      setNotice('Project restored and rebuilt.');
    } catch (err) {
      if (sequence === sequenceRef.current)
        setError(errorText(err), retryable ? { kind: 'restore', file } : null);
    } finally {
      if (sequence === sequenceRef.current) setBusy(null);
    }
  }

  function chooseFile(file?: File) {
    if (!file || busy) return;
    if (file.name.toLowerCase().endsWith('.json')) {
      void restoreProject(file);
      return;
    }
    if (!PHOTO_TYPES.includes(file.type) && !PHOTO_NAME.test(file.name)) {
      setError('Choose a PNG, JPEG, WebP, HEIC or AVIF image, or a saved project JSON file.');
      return;
    }
    void loadPhoto(file);
  }
  function onFile(event: ChangeEvent<HTMLInputElement>) {
    chooseFile(event.target.files?.[0]);
    event.target.value = '';
  }
  function drop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files?.[0]);
  }
  function leaveDrag(event: DragEvent) {
    // Moving onto a child (the canvas, the drop overlay) also fires dragleave; only leaving
    // the drop target itself ends the drag, so the overlay does not flicker on and off.
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false);
  }
  function changeUnit(next: Unit) {
    if (next === unit) return;
    const factor = next === 'in' ? 25.4 : 1;
    // Convert every entered number, valid or not, so the field keeps showing the stored length.
    if (width.trim() !== '' && Number.isFinite(widthMm))
      setWidth((widthMm / factor).toFixed(next === 'in' ? 6 : 4));
    if (thickness.trim() !== '' && Number.isFinite(thicknessMm))
      setThickness((thicknessMm / factor).toFixed(next === 'in' ? 6 : 4));
    if (measuredHeight.trim() !== '' && Number.isFinite(Number(measuredHeight)))
      setMeasuredHeight(String((Number(measuredHeight) * unitFactor) / factor));
    const convert = (value: string) =>
      value.trim() && Number.isFinite(Number(value))
        ? String((Number(value) * unitFactor) / factor)
        : value;
    setHeightAllowance(convert);
    setHeightBound(convert);
    setUnit(next);
  }
  function openTrace() {
    setDraftThreshold(threshold === -1 ? (trace?.threshold ?? 150) : threshold);
    setDraftAuto(threshold === -1);
    setDraftInverted(inverted);
    setDraftSheet(sheetChoice);
    setDraftSnap(snap);
    setModal('trace');
  }
  function saveProject() {
    if (!trace || !buildReady) return;
    const heightIssue = measuredHeightError(measuredHeight, unitFactor);
    if (heightIssue) {
      setModal(null);
      setMeasurementReview((value) => ({ request: value.request + 1, target: 'height' }));
      setError(heightIssue);
      return;
    }
    const check = heightCheckDraft(heightAllowance, heightBound, unitFactor);
    if (check.error || (check.value && !measuredHeight.trim())) {
      setModal(null);
      setMeasurementReview((value) => ({
        request: value.request + 1,
        target: check.error ? 'decision' : 'height',
      }));
      setError(
        check.error ?? 'Enter an independent height measurement, or clear both decision inputs.',
      );
      return;
    }
    downloadJson({
      format: 'pictures-to-cad',
      version: trace.profile.primitives || trace.profile.reference ? 3 : 2,
      name: projectName(),
      profile: trace.profile,
      width_mm: widthMm,
      thickness_mm: thicknessMm,
      design,
      ...(referenceCalibration ? { reference_calibration: referenceCalibration } : {}),
      ...(measuredHeight.trim() ? { measured_height_mm: Number(measuredHeight) * unitFactor } : {}),
      ...(check.value ? { height_check: check.value } : {}),
    });
    setNotice(
      'Project download started. Your outline, measurements and design settings are included; the photo is not.',
    );
  }
  async function exportFile(kind: ExportKind) {
    if (!model || !current || downloading) return;
    const exportedModel = model;
    const downloadUrl = model.downloads[kind];
    if (!downloadUrl) return;
    const exportsGeneration = temporaryExportGeneration();
    const exportsStillExist = () => exportsGeneration === temporaryExportGeneration();
    setDownloading(kind);
    setExportError('');
    try {
      const response = await fetch(downloadUrl, { signal: AbortSignal.timeout(30000) });
      if (!exportsStillExist()) return;
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        if (!exportsStillExist()) return;
        if (response.status === 404 || response.status === 410) {
          invalidate();
          setModal(null);
          throw new Error(
            'These temporary files have expired or were cleared. Update the model to generate fresh downloads.',
          );
        }
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'The file could not be downloaded. Try again.',
        );
      }
      const blob = await response.blob();
      if (!exportsStillExist()) return;
      if (
        modelRef.current?.id !== exportedModel.id ||
        String(revisionRef.current) !== exportedModel.revision
      )
        throw new Error(
          'The model changed during download. Update the model, then download it again.',
        );
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${projectName()
        .replace(/[^a-zA-Z0-9_-]+/g, '-')
        .slice(
          0,
          60,
        )}.${kind === 'parts' ? 'parts.zip' : kind === 'bambu' ? 'bambu-studio.zip' : kind === 'prusa' ? 'prusaslicer.zip' : kind === 'qidi' ? 'qidi-studio.zip' : kind === 'orca' ? 'orca-slicer.zip' : kind === 'cura' ? 'cura.zip' : kind}`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      const label =
        kind === 'bambu'
          ? 'Bambu Studio handoff ZIP'
          : kind === 'prusa'
            ? 'PrusaSlicer handoff ZIP'
            : kind === 'qidi'
              ? 'QIDI Studio handoff ZIP'
              : kind === 'orca'
                ? 'OrcaSlicer handoff ZIP'
                : kind === 'cura'
                  ? 'UltiMaker Cura handoff ZIP'
                  : kind.toUpperCase();
      setNotice(
        kind === 'pdf'
          ? 'PDF download started. Print it at 100 % (actual size) and check its two 100 mm rulers.'
          : `${label} download started. Exported geometry uses millimeters.`,
      );
    } catch (err) {
      if (!exportsStillExist()) return;
      const message =
        err instanceof DOMException && (err.name === 'TimeoutError' || err.name === 'AbortError')
          ? 'The download took too long. Your model is still here; try again.'
          : errorText(err);
      setExportError(message);
      setError(message, { kind: 'build', openExport: true });
    } finally {
      if (exportsStillExist()) setDownloading(null);
    }
  }
  async function launchSlicer(id: SlicerId): Promise<SlicerLaunch> {
    if (!model || !current || downloading)
      throw new Error('Update the model before opening it in your slicer.');
    const exportsGeneration = temporaryExportGeneration();
    let response: Response;
    try {
      response = await fetch(`/api/models/${encodeURIComponent(model.id)}/slicer/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
        signal: AbortSignal.timeout(30000),
      });
    } catch (error) {
      if (
        error instanceof DOMException &&
        (error.name === 'TimeoutError' || error.name === 'AbortError')
      )
        throw new Error(
          'The launch request timed out. Check the application before trying again, or download the handoff ZIP.',
        );
      throw new Error('Could not reach the CAD service. Check the connection and try again.');
    }
    const result = await response.json().catch(() => ({}));
    if (exportsGeneration !== temporaryExportGeneration())
      throw new Error(
        'Temporary exports were cleared. Update the model to create a fresh handoff.',
      );
    if (!response.ok) {
      if (response.status === 404 || response.status === 410) {
        invalidate();
        setModal(null);
        setError(
          'These temporary files have expired or were cleared. Update the model to create a fresh handoff.',
          { kind: 'build', openExport: true },
        );
      }
      throw new Error(
        typeof result.detail === 'string'
          ? result.detail
          : 'Could not open your slicer. Download the handoff ZIP instead.',
      );
    }
    return result as SlicerLaunch;
  }
  async function clearTemporaryExports() {
    if (busy) return;
    startBusy('Clearing temporary exports…');
    setError('');
    try {
      await api<{ deleted: number }>('/api/models', { method: 'DELETE' });
      publishTemporaryExportsCleared();
      setDownloading(null);
      setExportError('');
      invalidate();
      modelRef.current = null;
      setModel(null);
      setModal(null);
      setNotice(
        'Temporary exports cleared. Your outline and dimensions are still here; build the model to export again.',
      );
    } catch (err) {
      setModal(null);
      setError(errorText(err), { kind: 'clear' });
    } finally {
      setBusy(null);
    }
  }
  const handlePrimary = () => {
    setExportError('');
    if (current) setModal('export');
    else void buildModel(true);
  };
  function followNextStep() {
    switch (nextStep.action) {
      case 'photo':
        setModal('photo');
        break;
      case 'width':
        widthInput.current?.focus();
        break;
      case 'thickness':
        thicknessInput.current?.focus();
        break;
      case 'design':
        setDesignReview((value) => value + 1);
        break;
      case 'build':
        void buildModel(false);
        break;
      case 'export':
        handlePrimary();
        break;
    }
  }
  const warningMessages = [
    ...(trace?.warnings ?? []),
    ...(current
      ? (model?.warnings ?? []).filter(
          (warning) =>
            warning !==
            'STL coordinates are in millimeters. Set millimeters explicitly when importing the mesh.',
        )
      : []),
  ];

  return (
    <div className="app-shell">
      <AppHeader
        studio="workbench"
        commands={[
          {
            id: 'load-photo',
            label: 'Open a photo or project',
            detail: 'Start from a picture or restore a saved project',
            keywords: 'upload import image',
            disabled: !!busy,
            run: () => fileInput.current?.click(),
          },
          {
            id: 'save-project',
            label: 'Save project',
            detail: 'Download your outline, measurements and settings',
            disabled: !trace || !buildReady || !!busy,
            run: saveProject,
          },
          {
            id: 'update-preview',
            label: 'Build or update preview',
            detail: 'Apply the current dimensions and design to your solid',
            disabled: !trace || !buildReady || !!busy,
            run: () => void buildModel(false),
          },
          {
            id: 'prepare-slicing',
            label: 'Prepare for slicing',
            detail: 'Review the print bed, process plan and slicer handoff',
            run: () => setPrepareOpen(true),
          },
          {
            id: 'edit-model',
            label: 'Edit model',
            detail: 'Return to size, proportions and edit history',
            run: () => setPrepareOpen(false),
          },
          {
            id: 'capture-guide',
            label: 'Capture guide',
            detail: 'Photograph a clear outline with a measured reference',
            run: () => setModal('guide'),
          },
        ]}
        projectName={
          <>
            <input
              ref={nameInput}
              aria-label="Project name"
              value={name}
              maxLength={100}
              readOnly={!editingName}
              disabled={!!busy}
              onChange={(e) => {
                setName(e.target.value);
                invalidate();
              }}
              onBlur={() => {
                setEditingName(false);
                setName(projectName());
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setEditingName(false);
                  nameInput.current?.blur();
                }
              }}
              style={{ width: `${Math.min(Math.max(name.length, 10), 22)}ch` }}
            />
            <button
              className="icon-button"
              aria-label="Rename project"
              disabled={!!busy}
              onClick={() => setEditingName(true)}
            >
              <PencilSimple size={21} />
            </button>
          </>
        }
        actions={
          <>
            <button
              className="text-button guide-button"
              aria-label="Capture guide"
              onClick={() => setModal('guide')}
            >
              <Question size={25} />
              <span className="label-long">Capture guide</span>
              <span className="label-short">Guide</span>
            </button>
            <button
              className="outlined-button save-button"
              aria-label="Save project"
              onClick={saveProject}
              disabled={!trace || !buildReady || !!busy}
            >
              <FloppyDisk size={24} />
              <span className="label-long">Save project</span>
              <span className="label-short">Save</span>
            </button>
          </>
        }
      />

      <main id="workbench">
        <div className="workspace-heading">
          <div>
            <span className="workspace-eyebrow">01 / CREATE</span>
            <h2>Flat part studio</h2>
            <p>A clear outline. A measured solid.</p>
          </div>
          <nav className="workflow" aria-label="Conversion workflow">
            <button
              className={`workflow-step ${activeStage === 'photo' ? 'active' : ''}`}
              aria-current={activeStage === 'photo' ? 'step' : undefined}
              onClick={() => setModal('photo')}
              disabled={!!busy}
            >
              <span className="step-icon">
                <Camera size={26} />
              </span>
              <span>Photo</span>
            </button>
            <span className="step-line" />
            <button
              className={`workflow-step ${activeStage === 'trace' ? 'active' : ''}`}
              aria-current={activeStage === 'trace' ? 'step' : undefined}
              onClick={openTrace}
              disabled={!sourceFile || !!busy}
            >
              <span className="step-icon">
                <PencilSimple size={26} />
              </span>
              <span>Trace</span>
            </button>
            <span className="step-line" />
            <button
              className={`workflow-step ${activeStage === 'scale' ? 'active' : ''}`}
              aria-current={activeStage === 'scale' ? 'step' : undefined}
              onClick={() => widthInput.current?.focus()}
              disabled={!trace || !!busy}
            >
              <span className="step-icon">
                <Ruler size={28} />
              </span>
              <span>Scale</span>
            </button>
            <span className="step-line" />
            <button
              className={`workflow-step ${activeStage === 'export' ? 'active' : ''}`}
              aria-current={activeStage === 'export' ? 'step' : undefined}
              onClick={handlePrimary}
              disabled={!trace || !buildReady || !!busy}
            >
              <span className="step-icon">
                <DownloadSimple size={27} />
              </span>
              <span>Export</span>
            </button>
          </nav>
        </div>

        {error && (
          <div className="message error-message" role="alert">
            <WarningCircle size={23} />
            <div>
              <strong>We couldn’t complete that step.</strong>
              <span>{error}</span>
            </div>
            {retry && (
              <button className="text-button" disabled={!!busy} onClick={retryFailed}>
                Try again
              </button>
            )}
            <button className="icon-button" aria-label="Dismiss error" onClick={() => setError('')}>
              <X size={19} />
            </button>
          </div>
        )}
        <div className="sr-only" role="status" aria-live="polite">
          {busy || notice || (current ? 'CAD model ready.' : '')}
        </div>

        <section className="workflow-guide" aria-label="Next step">
          <div className="workflow-guide-icon" aria-hidden="true">
            {busy ? (
              <SpinnerGap size={25} className="spinner" />
            ) : nextStep.action === 'export' ? (
              <CheckCircle size={25} />
            ) : nextStep.action === 'design' ? (
              <WarningCircle size={25} />
            ) : (
              <Ruler size={25} />
            )}
          </div>
          <div className="workflow-guide-copy" aria-live="polite">
            <span className="workflow-guide-label">
              {sample ? 'Sample project · demonstration measurements' : 'Your next step'}
            </span>
            <h2>{nextStep.title}</h2>
            <p>{nextStep.detail}</p>
          </div>
          <button
            className="outlined-button"
            onClick={followNextStep}
            disabled={!!busy || !nextStep.action}
          >
            {busy ? 'Please wait…' : nextStep.actionLabel}
            <ArrowSquareOut size={18} aria-hidden="true" />
          </button>
        </section>

        <div className="workbench-tools" role="group" aria-label="Workbench tools">
          <button
            className="outlined-button"
            aria-pressed={!prepareOpen}
            onClick={() => setPrepareOpen(false)}
          >
            Edit model
          </button>
          <button
            className="outlined-button"
            aria-pressed={prepareOpen}
            onClick={() => setPrepareOpen(true)}
          >
            Prepare for slicing
          </button>
        </div>
        <section className="viewports" aria-label="Photo and CAD workbench">
          <section className="viewport-panel source-panel">
            <div className="panel-toolbar">
              <h1>
                <ImageIcon size={25} />
                Source &amp; outline
              </h1>
              <div className="panel-actions">
                <button
                  className="icon-button"
                  title={outline ? 'Hide outline' : 'Show outline'}
                  aria-label={outline ? 'Hide outline' : 'Show outline'}
                  aria-pressed={outline}
                  // Without a photo the outline is all there is to show, so it cannot be hidden.
                  disabled={!trace?.image.data_url}
                  onClick={() => setOutline(!outline)}
                >
                  {outline ? <Eye size={22} /> : <EyeSlash size={22} />}
                </button>
                <button
                  className="text-button accent"
                  onClick={openTrace}
                  disabled={!sourceFile || !!busy}
                >
                  <PencilSimple size={22} />
                  <span>Adjust outline</span>
                </button>
              </div>
            </div>
            <div
              className="canvas-stage"
              onDragOver={(e) => {
                e.preventDefault();
                if (!busy) setDragging(true);
              }}
              onDragLeave={leaveDrag}
              onDrop={drop}
            >
              {trace ? (
                <SourceCanvas
                  trace={trace}
                  showOutline={outline}
                  widthLabel={widthLabel}
                  imageUrl={
                    backgroundPreview?.trace === trace ? backgroundPreview?.dataUrl : undefined
                  }
                />
              ) : (
                <div className="empty-state">
                  <Camera size={44} weight="light" />
                  <h2>Start with a photo.</h2>
                  <p>A clear, front-on photo of one flat part is all you need to begin.</p>
                  <button
                    className="primary-button"
                    onClick={() => setModal('photo')}
                    disabled={!!busy}
                  >
                    Choose a photo
                  </button>
                </div>
              )}
              {trace && (
                <div className="source-caption">
                  <span>
                    {sample
                      ? 'Sample · mounting plate'
                      : sourceFile
                        ? sourceFile.name
                        : 'Restored project · outline only'}
                  </span>
                  <button onClick={() => setModal('photo')} disabled={!!busy}>
                    Change photo
                  </button>
                </div>
              )}
              {dragging && (
                <div className="drop-overlay">
                  <UploadSimple size={42} />
                  <strong>Drop your photo here</strong>
                </div>
              )}
            </div>
            <BackgroundRemoval
              trace={trace}
              name={name}
              disabled={!!busy}
              onPreviewChange={setBackgroundPreview}
            />
          </section>
          <section className="viewport-panel model-panel" aria-label="CAD preview">
            <div className="panel-toolbar">
              <h2>
                <Cube size={29} weight="light" />
                CAD preview
              </h2>
              <button
                className="text-button"
                onClick={() => setResetKey((v) => v + 1)}
                disabled={!model}
              >
                <ArrowCounterClockwise size={23} />
                Reset view
              </button>
            </div>
            <div className="canvas-stage model-stage">
              <ModelViewer
                mesh={model?.mesh ?? null}
                parts={model?.parts}
                resetKey={resetKey}
                loading={!!busy}
                emptyMessage={false}
                color={design.color}
                material={design.material}
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
                  <span>Previous model · update to apply your changes</span>
                </div>
              )}
              {!model && !busy && (
                <div className="model-empty">
                  <Cube size={45} weight="light" />
                  <h3>Your solid starts here.</h3>
                  <p>
                    {trace
                      ? 'Set the measured width and thickness, then build your model.'
                      : 'Load a photo to trace its outline.'}
                  </p>
                </div>
              )}
            </div>
          </section>
        </section>

        {prepareOpen ? (
          <PrintPreparation
            design={design}
            model={model}
            current={current}
            busy={!!busy}
            canBuild={!!trace && buildReady}
            onChange={changeDesign}
            onBuild={() => void buildModel(false)}
            onExport={handlePrimary}
            onAdvanced={() => setDesignReview((value) => value + 1)}
          />
        ) : (
          <QuickEdit
            design={design}
            onChange={changeDesign}
            sourceSize={sourceSize}
            disabled={!!busy}
            canUndo={designHistory.past.length > 0}
            canRedo={designHistory.future.length > 0}
            onUndo={() => travelDesign('undo')}
            onRedo={() => travelDesign('redo')}
            onAdvanced={() => setDesignReview((value) => value + 1)}
          />
        )}

        <section className="controls-section" aria-label="Model dimensions">
          <div className="controls-grid">
            <div className="control-group">
              <ArrowsHorizontal size={29} />
              <div className="field-stack">
                <div className="label-row">
                  <label htmlFor="reference-width">Reference width</label>
                  <div className="unit-toggle" role="group" aria-label="Measurement units">
                    <button
                      aria-pressed={unit === 'mm'}
                      disabled={!!busy}
                      onClick={() => changeUnit('mm')}
                    >
                      mm
                    </button>
                    <button
                      aria-pressed={unit === 'in'}
                      disabled={!!busy}
                      onClick={() => changeUnit('in')}
                    >
                      in
                    </button>
                  </div>
                </div>
                <div className={`number-field ${width && !validWidth ? 'invalid' : ''}`}>
                  <input
                    ref={widthInput}
                    id="reference-width"
                    type="number"
                    inputMode="decimal"
                    value={width}
                    min={0.1 / unitFactor}
                    max={2000 / unitFactor}
                    step="any"
                    placeholder="Set width"
                    disabled={!trace || !!busy}
                    aria-describedby="width-help"
                    aria-invalid={width !== '' && !validWidth}
                    onChange={(e) => {
                      setWidth(e.target.value);
                      setReferenceCalibration(null);
                      setWidthMm(Number(e.target.value) * unitFactor);
                      invalidate();
                      setError('');
                    }}
                  />
                  <span>{unit}</span>
                </div>
                <span id="width-help" className="field-hint">
                  {referenceCalibration
                    ? 'Outside width from your applied feature reference'
                    : trace?.profile.reference &&
                        Math.abs((sheetWidthMm(trace.profile) ?? NaN) - widthMm) < 1e-9
                      ? `From the ${sheetLabel(trace.profile.reference.kind)}; check it against the part`
                      : 'Full outside width, measured by you'}
                </span>
              </div>
            </div>
            <div className="control-group">
              <Stack size={30} />
              <div className="field-stack">
                <label htmlFor="thickness">Thickness</label>
                <div className={`number-field ${thickness && !validThickness ? 'invalid' : ''}`}>
                  <input
                    ref={thicknessInput}
                    id="thickness"
                    type="number"
                    inputMode="decimal"
                    value={thickness}
                    min={0.1 / unitFactor}
                    max={500 / unitFactor}
                    step="any"
                    placeholder="Set depth"
                    disabled={!trace || !!busy}
                    aria-describedby="thickness-help"
                    aria-invalid={thickness !== '' && !validThickness}
                    onChange={(e) => {
                      setThickness(e.target.value);
                      setThicknessMm(Number(e.target.value) * unitFactor);
                      invalidate();
                      setError('');
                    }}
                  />
                  <span>{unit}</span>
                </div>
                <span id="thickness-help" className="field-hint">
                  Measure separately from the photo
                </span>
              </div>
            </div>
            <div className="control-group detail-control">
              <Polygon size={29} />
              <div className="field-stack">
                <label htmlFor="outline-detail">Outline detail</label>
                <select
                  id="outline-detail"
                  value={detail}
                  disabled={!sourceFile || !!busy}
                  onChange={(e) => void retrace(e.target.value as Detail)}
                >
                  <option value="coarse">Simplified</option>
                  <option value="standard">Standard</option>
                  <option value="fine">Fine</option>
                </select>
                <span className="field-hint">
                  {trace
                    ? `${trace.profile.holes.length} through holes detected${
                        trace.profile.primitives
                          ? ` · fitted ${fitCounts(trace.profile)!.circle} circles, ${fitCounts(trace.profile)!.arc} arcs`
                          : ''
                      }`
                    : 'Review the outline before building'}
                </span>
              </div>
            </div>
            <div className="primary-action">
              <button
                className="primary-button export-button"
                onClick={handlePrimary}
                disabled={!trace || !buildReady || !!busy}
              >
                {busy ? <SpinnerGap size={25} className="spinner" /> : <ArrowSquareOut size={27} />}
                <span>
                  {busy
                    ? 'Processing…'
                    : current
                      ? 'Review export'
                      : model
                        ? 'Update model'
                        : 'Build model'}
                </span>
              </button>
            </div>
          </div>
          {trace && (
            <div ref={measurementTools}>
              <ReferenceCalibration
                key={measurementReset}
                trace={trace}
                calibration={referenceCalibration}
                unit={unit}
                widthMm={validWidth ? widthMm : null}
                height={measuredHeight}
                heightAllowance={heightAllowance}
                heightBound={heightBound}
                disabled={!!busy}
                onApply={(value, calculatedWidth) => {
                  invalidate();
                  setReferenceCalibration(value);
                  setWidthMm(calculatedWidth);
                  setWidth((calculatedWidth / unitFactor).toFixed(unit === 'in' ? 6 : 4));
                  setError('');
                  setNotice(
                    'Feature reference applied. Review the outside width and independent height check before building.',
                  );
                }}
                onHeight={(value) => {
                  setMeasuredHeight(value);
                  setError('');
                }}
                onHeightAllowance={(value) => {
                  setHeightAllowance(value);
                  setError('');
                }}
                onHeightBound={(value) => {
                  setHeightBound(value);
                  setError('');
                }}
              />
            </div>
          )}
          <p className="measurement-note">
            <Info size={21} />
            <span>
              {trace?.profile.reference
                ? 'Scale comes from the sheet size you chose; thickness is supplied by you. Check dimensions before manufacturing.'
                : 'Scale and thickness are supplied by you. Check dimensions before manufacturing.'}
            </span>
          </p>
          {!dimensionsValid && trace && !busy && (
            <p className="validation-message" role="status">
              {!validWidth
                ? 'Enter the full measured width (0.1–2000 mm).'
                : 'Enter the measured thickness (0.1–500 mm).'}
            </p>
          )}
          {notice && !busy && (
            <p className="notice">
              <CheckCircle size={18} />
              {notice}
            </p>
          )}
          {!!warningMessages.length && (
            <details className="warnings">
              <summary>
                <WarningCircle size={18} />
                {warningMessages.length} {warningMessages.length === 1 ? 'note' : 'notes'} to review
              </summary>
              <ul>
                {warningMessages.map((warning, i) => (
                  <li key={`${i}-${warning}`}>{warning}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
        <PrintSettings
          design={design}
          onChange={changeDesign}
          onEditEnd={() => {
            historyEditKey.current = undefined;
          }}
          busy={!!busy}
          sourceSize={sourceSize}
          model={model}
          current={current}
          revealRequest={designReview}
        />
        <LocalAssistant
          context={{
            threshold,
            inverted,
            detail,
            width_mm: validWidth ? widthMm : null,
            thickness_mm: validThickness ? thicknessMm : null,
            hole_count: trace?.profile.holes.length ?? null,
            has_image: !!sourceFile,
            has_model: current,
            warnings: warningMessages.slice(0, 8).map((warning) => warning.slice(0, 300)),
            design,
            ...(current && model
              ? {
                  geometry: {
                    width_mm: model.dimensions.width,
                    height_mm: model.dimensions.height,
                    thickness_mm: model.dimensions.thickness,
                    parts: (model.parts ?? []).slice(0, 8).map((part) => ({
                      width_mm: part.dimensions.width,
                      height_mm: part.dimensions.height,
                      thickness_mm: part.dimensions.thickness,
                    })),
                  },
                }
              : {}),
          }}
          revision={JSON.stringify({ revision, design, model: current ? model?.id : null })}
          busy={!!busy}
          settingsIssue={designError(design)}
          canUndo={!!assistantUndo}
          onApply={applyAssistantProposal}
          onUndo={undoAssistantProposal}
        />
      </main>

      <footer className="statusbar">
        <div className="workflow-description">
          <Cube size={27} weight="light" />
          <strong>Single-photo profile extrusion</strong>
        </div>
        <div className="dimensions-summary">
          {model ? (
            <>
              <span>{current ? 'Scaled dimensions:' : 'Previous dimensions:'}</span>
              <code>
                {displayNumber(model.dimensions.width)} {unit} (W) ×{' '}
                {displayNumber(model.dimensions.height)} {unit} (H) ×{' '}
                {displayNumber(model.dimensions.thickness)} {unit} (T)
              </code>
            </>
          ) : (
            <span>Set dimensions to create a CAD solid</span>
          )}
        </div>
        <span className="local-status">
          <span className="status-dot" />
          {nextStep.footer}
        </span>
      </footer>
      <input
        ref={fileInput}
        className="sr-only"
        type="file"
        accept="image/png,image/jpeg,image/webp,image/heic,image/heif,image/avif,.heic,.heif,.avif,application/json,.json"
        aria-label="Choose photo or project"
        onChange={onFile}
      />

      {active && modal === 'photo' && (
        <Modal
          title="Start from a photo."
          eyebrow="PHOTO TO PROFILE"
          onClose={() => setModal(null)}
          onFocusLost={rememberFocus}
        >
          <p className="modal-intro">
            One flat part, a contrasting background, and a straight-on view. We’ll trace the
            outline; you supply the real dimensions.
          </p>
          {/* A refused file (wrong type, too large, unset custom sheet) keeps this dialog open,
              and the page's own alert is hidden behind it. */}
          {error && (
            <p className="export-error" role="alert">
              {error}
            </p>
          )}
          <div
            className={`upload-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={leaveDrag}
            onDrop={drop}
          >
            <UploadSimple size={40} weight="light" />
            <strong>Drop a photo or saved project</strong>
            <p>PNG, JPEG, WebP, HEIC, AVIF or project JSON · photos up to 32 MiB</p>
            <button className="primary-button" onClick={() => fileInput.current?.click()}>
              Browse files
            </button>
          </div>
          <SheetReference
            id="photo-sheet-reference"
            value={sheetChoice}
            onChange={setSheetChoice}
          />
          <div className="modal-split-actions">
            <button
              className="text-button accent"
              onClick={() => {
                setModal(null);
                void loadSample();
              }}
            >
              Try the sample part
            </button>
            <button className="text-button" onClick={() => setModal('guide')}>
              Read the capture guide
              <ArrowSquareOut size={18} />
            </button>
          </div>
          <p className="privacy-note">
            <Info size={18} />
            <span>
              Photos are uploaded to this running CAD service for processing, then discarded.
              Generated files expire after one hour. No external AI service is used.
            </span>
          </p>
        </Modal>
      )}

      {active && modal === 'trace' && (
        <Modal
          title="Make the outline match."
          eyebrow="REVIEW YOUR TRACE"
          onClose={() => setModal(null)}
          onFocusLost={rememberFocus}
        >
          <p className="modal-intro">
            The cyan line becomes the edge of your part. Check the outside boundary and every hole
            before building.
          </p>
          <div className="trace-settings">
            <SheetReference id="sheet-reference" value={draftSheet} onChange={setDraftSheet} />
            <div className="field-stack sheet-reference">
              {draftSheet.kind !== 'none' && (
                <label className="check-field">
                  <input
                    type="checkbox"
                    checked={draftSnap}
                    onChange={(e) => setDraftSnap(e.target.checked)}
                  />
                  <span>Recover design intent: square edges, equal radii, aligned axes</span>
                </label>
              )}
            </div>
            <label className="check-field">
              <input
                type="checkbox"
                checked={draftAuto}
                disabled={draftSheet.kind !== 'none'}
                onChange={(e) => setDraftAuto(e.target.checked)}
              />
              <span>Choose contrast automatically</span>
            </label>
            <div className="slider-label">
              <label htmlFor="threshold">Contrast threshold</label>
              <output htmlFor="threshold">{draftAuto ? 'Auto' : draftThreshold}</output>
            </div>
            <input
              id="threshold"
              type="range"
              min="1"
              max="254"
              value={draftThreshold}
              disabled={draftAuto || draftSheet.kind !== 'none'}
              onChange={(e) => setDraftThreshold(Number(e.target.value))}
            />
            <p className="field-explanation">
              {draftSheet.kind === 'none'
                ? 'For a dark part on a light background, raise the threshold to include more of the dark edge.'
                : 'With a reference sheet, contrast is measured locally along every edge, so the threshold is not used.'}
            </p>
            <label className="check-field">
              <input
                type="checkbox"
                checked={draftInverted}
                onChange={(e) => setDraftInverted(e.target.checked)}
              />
              <span>Light part on a dark background</span>
            </label>
          </div>
          {trace?.profile.reference && (
            <div className="inline-note fit-report">
              <Info size={19} />
              <div>
                <p>
                  Traced on the {sheetLabel(trace.profile.reference.kind)}: edge blur{' '}
                  {trace.profile.reference.edge_blur_mm.toFixed(2)} mm
                  {trace.profile.reference.lens_k1
                    ? `, lens distortion k₁ ${trace.profile.reference.lens_k1.toFixed(4)}`
                    : ''}
                  {trace.profile.reference.thickness_mm
                    ? `, corrected for ${trace.profile.reference.thickness_mm} mm thickness`
                    : ', not yet corrected for thickness'}
                  .
                </p>
                <ul>
                  {trace.profile.reference.notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
          <div className="inline-note">
            <Info size={19} />
            <p>
              Photographed markings can look like holes. Retake the photo if the trace includes an
              unwanted opening. Detail settings simplify the detected outline; they do not improve
              the accuracy of the photograph.
            </p>
          </div>
          <div className="modal-footer">
            <button className="outlined-button" onClick={() => setModal(null)}>
              Keep current outline
            </button>
            <button
              className="primary-button"
              disabled={!!sheetChoiceError(draftSheet)}
              onClick={() =>
                void retrace(
                  detail,
                  draftAuto ? -1 : draftThreshold,
                  draftInverted,
                  draftSheet,
                  draftSnap,
                )
              }
            >
              Apply trace
            </button>
          </div>
        </Modal>
      )}

      {active && modal === 'guide' && (
        <Modal
          title="A better photo. A better outline."
          eyebrow="CAPTURE GUIDE"
          onClose={() => setModal(null)}
          onFocusLost={rememberFocus}
        >
          <p className="modal-intro">
            Designed for flat parts with a constant thickness: plates, gaskets, spacers, and
            templates.
          </p>
          <ol className="guide-list">
            <li>
              <strong>Face the part straight on.</strong>
              <p>
                Keep the camera parallel to the part. Include the full outline with space around
                every edge. Perspective and lens distortion affect the result.
              </p>
            </li>
            <li>
              <strong>Make the edges easy to see.</strong>
              <p>
                Use a plain, contrasting background and even light. Avoid glare, deep shadows,
                patterned surfaces, and overlapping objects.
              </p>
            </li>
            <li>
              <strong>Set scale from a real measurement.</strong>
              <p>
                For the best result, lay the part on a sheet of known size (A4, US Letter or a
                measured custom sheet), photograph the whole sheet, and choose it under Adjust
                outline. Otherwise enter the full outside width, or open Use a known feature and
                mark two measured endpoints in the part's plane. Measure thickness separately.
              </p>
            </li>
            <li>
              <strong>Inspect, then verify.</strong>
              <p>
                Confirm every hole and edge in the trace. Check another physical dimension before
                manufacturing. A single photo does not recover hidden geometry, bevels, or variable
                thickness.
              </p>
            </li>
          </ol>
          <div className="inline-note">
            <Info size={21} />
            <p>
              STEP contains a CAD solid; STL is a triangle mesh in millimeters; DXF and SVG are 2D
              outlines; PDF is that outline to print at 1:1; SCAD is an editable polygon extrusion
              for OpenSCAD. Save the project JSON to keep your outline and parameters. STEP does not
              retain a parametric feature history.
            </p>
          </div>
          <p className="privacy-note">
            Processing runs on this CAD service. Photos are discarded after tracing. Generated files
            are temporary; download your work to keep it. A saved project contains the outline and
            dimensions, not the source photograph.
          </p>
          <div className="cleanup-section">
            <button
              className="text-button"
              onClick={() => void clearTemporaryExports()}
              disabled={!!busy}
            >
              Clear temporary exports
            </button>
            <p>
              Deletes temporary model exports. Downloaded copies and retained slicer handoff copies
              remain. Models in both Flat part and Relief will need to be rebuilt.
            </p>
          </div>
          <div className="modal-footer">
            <button className="primary-button" onClick={() => setModal(null)}>
              Back to the workbench
            </button>
          </div>
        </Modal>
      )}

      {active && modal === 'export' && current && model && (
        <Modal
          title="Your part, ready for the next tool."
          eyebrow="REVIEW & EXPORT"
          onClose={() => setModal(null)}
          onFocusLost={rememberFocus}
        >
          <p className="modal-intro">
            Review the dimensions, then choose your format. These files match the current preview.
          </p>
          {exportError && (
            <p className="export-error" role="alert">
              {exportError}
            </p>
          )}
          <div className="export-summary">
            <div>
              <span>Width × height × thickness</span>
              <strong>
                {displayNumber(model.dimensions.width)} × {displayNumber(model.dimensions.height)} ×{' '}
                {displayNumber(model.dimensions.thickness)} {unit}
              </strong>
            </div>
            <div>
              <span>Through holes</span>
              <strong>{model.hole_count}</strong>
            </div>
            {model.geometry?.kind === 'fitted' && (
              <div>
                <span>Exact edges</span>
                <strong className="exact-edges">
                  {model.geometry.circles} circles · {model.geometry.arcs} arcs ·{' '}
                  {model.geometry.lines} lines
                </strong>
              </div>
            )}
          </div>
          <SlicerHandoff
            model={model}
            selected={selectedSlicer}
            onSelect={setSelectedSlicer}
            downloading={downloading}
            onDownload={(id) => void exportFile(id)}
            onLaunch={launchSlicer}
          />
          <ExportFormats
            model={model}
            downloading={downloading}
            onDownload={(kind) => void exportFile(kind)}
          />
          <div className="inline-note">
            <Info size={20} />
            <p>
              All geometry exports use millimeters, including when the interface displays inches.
              Select millimeters when importing STL. Print the PDF at 100 % and measure its rulers.
              Verify the dimensions before cutting or printing.
            </p>
          </div>
          <div className="modal-footer">
            <button className="text-button" onClick={saveProject}>
              <FloppyDisk size={22} />
              Save editable project recipe
            </button>
            <button className="outlined-button" onClick={() => setModal(null)}>
              Back to model
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
