import { useEffect, useId, useMemo, useRef, useState } from 'react';
import {
  ArrowSquareOut,
  ArrowCounterClockwise,
  CheckCircle,
  Printer,
  SlidersHorizontal,
  WarningCircle,
} from '@phosphor-icons/react';
import { designError } from './design';
import type { DesignSettings, ModelResult, ModelPart } from './types';
import { projectPlateMesh, suggestedPlateAngle } from './plateInspection';
import './PrintPreparation.css';

const presets = [
  { name: 'Quick prototype', layer: 0.28, walls: 2, infill: 10 },
  { name: 'Everyday', layer: 0.2, walls: 3, infill: 15 },
  { name: 'Fine surface', layer: 0.12, walls: 3, infill: 20 },
];

/** The model stays fixed; these controls inspect an individual mesh over a bed envelope. */
function PlatePreview({ part, design }: { part?: ModelPart; design: DesignSettings }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const id = useId();
  const suggestion = suggestedPlateAngle(part);
  const [angle, setAngle] = useState(suggestion);
  const [grid, setGrid] = useState(true);
  const [margins, setMargins] = useState(true);
  const [dimensions, setDimensions] = useState(true);
  const projection = useMemo(() => projectPlateMesh(part?.mesh, angle), [part?.mesh, angle]);
  const hasMesh = projection.points.length > 0;
  const hasSuggestion = part?.bed_fit.status === 'fits';
  useEffect(() => setAngle(suggestion), [part, suggestion]);
  function reset() {
    setAngle(suggestion);
    setGrid(true);
    setMargins(true);
    setDimensions(true);
  }
  const availableWidth = design.bed_width_mm - 2 * design.bed_margin_mm;
  const availableDepth = design.bed_depth_mm - 2 * design.bed_margin_mm;
  const insideEnvelope =
    projection.width <= availableWidth + 1e-5 && projection.depth <= availableDepth + 1e-5;
  const summary =
    part && hasMesh
      ? `Top-down bed preview. ${part.name}: preview turn ${angle.toFixed(1)} degrees; mesh footprint ${projection.width.toFixed(2)} by ${projection.depth.toFixed(2)} millimeters. ${insideEnvelope ? 'Inside' : 'Outside'} the rectangular margin envelope at this angle. Exported geometry is unchanged.`
      : part
        ? 'Top-down bed preview. A preview mesh is unavailable for this piece.'
        : 'Top-down bed preview. Build the model to inspect one piece over the bed envelope.';
  useEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (!ctx) return;
    const width = 760,
      height = 420;
    ctx.clearRect(0, 0, width, height);
    const { points, centerX, centerY } = projection;
    const scale = Math.min(
      (width - 120) / Math.max(design.bed_width_mm, projection.width, 1),
      (height - 100) / Math.max(design.bed_depth_mm, projection.depth, 1),
    );
    const bw = design.bed_width_mm * scale,
      bh = design.bed_depth_mm * scale;
    const ox = (width - bw) / 2,
      oy = (height - bh) / 2;
    ctx.fillStyle = '#152b37';
    ctx.fillRect(ox, oy, bw, bh);
    if (grid) {
      ctx.strokeStyle = '#29424e';
      ctx.lineWidth = 1;
      for (let n = 0; n <= 10; n++) {
        ctx.beginPath();
        ctx.moveTo(ox + (bw * n) / 10, oy);
        ctx.lineTo(ox + (bw * n) / 10, oy + bh);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(ox, oy + (bh * n) / 10);
        ctx.lineTo(ox + bw, oy + (bh * n) / 10);
        ctx.stroke();
      }
    }
    ctx.strokeStyle = '#6a92a6';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(ox, oy, bw, bh);
    if (margins) {
      const margin = design.bed_margin_mm * scale;
      ctx.setLineDash([6, 5]);
      ctx.strokeStyle = '#d1b56e';
      ctx.strokeRect(ox + margin, oy + margin, bw - margin * 2, bh - margin * 2);
      ctx.setLineDash([]);
    }
    if (points.length && part?.mesh) {
      ctx.fillStyle = insideEnvelope ? '#69d7df' : '#e8a76d';
      for (let i = 0; i < part.mesh.triangles.length; i += 3) {
        ctx.beginPath();
        for (let v = 0; v < 3; v++) {
          const p = points[part.mesh.triangles[i + v]];
          const x = width / 2 + (p[0] - centerX) * scale,
            y = height / 2 - (p[1] - centerY) * scale;
          if (v === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fill();
      }
    }
    if (dimensions) {
      ctx.font = '15px monospace';
      ctx.textAlign = 'center';
      ctx.fillStyle = '#d4e8f1';
      ctx.fillText(`${design.bed_width_mm} mm`, width / 2, oy + bh + 25);
      ctx.save();
      ctx.translate(ox - 22, height / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(`${design.bed_depth_mm} mm`, 0, 0);
      ctx.restore();
      ctx.textAlign = 'left';
      ctx.font = '12px sans-serif';
      ctx.fillText('Y', ox + 8, oy + 17);
      ctx.fillText('X', ox + bw - 17, oy + bh - 8);
    }
  }, [
    part,
    projection,
    design.bed_width_mm,
    design.bed_depth_mm,
    design.bed_margin_mm,
    grid,
    margins,
    dimensions,
    insideEnvelope,
  ]);
  return (
    <div className="plate-inspection">
      <figure className="plate-preview">
        <canvas ref={canvas} width={760} height={420} role="img" aria-label={summary} />
        <figcaption>
          <span className="plate-view-label">TOP VIEW · INSPECTION ONLY</span>
          <span>
            {hasMesh
              ? `${projection.width.toFixed(1)} × ${projection.depth.toFixed(1)} mm footprint`
              : part
                ? 'Preview mesh unavailable'
                : 'Waiting for a current build'}
          </span>
        </figcaption>
      </figure>
      <fieldset className="plate-view-controls" disabled={!hasMesh}>
        <legend>Inspect this piece</legend>
        <div className="plate-rotation-control">
          <label htmlFor={`${id}-rotation`}>
            Preview turn <output>{angle.toFixed(1)}°</output>
          </label>
          <input
            id={`${id}-rotation`}
            type="range"
            min="0"
            max="360"
            step="0.1"
            value={angle}
            aria-describedby={`${id}-note`}
            onChange={(event) => setAngle(Number(event.target.value))}
          />
          <div className="plate-angle-actions">
            {[0, 45, 90].map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={Math.abs(angle - value) < 0.05}
                onClick={() => setAngle(value)}
              >
                {value}°
              </button>
            ))}
            <button type="button" className="plate-suggestion" onClick={() => setAngle(suggestion)}>
              {hasSuggestion ? 'Use suggested turn' : 'Original angle'}
            </button>
          </div>
        </div>
        <div className="plate-display-options">
          <label>
            <input
              type="checkbox"
              checked={grid}
              onChange={(event) => setGrid(event.target.checked)}
            />{' '}
            Grid
          </label>
          <label>
            <input
              type="checkbox"
              checked={margins}
              onChange={(event) => setMargins(event.target.checked)}
            />{' '}
            Margin
          </label>
          <label>
            <input
              type="checkbox"
              checked={dimensions}
              onChange={(event) => setDimensions(event.target.checked)}
            />{' '}
            Dimensions
          </label>
          <button type="button" onClick={reset}>
            <ArrowCounterClockwise size={16} aria-hidden="true" /> Reset view
          </button>
        </div>
      </fieldset>
      <p className="plate-inspection-summary" role="status" aria-live="polite">
        {hasMesh
          ? `${insideEnvelope ? 'Inside' : 'Outside'} the margin envelope at this preview angle.`
          : part
            ? 'A mesh is required for visual inspection; consult the saved fit result.'
            : 'Build a model to activate inspection controls.'}
      </p>
      <p id={`${id}-note`} className="plan-note">
        Preview turns do not rotate exported geometry or change the saved fit check. This mesh
        envelope omits bed exclusions, supports and toolpaths.
      </p>
    </div>
  );
}

function PlanNumber({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  disabled: boolean;
}) {
  const id = useId();
  const [draft, setDraft] = useState(String(value));
  const [invalid, setInvalid] = useState(false);
  useEffect(() => {
    setDraft(String(value));
    setInvalid(false);
  }, [value]);
  function commit() {
    const n = Number(draft);
    if (
      !draft.trim() ||
      !Number.isFinite(n) ||
      n < min ||
      n > max ||
      (step === 1 && !Number.isInteger(n))
    ) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    if (n !== value) onChange(n);
  }
  return (
    <div className="plan-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="number"
        value={draft}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        aria-invalid={invalid}
        aria-describedby={invalid ? `${id}-error` : undefined}
        onChange={(e) => {
          setDraft(e.target.value);
          setInvalid(false);
        }}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            commit();
          }
          if (e.key === 'Escape') {
            setDraft(String(value));
            setInvalid(false);
          }
        }}
      />
      {invalid && (
        <small id={`${id}-error`} role="alert">
          Enter {min}–{max}
          {step === 1 ? ' (whole numbers)' : ''}. Current plan still uses {value}.
        </small>
      )}
    </div>
  );
}

export default function PrintPreparation({
  design,
  model,
  current,
  busy,
  canBuild,
  onChange,
  onBuild,
  onExport,
  onAdvanced,
}: {
  design: DesignSettings;
  model: ModelResult | null;
  current: boolean;
  busy: boolean;
  canBuild: boolean;
  onChange: (settings: DesignSettings) => void;
  onBuild: () => void;
  onExport: () => void;
  onAdvanced: () => void;
}) {
  const [piece, setPiece] = useState(0);
  useEffect(() => setPiece(0), [model?.id]);
  const parts = current ? (model?.parts ?? []) : [];
  const selected = parts[piece] ?? parts[0];
  const issue = designError(design);
  const update = (patch: Partial<DesignSettings>) => onChange({ ...design, ...patch });
  return (
    <section className="print-preparation" aria-labelledby="prepare-heading">
      <header className="prepare-header">
        <div>
          <p className="prepare-eyebrow">FROM MODEL TO BUILD PLATE</p>
          <h2 id="prepare-heading">
            <Printer size={24} /> Prepare for slicing
          </h2>
        </div>
        <button className="outlined-button" onClick={onAdvanced} disabled={busy}>
          <SlidersHorizontal size={18} /> Printer &amp; split settings
        </button>
      </header>
      <div className="prepare-grid">
        <div className="process-plan">
          <h3>Choose a starting point</h3>
          <p>Plan your print here. Review and apply these settings in your slicer.</p>
          <div className="process-presets" role="group" aria-label="Process starting points">
            {presets.map((p) => {
              const layer = Number(
                Math.max(0.05, Math.min(p.layer, design.nozzle_mm * 0.75)).toFixed(3),
              );
              return (
                <button
                  key={p.name}
                  disabled={busy}
                  aria-pressed={
                    design.layer_height_mm === layer &&
                    design.wall_count === p.walls &&
                    design.infill_percent === p.infill
                  }
                  onClick={() =>
                    update({
                      layer_height_mm: layer,
                      wall_count: p.walls,
                      infill_percent: p.infill,
                    })
                  }
                >
                  <strong>{p.name}</strong>
                  <span>
                    {layer} mm · {p.walls} walls · {p.infill}%
                  </span>
                </button>
              );
            })}
          </div>
          <fieldset className="process-fields" disabled={busy}>
            <legend>Process plan</legend>
            <PlanNumber
              label="Layer height (mm)"
              value={design.layer_height_mm}
              min={0.05}
              max={Math.min(1.2, design.nozzle_mm)}
              step={0.01}
              disabled={busy}
              onChange={(v) => update({ layer_height_mm: v })}
            />
            <PlanNumber
              label="Wall count"
              value={design.wall_count}
              min={1}
              max={12}
              disabled={busy}
              onChange={(v) => update({ wall_count: v })}
            />
            <PlanNumber
              label="Infill (%)"
              step={0.1}
              value={design.infill_percent}
              min={0}
              max={100}
              disabled={busy}
              onChange={(v) => update({ infill_percent: v })}
            />
            <label className="plan-field">
              <span>Supports</span>
              <select
                value={design.supports}
                onChange={(e) => update({ supports: e.target.value as DesignSettings['supports'] })}
              >
                <option value="none">None</option>
                <option value="build_plate">Build plate only</option>
                <option value="everywhere">Everywhere</option>
              </select>
            </label>
            <label className="plan-field">
              <span>Bed adhesion</span>
              <select
                value={design.adhesion}
                onChange={(e) => update({ adhesion: e.target.value as DesignSettings['adhesion'] })}
              >
                <option value="none">None</option>
                <option value="brim">Brim</option>
                <option value="raft">Raft</option>
              </select>
            </label>
            <div className="plan-field">
              <span>Material · nozzle</span>
              <strong>
                {design.material.toUpperCase()} · {design.nozzle_mm} mm
              </strong>
            </div>
          </fieldset>
          {issue && (
            <p role="alert" className="prepare-issue">
              {issue}
            </p>
          )}
          <p className="plan-note">
            Saved with your project and handoff ZIP. These are planning values; your printer profile
            determines the supported settings.
          </p>
        </div>
        <div className="plate-plan">
          <div className="plate-title">
            <h3>Check the bed</h3>
            {parts.length > 1 && (
              <label>
                Piece{' '}
                <select
                  aria-label="Preview piece on bed"
                  value={piece}
                  onChange={(e) => setPiece(Number(e.target.value))}
                >
                  {parts.map((p, i) => (
                    <option value={i} key={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {!issue && <PlatePreview part={selected} design={design} />}
          <p
            className={`plate-status ${current && model?.print_fit?.status === 'fits' ? 'fits' : ''}`}
            role="status"
          >
            {current && model?.print_fit?.status === 'fits' ? (
              <CheckCircle size={18} />
            ) : (
              <WarningCircle size={18} />
            )}
            {!current
              ? 'Update the preview to check this plan.'
              : (selected?.bed_fit.reason ??
                model?.print_fit?.reason ??
                'Review bed fit in your slicer.')}
          </p>
          <p className="plan-note">
            Rectangular bed envelope, with a dashed margin. Bed exclusions and toolpaths are not
            shown. Suggested turns are not applied to exported geometry.
          </p>
          <button
            className="primary-button prepare-action"
            disabled={busy || (!current && !canBuild)}
            onClick={current ? onExport : onBuild}
          >
            <ArrowSquareOut size={20} />{' '}
            {busy
              ? 'Please wait…'
              : current
                ? 'Review slicer handoff'
                : 'Update preparation preview'}
          </button>
        </div>
      </div>
    </section>
  );
}
