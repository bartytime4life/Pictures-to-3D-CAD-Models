import { useState } from 'react';
import { scaleSensitivity } from './calibration';
import type { ReferenceCalibration } from './types';

export default function ReferenceSensitivity({
  calibration,
  outlineWidth,
  unit,
  disabled,
  available,
}: {
  calibration: ReferenceCalibration;
  outlineWidth: number;
  unit: 'mm' | 'in';
  disabled: boolean;
  available: boolean;
}) {
  const [offset, setOffset] = useState('1');
  const offsetPx = offset.trim() ? Number(offset) : NaN;
  const invalidOffset = !Number.isFinite(offsetPx) || offsetPx < 0 || offsetPx > 5;
  const result = scaleSensitivity(calibration, outlineWidth, offsetPx);
  const format = (mm: number) =>
    `${(mm / (unit === 'in' ? 25.4 : 1)).toFixed(unit === 'in' ? 4 : 3)} ${unit}`;
  const currentX =
    result && result.high > result.low
      ? 24 + (432 * (result.current - result.low)) / (result.high - result.low)
      : 240;
  const lowX = result && result.high > result.low ? 24 : 240;
  const highX = result && result.high > result.low ? 456 : 240;

  return (
    // Keep the draft and disclosure state while unit conversion briefly makes
    // the reference invalid; hide the scenario instead of recreating it.
    <details className="reference-sensitivity" hidden={!available}>
      <summary>Explore endpoint placement</summary>
      <p>
        Try moving each endpoint along the reference by the amount below, in opposite directions.
        The measured feature length and traced outside boundary stay fixed.
      </p>
      <label>
        Assumed shift per endpoint (px)
        <input
          type="number"
          min="0"
          max="5"
          step="0.1"
          value={offset}
          disabled={disabled}
          aria-invalid={invalidOffset}
          aria-describedby="reference-sensitivity-result"
          onChange={(event) => setOffset(event.target.value)}
        />
      </label>
      <div id="reference-sensitivity-result" aria-live="polite">
        {invalidOffset ? (
          <p>Enter a shift from 0 to 5 working-image pixels.</p>
        ) : !result ? (
          <p>
            This shift can collapse the reference span to zero. Use a longer reference or a smaller
            shift to compare widths.
          </p>
        ) : (
          <>
            <p className="sensitivity-scale">
              Working-image span: <strong>{result.span.toFixed(1)} px</strong> · Scale:{' '}
              <strong>{result.mmPerPixel.toPrecision(4)} mm/px</strong>
            </p>
            <svg
              className="sensitivity-plot"
              viewBox="0 0 480 56"
              role="img"
              aria-label={`Outside width scenario from ${format(result.low)} to ${format(result.high)}; current draft ${format(result.current)}.`}
            >
              <line x1={lowX} x2={highX} y1="28" y2="28" className="sensitivity-range" />
              <line x1={lowX} x2={lowX} y1="18" y2="38" />
              <line x1={highX} x2={highX} y1="18" y2="38" />
              <circle cx={currentX} cy="28" r="7" />
            </svg>
            <dl className="sensitivity-values">
              <div>
                <dt>Longer span</dt>
                <dd>{format(result.low)}</dd>
              </div>
              <div>
                <dt>Current draft</dt>
                <dd>{format(result.current)}</dd>
              </div>
              <div>
                <dt>Shorter span</dt>
                <dd>{format(result.high)}</dd>
              </div>
            </dl>
          </>
        )}
      </div>
      <p className="field-hint">
        This is a sensitivity scenario, not a measured error range or accuracy guarantee. It
        excludes lens distortion, perspective, tracing error, and measurement error. Exploring it
        does not apply scale or change the model.
      </p>
    </details>
  );
}
