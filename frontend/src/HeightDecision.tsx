import { assessHeight, heightCheckDraft } from './heightCheck';

export default function HeightDecision({
  estimate,
  measured,
  allowance,
  bound,
  unit,
  disabled,
  onAllowance,
  onBound,
}: {
  estimate: number | null;
  measured: number | null;
  allowance: string;
  bound: string;
  unit: 'mm' | 'in';
  disabled: boolean;
  onAllowance: (value: string) => void;
  onBound: (value: string) => void;
}) {
  const factor = unit === 'in' ? 25.4 : 1;
  const draft = heightCheckDraft(allowance, bound, factor);
  const result =
    draft.value && estimate !== null && measured !== null
      ? assessHeight(estimate, measured, draft.value)
      : null;
  const format = (mm: number) => String(Number((mm / factor).toPrecision(10)));
  return (
    <div className="height-decision">
      <p id="height-decision-help">
        Optional: set the allowed source-height deviation and an absolute error bound for your
        independent measurement. Supply a defensible bound for the whole measurement method;
        instrument resolution alone does not establish it. Leave both blank if unknown.
      </p>
      <div className="height-decision-fields">
        <label>
          Allowed height deviation (±{unit})
          <input
            type="number"
            step="any"
            min="0"
            max={2000 / factor}
            value={allowance}
            disabled={disabled}
            aria-describedby="height-decision-help height-decision-result"
            aria-invalid={!!draft.error}
            onChange={(event) => onAllowance(event.target.value)}
            placeholder="Optional"
          />
        </label>
        <label>
          Measurement error bound (±{unit})
          <input
            type="number"
            step="any"
            min="0"
            max={2000 / factor}
            value={bound}
            disabled={disabled}
            aria-describedby="height-decision-help height-decision-result"
            aria-invalid={!!draft.error}
            onChange={(event) => onBound(event.target.value)}
            placeholder="Unknown until entered"
          />
        </label>
      </div>
      <div id="height-decision-result" className="reference-result" aria-live="polite">
        {draft.error ? (
          <p>{draft.error}</p>
        ) : result && draft.value ? (
          <>
            <p>
              <strong>
                {result.status === 'within'
                  ? 'Within entered allowance'
                  : result.status === 'outside'
                    ? 'Outside entered allowance'
                    : 'Inconclusive: interval reaches a limit'}
              </strong>
            </p>
            <p>
              Source-height discrepancy under entered bound: {format(result.low)} to{' '}
              {format(result.high)} {unit}. Allowed deviation: ±{format(draft.value.allowance_mm)}{' '}
              {unit}.
            </p>
            <p>
              {result.status === 'within'
                ? 'The complete interval is strictly inside the allowance for this one source dimension.'
                : result.status === 'outside'
                  ? 'The complete interval is outside the allowance. Review the capture, trace, scale and measurement.'
                  : 'The interval touches or crosses an allowance limit. Improve the measurement or review the requirement.'}
            </p>
          </>
        ) : (
          <p>Undecided: enter a valid source width, independent height and both decision inputs.</p>
        )}
        <p className="field-hint">
          This compares the source outline with your measurement under the bound you supply. The
          workbench does not validate that bound. It does not assess other dimensions, printed fit
          or strength. No probability or confidence level is assigned.
        </p>
      </div>
    </div>
  );
}
