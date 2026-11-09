import { useEffect, useRef, useState } from 'react';
import type { PointerEvent } from 'react';
import { calibrationError, measuredHeightError, referenceWidth } from './calibration';
import type { Point, ReferenceCalibration as Calibration, TraceResult } from './types';
import './ReferenceCalibration.css';

export default function ReferenceCalibration({
  trace,
  calibration,
  unit,
  widthMm,
  height,
  disabled,
  onApply,
  onHeight,
}: {
  trace: TraceResult;
  calibration: Calibration | null;
  unit: 'mm' | 'in';
  widthMm: number | null;
  height: string;
  disabled: boolean;
  onApply: (value: Calibration, widthMm: number) => void;
  onHeight: (value: string) => void;
}) {
  const factor = unit === 'in' ? 25.4 : 1;
  const [points, setPoints] = useState<[[string, string], [string, string]]>([
    ['', ''],
    ['', ''],
  ]);
  const [length, setLength] = useState('');
  const [nextPoint, setNextPoint] = useState<0 | 1>(0);
  const previousFactor = useRef(factor);
  const previousCalibration = useRef<Calibration | null | undefined>(undefined);
  useEffect(() => {
    if (previousCalibration.current !== calibration) {
      if (calibration) {
        setPoints(calibration.reference_points.map((p) => p.map(String)) as typeof points);
        setLength(String(Number((calibration.known_length_mm / factor).toPrecision(12))));
      } else {
        setPoints([
          ['', ''],
          ['', ''],
        ]);
        setLength('');
      }
      setNextPoint(0);
    } else if (previousFactor.current !== factor) {
      const previous = previousFactor.current;
      setLength((old) =>
        old.trim() && Number.isFinite(Number(old))
          ? String(Number(((Number(old) * previous) / factor).toPrecision(12)))
          : old,
      );
    }
    previousFactor.current = factor;
    previousCalibration.current = calibration;
  }, [calibration, factor]);

  const value: Calibration = {
    known_length_mm: length.trim() ? Number(length) * factor : NaN,
    reference_points: points.map((p) => p.map((v) => (v.trim() ? Number(v) : NaN))) as [
      Point,
      Point,
    ],
    image_size: { width: trace.image.width, height: trace.image.height },
  };
  const referenceAvailable =
    [trace.image.width, trace.image.height].every(
      (n) => Number.isInteger(n) && n > 0 && n <= 1400,
    ) &&
    [trace.profile.outer, ...trace.profile.holes].every((loop) =>
      loop.every(([x, y]) => x >= 0 && y >= 0 && x <= trace.image.width && y <= trace.image.height),
    );
  const issue = calibrationError(value);
  const derivedWidth = issue ? NaN : referenceWidth(value, trace.bounds.width);
  const rangeIssue =
    !issue && (!Number.isFinite(derivedWidth) || derivedWidth < 0.1 || derivedWidth > 2000)
      ? 'This reference gives an outside width beyond 0.1–2000 mm. Check the points and length.'
      : null;
  const pixelSpan = issue
    ? NaN
    : Math.hypot(
        value.reference_points[1][0] - value.reference_points[0][0],
        value.reference_points[1][1] - value.reference_points[0][1],
      );
  const heightIssue = measuredHeightError(height, factor);
  const estimate = widthMm === null ? null : (trace.bounds.height / trace.bounds.width) * widthMm;
  const difference =
    estimate !== null && height.trim() && !heightIssue ? estimate - Number(height) * factor : null;
  const format = (mm: number) => (mm / factor).toFixed(unit === 'in' ? 4 : 3);
  const hasDraft = length !== '' || points.some((p) => p.some((v) => v !== ''));

  function mark(event: PointerEvent<SVGSVGElement>) {
    if (disabled || event.button !== 0) return;
    // The SVG's aspect ratio matches its viewBox, so the visible image and numeric frame agree
    // at every CSS size and device pixel ratio. Keyboard users can enter the same coordinates.
    const matrix = event.currentTarget.getScreenCTM();
    if (!matrix) return;
    const local = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
    const point: [string, string] = [
      Math.max(0, Math.min(trace.image.width, local.x)).toFixed(3),
      Math.max(0, Math.min(trace.image.height, local.y)).toFixed(3),
    ];
    setPoints((old) => (nextPoint === 0 ? [point, old[1]] : [old[0], point]));
    setNextPoint(nextPoint === 0 ? 1 : 0);
  }

  return (
    <div className="measurement-tools">
      <details className="reference-tool">
        <summary>Use a known feature{calibration ? ' · scale applied' : ''}</summary>
        <div className="reference-content">
          <p>
            Mark two ends of a measured feature in the same plane as the outline. Use a front-on
            photo. This sets a uniform scale; it does not correct perspective or lens distortion.
          </p>
          {!referenceAvailable ? (
            <p>
              This saved outline has no compatible working-image frame. Upload its original photo to
              use feature scaling.
            </p>
          ) : (
            <div className="reference-layout">
              <div>
                <svg
                  className={`reference-image ${disabled ? 'disabled' : ''}`}
                  viewBox={`0 0 ${trace.image.width} ${trace.image.height}`}
                  style={{ aspectRatio: `${trace.image.width} / ${trace.image.height}` }}
                  role="img"
                  aria-label="Reference endpoints on the working image. Use the coordinate fields to set endpoints with a keyboard."
                  onPointerDown={mark}
                >
                  {trace.image.data_url ? (
                    <image
                      href={trace.image.data_url}
                      width={trace.image.width}
                      height={trace.image.height}
                    />
                  ) : (
                    <path
                      d={[trace.profile.outer, ...trace.profile.holes]
                        .map((loop) => `M ${loop.map((p) => p.join(',')).join(' L ')} Z`)
                        .join(' ')}
                      fillRule="evenodd"
                      fill="#dde7e9"
                      stroke="#46636a"
                      strokeWidth="2"
                    />
                  )}
                  {value.reference_points.every((p) => p.every(Number.isFinite)) && (
                    <line
                      x1={value.reference_points[0][0]}
                      y1={value.reference_points[0][1]}
                      x2={value.reference_points[1][0]}
                      y2={value.reference_points[1][1]}
                      stroke="#007b86"
                      strokeWidth="3"
                    />
                  )}
                  {value.reference_points.map((p, i) =>
                    p.every(Number.isFinite) ? (
                      <g key={i}>
                        <circle
                          cx={p[0]}
                          cy={p[1]}
                          r={trace.image.width / 80}
                          fill="#007b86"
                          stroke="white"
                          strokeWidth="2"
                        />
                        <text
                          x={p[0]}
                          y={p[1]}
                          textAnchor="middle"
                          dominantBaseline="central"
                          fill="white"
                          fontSize={trace.image.width / 65}
                        >
                          {i + 1}
                        </text>
                      </g>
                    ) : null,
                  )}
                </svg>
                <p className="field-hint" aria-live="polite">
                  Click or tap endpoint {nextPoint + 1}, or enter coordinates below. Working image:{' '}
                  {trace.image.width} × {trace.image.height} px.
                  {!trace.image.data_url &&
                    ' Restored outline only; the photo is not in this project.'}
                </p>
              </div>
              <div className="reference-fields">
                <fieldset disabled={disabled}>
                  <legend>Working-image endpoints (px)</legend>
                  {points.map((point, index) => (
                    <div className="endpoint-row" key={index}>
                      <span>{index + 1}</span>
                      {point.map((coordinate, axis) => (
                        <label key={axis}>
                          {axis === 0 ? 'X' : 'Y'}
                          <input
                            aria-label={`Endpoint ${index + 1} ${axis === 0 ? 'X' : 'Y'}`}
                            type="number"
                            step="any"
                            min="0"
                            max={axis === 0 ? trace.image.width : trace.image.height}
                            value={coordinate}
                            onChange={(e) =>
                              setPoints(
                                (old) =>
                                  old.map((p, i) =>
                                    i === index
                                      ? p.map((v, a) => (a === axis ? e.target.value : v))
                                      : p,
                                  ) as typeof points,
                              )
                            }
                          />
                        </label>
                      ))}
                    </div>
                  ))}
                  <label className="known-length">
                    Known feature length ({unit})
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={length}
                      onChange={(e) => setLength(e.target.value)}
                    />
                  </label>
                </fieldset>
                <div aria-live="polite" className="reference-result">
                  {hasDraft && (issue || rangeIssue) ? (
                    <p>{issue || rangeIssue}</p>
                  ) : Number.isFinite(derivedWidth) ? (
                    <p>
                      Outside width:{' '}
                      <strong>
                        {format(derivedWidth)} {unit}
                      </strong>
                    </p>
                  ) : (
                    <p>Set two endpoints and a known length to calculate scale.</p>
                  )}
                  {pixelSpan < 200 && (
                    <p>
                      A longer reference reduces sensitivity to endpoint placement. This short span
                      is not an accuracy check.
                    </p>
                  )}
                </div>
                <button
                  className="secondary-button"
                  disabled={disabled || !!issue || !!rangeIssue}
                  onClick={() => onApply(value, derivedWidth)}
                >
                  Apply reference scale
                </button>
                <p className="field-hint">
                  Draft edits affect width only when you apply them. Editing Reference width clears
                  its applied reference.
                </p>
              </div>
            </div>
          )}
        </div>
      </details>
      <details className="reference-tool">
        <summary>Independent height check{height.trim() ? ' · measurement entered' : ''}</summary>
        <div className="reference-content height-check">
          <p>
            Measure the full outside height separately. Keep it independent of the feature used to
            set scale. This compares the source outline before Design &amp; print scaling.
          </p>
          <label>
            Measured outside height ({unit})
            <input
              type="number"
              step="any"
              min={0.1 / factor}
              max={2000 / factor}
              value={height}
              disabled={disabled}
              aria-invalid={!!heightIssue}
              aria-describedby="height-check-result"
              onChange={(e) => onHeight(e.target.value)}
              placeholder="Optional"
            />
          </label>
          <div id="height-check-result" className="reference-result" aria-live="polite">
            {heightIssue ? (
              <p>{heightIssue}</p>
            ) : estimate === null ? (
              <p>Set a valid reference width to estimate source height.</p>
            ) : (
              <p>
                Estimated source height:{' '}
                <strong>
                  {format(estimate)} {unit}
                </strong>
                .
                {difference !== null && (
                  <>
                    {' '}
                    Difference (estimate − measured):{' '}
                    <strong>
                      {difference >= 0 ? '+' : ''}
                      {format(difference)} {unit}
                    </strong>
                    .
                  </>
                )}
              </p>
            )}
            <p>
              Agreement does not establish manufacturing accuracy. Check more independent features
              and a physical prototype.
            </p>
          </div>
        </div>
      </details>
    </div>
  );
}
