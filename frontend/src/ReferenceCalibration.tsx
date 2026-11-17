import { useEffect, useRef, useState } from 'react';
import type { PointerEvent } from 'react';
import { calibrationError, measuredHeightError, referenceWidth } from './calibration';
import ReferenceSensitivity from './ReferenceSensitivity';
import HeightDecision from './HeightDecision';
import { COMMON_REFERENCES } from './commonReferences';
import type { Point, ReferenceCalibration as Calibration, TraceResult } from './types';
import './ReferenceCalibration.css';

export default function ReferenceCalibration({
  trace,
  calibration,
  unit,
  widthMm,
  height,
  heightAllowance,
  heightBound,
  disabled,
  onApply,
  onHeight,
  onHeightAllowance,
  onHeightBound,
}: {
  trace: TraceResult;
  calibration: Calibration | null;
  unit: 'mm' | 'in';
  widthMm: number | null;
  height: string;
  heightAllowance: string;
  heightBound: string;
  disabled: boolean;
  onApply: (value: Calibration, widthMm: number) => void;
  onHeight: (value: string) => void;
  onHeightAllowance: (value: string) => void;
  onHeightBound: (value: string) => void;
}) {
  const factor = unit === 'in' ? 25.4 : 1;
  const [points, setPoints] = useState<[[string, string], [string, string]]>([
    ['', ''],
    ['', ''],
  ]);
  const [length, setLength] = useState('');
  const [referenceObject, setReferenceObject] = useState('custom');
  const [nextPoint, setNextPoint] = useState<0 | 1>(0);
  const previousFactor = useRef(factor);
  const previousCalibration = useRef<Calibration | null | undefined>(undefined);
  const previousFrame = useRef(trace.image);
  useEffect(() => {
    const frameChanged =
      previousFrame.current.width !== trace.image.width ||
      previousFrame.current.height !== trace.image.height ||
      previousFrame.current.data_url !== trace.image.data_url;
    // Applied evidence is coordinated by App. An unapplied draft has no such owner:
    // discard its points if rectification or resizing replaces their image frame.
    // Identical working-image pixels preserve drafts through ordinary detail changes.
    if (previousCalibration.current !== calibration || (frameChanged && !calibration)) {
      if (calibration) {
        setPoints(calibration.reference_points.map((p) => p.map(String)) as typeof points);
        setLength(String(calibration.known_length_mm / factor));
        setReferenceObject((previous) =>
          COMMON_REFERENCES.find((item) => item.id === previous)?.lengthMm ===
          calibration.known_length_mm
            ? previous
            : 'custom',
        );
      } else {
        setReferenceObject('custom');
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
          ? String((Number(old) * previous) / factor)
          : old,
      );
    }
    previousFactor.current = factor;
    previousCalibration.current = calibration;
    previousFrame.current = trace.image;
  }, [calibration, factor, trace.image.width, trace.image.height, trace.image.data_url]);

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
  const heightIssue = measuredHeightError(height, factor);
  const estimate = widthMm === null ? null : (trace.bounds.height / trace.bounds.width) * widthMm;
  const difference =
    estimate !== null && height.trim() && !heightIssue ? estimate - Number(height) * factor : null;
  const format = (mm: number) => (mm / factor).toFixed(unit === 'in' ? 4 : 3);
  const hasDraft = length !== '' || points.some((p) => p.some((v) => v !== ''));
  const selectedObject = COMMON_REFERENCES.find((item) => item.id === referenceObject);
  const pixelSpan = Math.hypot(
    value.reference_points[1][0] - value.reference_points[0][0],
    value.reference_points[1][1] - value.reference_points[0][1],
  );

  function chooseReference(id: string) {
    const selected = COMMON_REFERENCES.find((item) => item.id === id);
    setReferenceObject(selected?.id ?? 'custom');
    setLength(selected ? String(selected.lengthMm / factor) : '');
    // A different object needs its own visible endpoints. Never reuse a previous span
    // as if recognizing the object had located it in the image.
    setPoints([
      ['', ''],
      ['', ''],
    ]);
    setNextPoint(0);
  }

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
                <div className="common-reference">
                  <label htmlFor="common-reference-object">Reference object (optional)</label>
                  <select
                    id="common-reference-object"
                    value={referenceObject}
                    disabled={disabled || !trace.image.data_url}
                    onChange={(event) => chooseReference(event.target.value)}
                    aria-describedby="common-reference-help"
                  >
                    <option value="custom">Custom or saved length</option>
                    {COMMON_REFERENCES.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label} · {item.lengthMm.toFixed(2)} mm diameter
                      </option>
                    ))}
                  </select>
                  <p id="common-reference-help" className="field-hint">
                    {selectedObject ? (
                      <>
                        {selectedObject.instruction} This is a nominal size; verify your coin and
                        edit the length below if measured differently. Keep it in the same plane as
                        the part and photograph straight-on.{' '}
                        <a href={selectedObject.sourceUrl} target="_blank" rel="noreferrer">
                          {selectedObject.sourceTitle} (opens in a new tab)
                        </a>
                      </>
                    ) : (
                      'A coin or another measured object visible beside the part can set scale. Choose it, then mark its two endpoints in the photo.'
                    )}
                  </p>
                </div>
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
                      onChange={(e) => {
                        setLength(e.target.value);
                        setReferenceObject('custom');
                      }}
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
                  {!issue && !rangeIssue && (
                    <p className="reference-scale-math">
                      Scale: {(value.known_length_mm / factor).toFixed(unit === 'in' ? 4 : 3)}{' '}
                      {unit} ÷ {pixelSpan.toFixed(2)} px ={' '}
                      {(value.known_length_mm / factor / pixelSpan).toPrecision(5)} {unit}/px.{' '}
                      Applied to the traced outline width.
                    </p>
                  )}
                </div>
                <ReferenceSensitivity
                  calibration={value}
                  outlineWidth={trace.bounds.width}
                  unit={unit}
                  disabled={disabled}
                  available={!issue && !rangeIssue}
                />
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
          <HeightDecision
            estimate={estimate}
            measured={height.trim() && !heightIssue ? Number(height) * factor : null}
            allowance={heightAllowance}
            bound={heightBound}
            unit={unit}
            disabled={disabled}
            onAllowance={onHeightAllowance}
            onBound={onHeightBound}
          />
        </div>
      </details>
    </div>
  );
}
