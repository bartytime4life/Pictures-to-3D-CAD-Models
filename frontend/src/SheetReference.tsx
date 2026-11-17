import { sheetChoiceError } from './sheet';
import type { SheetChoice } from './types';

/** The scale-reference choice, shared by the photo dialog and the outline dialog. */
export default function SheetReference({
  id,
  value,
  onChange,
}: {
  id: string;
  value: SheetChoice;
  onChange: (next: SheetChoice) => void;
}) {
  // Say why a custom sheet blocks tracing next to its fields, not only in a disabled button.
  const issue = sheetChoiceError(value);
  const sideInvalid = (side: string) => {
    const mm = Number(side);
    return !!side.trim() && !(Number.isFinite(mm) && mm >= 10 && mm <= 2000);
  };
  return (
    <div className="field-stack sheet-reference">
      <label htmlFor={id}>Scale reference</label>
      <select
        id={id}
        value={value.kind}
        onChange={(e) => onChange({ ...value, kind: e.target.value as SheetChoice['kind'] })}
      >
        <option value="none">None: I will enter a measured width</option>
        <option value="a4">A4 sheet (210 × 297 mm)</option>
        <option value="letter">US Letter sheet (215.9 × 279.4 mm)</option>
        <option value="custom">Custom sheet, measured</option>
      </select>
      {value.kind === 'custom' && (
        <div className="sheet-size">
          <label>
            <span>Sheet width (mm)</span>
            <input
              type="number"
              inputMode="decimal"
              min="10"
              max="2000"
              step="any"
              value={value.width}
              aria-invalid={sideInvalid(value.width)}
              aria-describedby={issue ? `${id}-error` : undefined}
              onChange={(e) => onChange({ ...value, width: e.target.value })}
            />
          </label>
          <label>
            <span>Sheet height (mm)</span>
            <input
              type="number"
              inputMode="decimal"
              min="10"
              max="2000"
              step="any"
              value={value.height}
              aria-invalid={sideInvalid(value.height)}
              aria-describedby={issue ? `${id}-error` : undefined}
              onChange={(e) => onChange({ ...value, height: e.target.value })}
            />
          </label>
        </div>
      )}
      {issue && (
        <p id={`${id}-error`} className="field-explanation">
          {issue}
        </p>
      )}
      <p className="field-explanation">
        Lay the part on a flat sheet of known size and show all four corners. The sheet sets scale
        and supports perspective and lens correction; measured thickness supports correction for
        vertical side walls. If the sheet orientation is unclear, retake the photo more directly
        above it. Measure your sheet: paper sizes vary slightly.
      </p>
    </div>
  );
}
