import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, ReactNode } from 'react';
import {
  ArrowCounterClockwise,
  ArrowSquareOut,
  ArrowsHorizontal,
  Camera,
  CheckCircle,
  Cube,
  DownloadSimple,
  Eye,
  EyeSlash,
  FloppyDisk,
  Image as ImageIcon,
  Info,
  PencilSimple,
  Polygon,
  Question,
  Ruler,
  SpinnerGap,
  Stack,
  UploadSimple,
  WarningCircle,
  X,
} from '@phosphor-icons/react';
import ModelViewer from './ModelViewer';
import LocalAssistant from './LocalAssistant';
import PrintSettings from './PrintSettings';
import ReferenceCalibration from './ReferenceCalibration';
import { calibrationError, measuredHeightError, referenceWidth } from './calibration';
import { DEFAULT_DESIGN, designError, designFromProposal, parseDesign } from './design';
import type {
  AssistantProposal,
  DesignSettings,
  Detail,
  ModelResult,
  Point,
  Profile,
  ProjectRecipe,
  ReferenceCalibration as Calibration,
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
  | { kind: 'retrace'; detail: Detail; threshold: number; inverted: boolean }
  | { kind: 'proposal'; proposal: AssistantProposal }
  | { kind: 'restore'; file: File }
  | { kind: 'clear' };
const MAX_FILE = 10 * 1024 * 1024;

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
    (recipe.version !== 1 && recipe.version !== 2) ||
    typeof recipe.name !== 'string' ||
    recipe.name.length > 100
  )
    throw new Error(
      'This is not a supported Pictures to CAD project. Choose a version 1 or 2 project JSON file.',
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
  if (recipe.version === 2) recipe.design = parseDesign(recipe.design);
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
}: {
  trace: TraceResult | null;
  showOutline: boolean;
  widthLabel: string;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!trace || !canvas.current || !container.current) return;
    const image = new window.Image();
    let disposed = false;
    const draw = () => {
      if (disposed || !canvas.current || !container.current) return;
      const el = canvas.current;
      const ctx = el.getContext('2d');
      if (!ctx) return;
      const width = container.current.clientWidth,
        height = container.current.clientHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      el.width = width * dpr;
      el.height = height * dpr;
      ctx.scale(dpr, dpr);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, width, height);
      const b = trace.bounds;
      const marginX = b.width * 0.09;
      const marginY = Math.max(b.height * 0.48, b.width * 0.17);
      const crop = {
        x: b.x - marginX,
        y: b.y - marginY,
        width: b.width + marginX * 2,
        height: b.height + marginY * 2,
      };
      const scale = Math.min(width / crop.width, height / crop.height);
      const ox = (width - crop.width * scale) / 2 - crop.x * scale;
      const oy = (height - crop.height * scale) / 2 - crop.y * scale;
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
      const y = Math.min(height - 26, bottom + 44);
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
        ctx.fillRect(width / 2 - textWidth / 2 - 13, y - 16, textWidth + 26, 32);
        ctx.strokeStyle = '#00b9e8';
        ctx.strokeRect(width / 2 - textWidth / 2 - 13, y - 16, textWidth + 26, 32);
        ctx.fillStyle = '#202a30';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(widthLabel, width / 2, y + 1);
      }
    };
    const observer = new ResizeObserver(draw);
    observer.observe(container.current);
    image.onload = draw;
    if (trace.image.data_url) image.src = trace.image.data_url;
    draw();
    return () => {
      disposed = true;
      observer.disconnect();
    };
  }, [trace, showOutline, widthLabel]);
  return (
    <div className="source-canvas" ref={container}>
      <canvas
        ref={canvas}
        role="img"
        aria-label={
          trace
            ? `Source outline with ${trace.profile.holes.length} through holes. Reference width ${widthLabel || 'not set'}.`
            : 'No source photo loaded'
        }
      />
    </div>
  );
}

export default function App() {
  const [name, setName] = useState('Mounting plate');
  const [editingName, setEditingName] = useState(false);
  const [trace, setTrace] = useState<TraceResult | null>(null);
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
  const [measurementReset, setMeasurementReset] = useState(0);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [exportError, setExportError] = useState('');
  const [detail, setDetail] = useState<Detail>('standard');
  const [threshold, setThreshold] = useState(-1);
  const [inverted, setInverted] = useState(false);
  const [design, setDesign] = useState<DesignSettings>({ ...DEFAULT_DESIGN });
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
  const buildReady = dimensionsValid && !designIssue;
  const current = !!model && model.revision === String(revision);
  const stale = !!model && !current;
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
    if (result.design) setDesign(result.design);
    if (previous && previous.id !== result.id) releaseModel(previous.id);
  }
  function projectName() {
    return cleanName(name);
  }
  function invalidate() {
    setAssistantUndo(null);
    const next = ++revisionRef.current;
    setRevision(next);
    setNotice('');
    return String(next);
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
        return void retrace(retry.detail, retry.threshold, retry.inverted);
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
  ) {
    const body = new FormData();
    body.append('file', file);
    body.append('detail', newDetail);
    body.append('threshold', String(newThreshold));
    body.append('inverted', String(newInverted));
    return api<TraceResult>('/api/trace', { method: 'POST', body });
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
    if (file.size > MAX_FILE) {
      setError('This file is too large. Choose an image or project smaller than 10 MiB.');
      return;
    }
    const sequence = ++sequenceRef.current;
    setError('');
    setNotice('');
    setModal(null);
    startBusy('Finding the outline…');
    try {
      const result = await requestTrace(file, 'standard', -1, false);
      if (sequence !== sequenceRef.current) return;
      const projectName = isSample
        ? 'Mounting plate'
        : cleanName(file.name.replace(/\.[^.]+$/, '').slice(0, 100));
      const rev = invalidate();
      setTrace(result);
      setSourceFile(file);
      setReferenceCalibration(null);
      setMeasuredHeight('');
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
      } else {
        setNotice('Outline ready. Enter the full measured width and thickness of your part.');
        window.setTimeout(() => widthInput.current?.focus(), 0);
      }
    } catch (err) {
      if (sequence === sequenceRef.current)
        setError(errorText(err), { kind: 'photo', file, isSample });
    } finally {
      if (sequence === sequenceRef.current) setBusy(null);
    }
  }

  async function loadSample() {
    startBusy('Loading sample…');
    setError('');
    try {
      const response = await fetch('/sample.png');
      if (!response.ok)
        throw new Error(
          'The sample image could not be loaded. Upload your own photo to get started.',
        );
      const blob = await response.blob();
      await loadPhoto(new File([blob], 'mounting-plate.png', { type: 'image/png' }), true);
    } catch (err) {
      setError(errorText(err), { kind: 'sample' });
      setBusy(null);
    }
  }

  useEffect(() => {
    void loadSample();
    return () => {
      sequenceRef.current++;
    };
  }, []);
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
    };
  }, []);
  useEffect(() => {
    if (editingName) nameInput.current?.focus();
  }, [editingName]);
  useEffect(() => {
    // Disabling a focused control during busy work drops focus to the page body. Return it once
    // the work and any dialog it opened are finished, unless the user has focused something else.
    if (busy || modal) return;
    const target = pendingFocusRef.current;
    pendingFocusRef.current = null;
    const active = document.activeElement;
    if (
      target?.isConnected &&
      !target.matches(':disabled') &&
      (!active || active === document.body)
    )
      target.focus();
  }, [busy, modal]);

  async function buildModel(openExport = false) {
    if (!trace || !buildReady || busy) return;
    const sequence = ++sequenceRef.current;
    const rev = String(revisionRef.current);
    startBusy('Building the CAD solid…');
    setError('');
    setNotice('');
    try {
      const result = await requestModel(trace.profile, widthMm, thicknessMm, projectName(), rev);
      if (sequence === sequenceRef.current && String(revisionRef.current) === rev) {
        installModel(result);
        if (openExport) {
          setExportError('');
          setModal('export');
        } else setNotice('Model updated. The preview and downloads now use these dimensions.');
      } else releaseModel(result.id);
    } catch (err) {
      if (sequence === sequenceRef.current) setError(errorText(err), { kind: 'build', openExport });
    } finally {
      if (sequence === sequenceRef.current) setBusy(null);
    }
  }

  async function retrace(newDetail: Detail, newThreshold = threshold, newInverted = inverted) {
    if (!sourceFile || busy) return false;
    const sequence = ++sequenceRef.current;
    startBusy('Finding the outline…');
    setError('');
    setModal(null);
    try {
      const result = await requestTrace(sourceFile, newDetail, newThreshold, newInverted);
      if (sequence !== sequenceRef.current) return false;
      // Only a new outline makes the model outdated; a failed trace leaves it current.
      invalidate();
      setTrace(result);
      setDetail(newDetail);
      setThreshold(newThreshold);
      setInverted(newInverted);
      if (referenceCalibration) {
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
    if (file.size > MAX_FILE) {
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
      const restoredDesign = recipe.version === 2 ? recipe.design! : { ...DEFAULT_DESIGN };
      const bounds = getBounds(recipe.profile);
      if (bounds.width <= 0 || bounds.height <= 0)
        throw new Error('The project outline has no area.');
      const restoredError = designError(restoredDesign, {
        width: recipe.width_mm,
        height: (bounds.height / bounds.width) * recipe.width_mm,
        thickness: recipe.thickness_mm,
      });
      if (restoredError) throw new Error(`This project could not be opened. ${restoredError}`);
      const rev = invalidate();
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
      if (sequence === sequenceRef.current && String(revisionRef.current) === rev) {
        installModel(built);
        setNotice('Project restored and rebuilt.');
      } else releaseModel(built.id);
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
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      setError('Choose a PNG, JPEG or WebP image, or a saved project JSON file.');
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
  function changeUnit(next: Unit) {
    if (next === unit) return;
    const factor = next === 'in' ? 25.4 : 1;
    // Convert every entered number, valid or not, so the field keeps showing the stored length.
    if (width.trim() !== '' && Number.isFinite(widthMm))
      setWidth((widthMm / factor).toFixed(next === 'in' ? 6 : 4));
    if (thickness.trim() !== '' && Number.isFinite(thicknessMm))
      setThickness((thicknessMm / factor).toFixed(next === 'in' ? 6 : 4));
    if (measuredHeight.trim() !== '' && Number.isFinite(Number(measuredHeight)))
      setMeasuredHeight(
        String(Number(((Number(measuredHeight) * unitFactor) / factor).toPrecision(12))),
      );
    setUnit(next);
  }
  function openTrace() {
    setDraftThreshold(threshold === -1 ? (trace?.threshold ?? 150) : threshold);
    setDraftAuto(threshold === -1);
    setDraftInverted(inverted);
    setModal('trace');
  }
  function saveProject() {
    if (!trace || !buildReady) return;
    const heightIssue = measuredHeightError(measuredHeight, unitFactor);
    if (heightIssue) {
      setError(heightIssue);
      return;
    }
    downloadJson({
      format: 'pictures-to-cad',
      version: 2,
      name: projectName(),
      profile: trace.profile,
      width_mm: widthMm,
      thickness_mm: thicknessMm,
      design,
      ...(referenceCalibration ? { reference_calibration: referenceCalibration } : {}),
      ...(measuredHeight.trim() ? { measured_height_mm: Number(measuredHeight) * unitFactor } : {}),
    });
    setNotice(
      'Project download started. Your outline, measurements and design settings are included; the photo is not.',
    );
  }
  async function exportFile(kind: 'step' | 'stl' | 'dxf' | 'scad' | 'parts') {
    if (!model || !current || downloading) return;
    const downloadUrl = model.downloads[kind];
    if (!downloadUrl) return;
    setDownloading(kind);
    setExportError('');
    try {
      const response = await fetch(downloadUrl, { signal: AbortSignal.timeout(30000) });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
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
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${projectName()
        .replace(/[^a-zA-Z0-9_-]+/g, '-')
        .slice(0, 60)}.${kind === 'parts' ? 'parts.zip' : kind}`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice(`${kind.toUpperCase()} download started. Exported geometry uses millimeters.`);
    } catch (err) {
      const message = errorText(err);
      setExportError(message);
      setError(message, { kind: 'build', openExport: true });
    } finally {
      setDownloading(null);
    }
  }
  async function clearTemporaryExports() {
    if (busy) return;
    startBusy('Clearing temporary exports…');
    setError('');
    try {
      await api<{ deleted: number }>('/api/models', { method: 'DELETE' });
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
      <header className="topbar">
        <a className="brand" href="#workbench" aria-label="Pictures to CAD workbench">
          <Cube size={35} weight="light" />
          <span>Pictures to CAD</span>
        </a>
        <div className="project-name">
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
        </div>
        <div className="header-actions">
          <a
            className="text-button guide-button"
            href="/reference-library/index.html#cad"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="OpenSCAD workspace (opens in a new tab)"
          >
            <Cube size={25} />
            <span>OpenSCAD</span>
          </a>
          <button
            className="text-button guide-button"
            aria-label="Capture guide"
            onClick={() => setModal('guide')}
          >
            <Question size={25} />
            <span>Capture guide</span>
          </button>
          <button
            className="outlined-button save-button"
            aria-label="Save project"
            onClick={saveProject}
            disabled={!trace || !buildReady || !!busy}
          >
            <FloppyDisk size={24} />
            <span>Save project</span>
          </button>
        </div>
      </header>

      <main id="workbench">
        <nav className="workflow" aria-label="Conversion workflow">
          <button className="workflow-step" onClick={() => setModal('photo')} disabled={!!busy}>
            <span className="step-icon">
              <Camera size={26} />
            </span>
            <span>Photo</span>
          </button>
          <span className="step-line" />
          <button className="workflow-step" onClick={openTrace} disabled={!sourceFile || !!busy}>
            <span className="step-icon">
              <PencilSimple size={26} />
            </span>
            <span>Trace</span>
          </button>
          <span className="step-line" />
          <button
            className="workflow-step active"
            aria-current="step"
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
            className="workflow-step"
            onClick={handlePrimary}
            disabled={!trace || !buildReady || !!busy}
          >
            <span className="step-icon">
              <DownloadSimple size={27} />
            </span>
            <span>Export</span>
          </button>
        </nav>

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
              onDragLeave={() => setDragging(false)}
              onDrop={drop}
            >
              {trace ? (
                <SourceCanvas trace={trace} showOutline={outline} widthLabel={widthLabel} />
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

        <section className="controls-section" aria-label="Model dimensions">
          <div className="controls-grid">
            <div className="control-group">
              <ArrowsHorizontal size={29} />
              <div className="field-stack">
                <div className="label-row">
                  <label htmlFor="reference-width">Reference width</label>
                  <div className="unit-toggle" aria-label="Measurement units">
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
                    ? `${trace.profile.holes.length} through holes detected`
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
            <ReferenceCalibration
              key={measurementReset}
              trace={trace}
              calibration={referenceCalibration}
              unit={unit}
              widthMm={validWidth ? widthMm : null}
              height={measuredHeight}
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
            />
          )}
          <p className="measurement-note">
            <Info size={21} />
            <span>
              Scale and thickness are supplied by you. Check dimensions before manufacturing.
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
          onChange={(next) => {
            setDesign(next);
            invalidate();
            setError('');
          }}
          busy={!!busy}
          sourceSize={sourceSize}
          model={model}
          current={current}
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
          busy={!!busy || !!designIssue}
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
          {current ? 'Solid ready' : busy ? 'Processing' : 'Awaiting dimensions'}
        </span>
      </footer>
      <input
        ref={fileInput}
        className="sr-only"
        type="file"
        accept="image/png,image/jpeg,image/webp,application/json,.json"
        aria-label="Choose photo or project"
        onChange={onFile}
      />

      {modal === 'photo' && (
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
          <div
            className={`upload-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={drop}
          >
            <UploadSimple size={40} weight="light" />
            <strong>Drop a photo or saved project</strong>
            <p>PNG, JPEG, WebP or project JSON · up to 10 MiB</p>
            <button className="primary-button" onClick={() => fileInput.current?.click()}>
              Browse files
            </button>
          </div>
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

      {modal === 'trace' && (
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
            <label className="check-field">
              <input
                type="checkbox"
                checked={draftAuto}
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
              disabled={draftAuto}
              onChange={(e) => setDraftThreshold(Number(e.target.value))}
            />
            <p className="field-explanation">
              For a dark part on a light background, raise the threshold to include more of the dark
              edge.
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
              onClick={() => void retrace(detail, draftAuto ? -1 : draftThreshold, draftInverted)}
            >
              Apply trace
            </button>
          </div>
        </Modal>
      )}

      {modal === 'guide' && (
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
                Enter the full outside width, or open Use a known feature and mark two measured
                endpoints. Keep the reference in the same plane as the part. Measure thickness
                separately.
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
              STEP contains a CAD solid; STL is a triangle mesh in millimeters; DXF is a 2D outline;
              SCAD is an editable polygon extrusion for OpenSCAD. Save the project JSON to keep your
              outline and parameters. STEP does not retain a parametric feature history.
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
              Deletes all generated files on this instance. Downloaded copies are unaffected. The
              current model will need to be rebuilt.
            </p>
          </div>
          <div className="modal-footer">
            <button className="primary-button" onClick={() => setModal(null)}>
              Back to the workbench
            </button>
          </div>
        </Modal>
      )}

      {modal === 'export' && current && model && (
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
          </div>
          <div className="export-options">
            {(
              [
                {
                  type: 'step',
                  label: 'STEP',
                  description: 'CAD solid for CAD applications',
                  suffix: '.step',
                },
                {
                  type: 'stl',
                  label: 'STL',
                  description: 'Triangle mesh for 3D printing',
                  suffix: '.stl',
                },
                {
                  type: 'dxf',
                  label: 'DXF',
                  description: 'Flat outline for 2D workflows',
                  suffix: '.dxf',
                },
                {
                  type: 'scad',
                  label: 'OpenSCAD',
                  description: 'Editable polygon extrusion with the current holes and design',
                  suffix: '.scad',
                },
                ...(model.downloads.parts
                  ? [
                      {
                        type: 'parts' as const,
                        label: 'Parts ZIP',
                        description: 'Individual STEP and STL files for each built part',
                        suffix: '.zip',
                      },
                    ]
                  : []),
              ] as const
            ).map((format) => (
              <button
                key={format.type}
                className="export-row"
                disabled={!!downloading}
                onClick={() => void exportFile(format.type)}
              >
                <span className="format-name">{format.label}</span>
                <span className="format-description">
                  {format.description}
                  <small>{format.suffix} · millimeters</small>
                </span>
                {downloading === format.type ? (
                  <SpinnerGap size={23} className="spinner" />
                ) : (
                  <DownloadSimple size={23} />
                )}
              </button>
            ))}
          </div>
          <div className="inline-note">
            <Info size={20} />
            <p>
              All geometry exports use millimeters, including when the interface displays inches.
              Select millimeters when importing STL. Verify the dimensions before cutting or
              printing.
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
