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
              onChange={(e) => onChange({ ...value, height: e.target.value })}
            />
          </label>
        </div>
      )}
      <p className="field-explanation">
        Lay the part on a sheet of known size and photograph the whole sheet. The sheet sets the
        scale and corrects perspective and lens distortion; the entered thickness corrects for
        visible side walls. Measure your sheet: paper sizes vary slightly.
      </p>
    </div>
  );
}
