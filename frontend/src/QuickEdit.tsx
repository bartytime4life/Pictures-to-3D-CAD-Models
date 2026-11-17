import { useEffect, useId, useState } from 'react';
import {
  ArrowCounterClockwise,
  ArrowClockwise,
  LinkSimple,
  SlidersHorizontal,
} from '@phosphor-icons/react';
import { designError } from './design';
import {
  formatTargetSize,
  targetSizeChange,
  type QuickEditDimension,
  type SourceSize,
} from './quickEditValues';
import type { DesignSettings } from './types';
import './QuickEdit.css';

type QuickEditProps = {
  design: DesignSettings;
  onChange: (design: DesignSettings) => void;
  sourceSize: SourceSize | null;
  disabled: boolean;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onAdvanced: () => void;
};

export default function QuickEdit({
  design,
  onChange,
  sourceSize,
  disabled,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onAdvanced,
}: QuickEditProps) {
  const id = useId();
  const targetWidth = sourceSize ? (sourceSize.width * design.scale_percent) / 100 : NaN;
  const targetHeight = sourceSize ? (sourceSize.height * design.scale_percent) / 100 : NaN;
  const targetThickness = sourceSize
    ? (sourceSize.thickness * design.thickness_percent) / 100
    : NaN;
  const [widthDraft, setWidthDraft] = useState(formatTargetSize(targetWidth));
  const [thicknessDraft, setThicknessDraft] = useState(formatTargetSize(targetThickness));
  const [issues, setIssues] = useState({ width: '', thickness: '', preset: '' });

  // Imports, undo, and edits in the advanced panel replace local drafts, even if
  // a different setting changed while the requested dimension stayed the same.
  useEffect(() => {
    setWidthDraft(formatTargetSize(targetWidth));
    setThicknessDraft(formatTargetSize(targetThickness));
    setIssues({ width: '', thickness: '', preset: '' });
  }, [
    design,
    sourceSize?.width,
    sourceSize?.height,
    sourceSize?.thickness,
    targetWidth,
    targetThickness,
  ]);

  const commit = (dimension: QuickEditDimension, draft: string) => {
    if (disabled || !sourceSize) return;
    // The display is rounded for readability. Merely focusing and leaving it
    // must not round the committed scale or create an undo entry.
    const displayed = formatTargetSize(dimension === 'width' ? targetWidth : targetThickness);
    if (draft === displayed) {
      setIssues((previous) => ({ ...previous, [dimension]: '' }));
      return;
    }
    const result = targetSizeChange(design, sourceSize, dimension, draft);
    setIssues((previous) => ({ ...previous, [dimension]: result.error }));
    if (result.design) onChange(result.design);
  };
  const apply = (patch: Partial<DesignSettings>) => {
    if (disabled || !sourceSize) return;
    const next = { ...design, ...patch };
    const error = designError(next, sourceSize);
    setIssues((previous) => ({ ...previous, preset: error }));
    if (!error) onChange(next);
  };
  const locked = disabled || !sourceSize;

  return (
    <section className="quick-edit" aria-label="Quick model editing">
      <div className="quick-edit-heading">
        <div>
          <h2>
            <SlidersHorizontal size={22} aria-hidden="true" /> Quick edit
          </h2>
          <p>Choose the size you want to make, then update your model.</p>
        </div>
        <div className="quick-edit-history" role="group" aria-label="Design edit history">
          <button type="button" onClick={onUndo} disabled={disabled || !canUndo}>
            <ArrowCounterClockwise size={18} aria-hidden="true" /> Undo
          </button>
          <button type="button" onClick={onRedo} disabled={disabled || !canRedo}>
            <ArrowClockwise size={18} aria-hidden="true" /> Redo
          </button>
        </div>
      </div>

      <div className="quick-edit-fields">
        <div className="quick-edit-field">
          <label htmlFor={`${id}-width`}>Target width (mm)</label>
          <input
            id={`${id}-width`}
            type="number"
            inputMode="decimal"
            step="any"
            min="0.1"
            max="2000"
            value={widthDraft}
            placeholder="Set reference size first"
            disabled={locked}
            aria-describedby={`${id}-proportions${issues.width ? ` ${id}-width-error` : ''}`}
            aria-invalid={!!issues.width}
            onChange={(event) => {
              setWidthDraft(event.target.value);
              setIssues((previous) => ({ ...previous, width: '' }));
            }}
            onBlur={() => commit('width', widthDraft)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault();
                event.currentTarget.blur();
              } else if (event.key === 'Escape') {
                event.preventDefault();
                setWidthDraft(formatTargetSize(targetWidth));
                setIssues((previous) => ({ ...previous, width: '' }));
              }
            }}
          />
          {issues.width && (
            <p id={`${id}-width-error`} className="quick-edit-error" role="alert">
              {issues.width}
            </p>
          )}
        </div>
        <div className="quick-edit-linked" id={`${id}-proportions`}>
          <LinkSimple size={20} aria-hidden="true" />
          <div>
            <span>Height stays proportional</span>
            <strong>
              {Number.isFinite(targetHeight)
                ? `${formatTargetSize(targetHeight)} mm`
                : 'Set reference size first'}
            </strong>
          </div>
        </div>
        <div className="quick-edit-field">
          <label htmlFor={`${id}-thickness`}>Target thickness (mm)</label>
          <input
            id={`${id}-thickness`}
            type="number"
            inputMode="decimal"
            step="any"
            min="0.1"
            max="500"
            value={thicknessDraft}
            placeholder="Set reference size first"
            disabled={locked}
            aria-describedby={issues.thickness ? `${id}-thickness-error` : undefined}
            aria-invalid={!!issues.thickness}
            onChange={(event) => {
              setThicknessDraft(event.target.value);
              setIssues((previous) => ({ ...previous, thickness: '' }));
            }}
            onBlur={() => commit('thickness', thicknessDraft)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault();
                event.currentTarget.blur();
              } else if (event.key === 'Escape') {
                event.preventDefault();
                setThicknessDraft(formatTargetSize(targetThickness));
                setIssues((previous) => ({ ...previous, thickness: '' }));
              }
            }}
          />
          {issues.thickness && (
            <p id={`${id}-thickness-error`} className="quick-edit-error" role="alert">
              {issues.thickness}
            </p>
          )}
        </div>
      </div>

      <div className="quick-edit-footer">
        <div className="quick-edit-presets" role="group" aria-label="XY size presets">
          <span>XY size</span>
          {[75, 100, 125, 150].map((scale) => (
            <button
              type="button"
              key={scale}
              disabled={locked}
              aria-pressed={Math.abs(design.scale_percent - scale) < 1e-8}
              onClick={() => apply({ scale_percent: scale })}
            >
              {scale}%
            </button>
          ))}
        </div>
        <div className="quick-edit-actions">
          <button
            type="button"
            disabled={locked}
            onClick={() => apply({ scale_percent: 100, thickness_percent: 100 })}
          >
            Restore measured size
          </button>
          <button type="button" disabled={disabled} onClick={onAdvanced}>
            All design &amp; print settings
          </button>
        </div>
      </div>
      {issues.preset && (
        <p className="quick-edit-error" role="alert">
          {issues.preset}
        </p>
      )}
      <p className="quick-edit-note">
        Press Enter or leave a field to apply. Your reference measurements stay unchanged.
      </p>
    </section>
  );
}
