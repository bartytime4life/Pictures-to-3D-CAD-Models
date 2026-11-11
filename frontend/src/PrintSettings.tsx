import { useEffect, useRef, useState } from 'react';
import {
  ArrowSquareOut,
  CaretDown,
  CheckCircle,
  Info,
  Printer,
  SlidersHorizontal,
  SpinnerGap,
  WarningCircle,
  X,
} from '@phosphor-icons/react';
import { DEFAULT_DESIGN, designError } from './design';
import type { DesignSettings, ModelResult } from './types';
import './PrintSettings.css';

type PrinterProfile = {
  id: string;
  name: string;
  manufacturer: string;
  bed_shape: string;
  build_volume: { x_mm: number; y_mm: number; z_mm: number };
  excluded_areas_mm: number[][][];
  nozzle_diameters_mm: number[];
  default_nozzle_mm: number;
  profiles: {
    name: string;
    source_url: string;
    nozzle_diameters_mm: number[];
    build_volume: { x_mm: number; y_mm: number; z_mm: number };
    bed_shape: string;
    printable_area_mm?: number[][] | null;
    excluded_areas_mm: number[][][];
    min_layer_height_mm: number | null;
    max_layer_height_mm: number | null;
    printer_structure: string | null;
    extruder_types: string[];
    single_extruder_multi_material_profile: boolean | null;
    chamber_temperature_control_profile: boolean | null;
  }[];
};
type Catalog = {
  printers: PrinterProfile[];
  source: { name: string; repository: string; license: string };
};

const colors = [
  ['Silver', '#9ca3af'],
  ['White', '#e5e7eb'],
  ['Charcoal', '#374151'],
  ['Ocean', '#0284c7'],
  ['Coral', '#ef6b5b'],
  ['Forest', '#3c8d6b'],
];
const sizeText = (value: number) => value.toFixed(2).replace(/\.00$/, '');
const normalizeSearch = (value: string) =>
  value.normalize('NFKD').toLowerCase().replace(/\p{M}/gu, '');

export default function PrintSettings({
  design,
  onChange,
  busy,
  sourceSize,
  model,
  current,
}: {
  design: DesignSettings;
  onChange: (settings: DesignSettings) => void;
  busy: boolean;
  sourceSize: { width: number; height: number; thickness: number } | null;
  model: ModelResult | null;
  current: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [loading, setLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [search, setSearch] = useState('');
  const searchInput = useRef<HTMLInputElement>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    if (!expanded || catalog) return;
    const controller = new AbortController();
    setLoading(true);
    setCatalogError('');
    const timeout = window.setTimeout(
      () => controller.abort(new DOMException('timed out', 'TimeoutError')),
      15000,
    );
    void fetch('/api/printers', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok)
          throw new Error(
            'The printer catalog is unavailable. You can enter a custom build volume.',
          );
        return (await response.json()) as Catalog;
      })
      .then((result) => {
        if (!Array.isArray(result.printers))
          throw new Error('The printer catalog could not be read.');
        setCatalog(result);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setCatalogError(
            error instanceof Error ? error.message : 'Could not load the printer catalog.',
          );
        else if (controller.signal.reason?.name === 'TimeoutError')
          setCatalogError(
            'The printer catalog took too long. Try again or enter a custom build volume.',
          );
      })
      .finally(() => {
        window.clearTimeout(timeout);
        setLoading(false);
      });
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [expanded, catalog, reload]);

  const selectedPrinter = catalog?.printers.find((item) => item.id === design.printer_id);
  const matchingProfiles =
    selectedPrinter?.profiles.filter((profile) =>
      profile.nozzle_diameters_mm.includes(design.nozzle_mm),
    ) ?? [];
  const selectedProfile = matchingProfiles.length === 1 ? matchingProfiles[0] : null;
  // Like the service's fit check (backend/printing.py), several matching profiles are not
  // ambiguous for bed fit when they all describe the same bed.
  const bedGeometry = (profile: (typeof matchingProfiles)[number]) =>
    JSON.stringify([
      profile.build_volume,
      profile.bed_shape,
      profile.printable_area_mm ?? null,
      profile.excluded_areas_mm,
    ]);
  const sharedBedProfile =
    matchingProfiles.length > 1 && new Set(matchingProfiles.map(bedGeometry)).size === 1
      ? matchingProfiles[0]
      : null;
  const bedProfile = selectedProfile ?? sharedBedProfile;
  const queryTokens = normalizeSearch(search).match(/[\p{L}\p{N}]+/gu) ?? [];
  const matches =
    catalog?.printers.filter((item) =>
      queryTokens.every((token) =>
        normalizeSearch(`${item.manufacturer} ${item.name}`)
          .replace(/[^\p{L}\p{N}]+/gu, '')
          .includes(token),
      ),
    ) ?? [];
  const error = designError(design, sourceSize);
  const tolerance =
    design.detail_mode === 'original'
      ? 0
      : design.nozzle_mm * { draft: 0.5, balanced: 0.25, fine: 0.1 }[design.detail_mode];
  const change = (patch: Partial<DesignSettings>) => onChange({ ...design, ...patch });
  const setNumber = (key: keyof DesignSettings, value: string) => {
    const next = value === '' ? 0 : Number(value);
    if (key === 'nozzle_mm' && selectedPrinter) {
      const volume =
        selectedPrinter.profiles.find((profile) => profile.nozzle_diameters_mm.includes(next))
          ?.build_volume ?? selectedPrinter.build_volume;
      change({
        nozzle_mm: next,
        bed_width_mm: volume.x_mm,
        bed_depth_mm: volume.y_mm,
        bed_height_mm: volume.z_mm,
      });
    } else change({ [key]: next });
  };
  const setBed = (key: keyof DesignSettings, value: string) =>
    change({ [key]: value === '' ? 0 : Number(value), printer_id: 'custom' });
  const printerTitle =
    selectedPrinter?.name ??
    (design.printer_id === 'custom' ? 'Custom printer' : design.printer_id);
  const printedParts = current ? (model?.parts ?? []) : [];
  const fit = current ? model?.print_fit : undefined;
  const splitPlan = current ? model?.split_plan : undefined;

  return (
    <section
      className={`print-settings ${expanded ? 'expanded' : ''}`}
      aria-label="Design and print settings"
    >
      <button
        className="assistant-toggle"
        aria-expanded={expanded}
        aria-controls="print-settings-content"
        onClick={() => setExpanded(!expanded)}
      >
        <SlidersHorizontal size={23} />
        <span className="assistant-title">Design &amp; print</span>
        <span className="assistant-toggle-hint">Size, appearance, parts and printer fit</span>
        <span className="assistant-local-label">
          {design.output_mode === 'single'
            ? 'Single part'
            : `${design.split_columns} × ${design.split_rows} split grid`}
        </span>
        <CaretDown size={19} className="assistant-chevron" />
      </button>
      <div id="print-settings-content" hidden={!expanded}>
        <div className="print-settings-content">
          <p className="print-intro">
            Start with your measured part, then choose the version you want to make. Review changes
            in a fresh build before exporting.
          </p>
          <div className="print-settings-grid">
            <fieldset disabled={busy} className="print-group">
              <legend>Size &amp; appearance</legend>
              <div className="print-two-fields">
                <label>
                  XY scale (%)
                  <input
                    type="number"
                    min="10"
                    max="400"
                    step="1"
                    value={design.scale_percent || ''}
                    onChange={(event) => setNumber('scale_percent', event.target.value)}
                  />
                </label>
                <label>
                  Thickness scale (%)
                  <input
                    type="number"
                    min="10"
                    max="400"
                    step="1"
                    value={design.thickness_percent || ''}
                    onChange={(event) => setNumber('thickness_percent', event.target.value)}
                  />
                </label>
              </div>
              <p className="print-field-note">
                100% keeps your measured size. Original width and thickness stay in the main
                controls.
              </p>
              {sourceSize && (
                <p className="print-target-size">
                  <span>Requested size</span>
                  <strong>
                    {sizeText((sourceSize.width * design.scale_percent) / 100)} ×{' '}
                    {sizeText((sourceSize.height * design.scale_percent) / 100)} ×{' '}
                    {sizeText((sourceSize.thickness * design.thickness_percent) / 100)} mm
                  </strong>
                  <span>width × height × thickness</span>
                </p>
              )}
              <div className="print-two-fields appearance-fields">
                <label>
                  Model color
                  <input
                    type="color"
                    value={design.color}
                    onChange={(event) => change({ color: event.target.value })}
                  />
                </label>
                <label>
                  Material
                  <select
                    value={design.material}
                    onChange={(event) =>
                      change({ material: event.target.value as DesignSettings['material'] })
                    }
                  >
                    {['pla', 'petg', 'abs', 'asa', 'tpu', 'nylon'].map((material) => (
                      <option key={material} value={material}>
                        {material.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="print-color-swatches" aria-label="Color presets">
                {colors.map(([name, color]) => (
                  <button
                    type="button"
                    key={name}
                    style={{ background: color }}
                    aria-label={`${name} color`}
                    aria-pressed={design.color.toLowerCase() === color}
                    onClick={() => change({ color })}
                  >
                    {design.color.toLowerCase() === color && <span aria-hidden="true">✓</span>}
                  </button>
                ))}
              </div>
              <p className="print-field-note">
                Color previews immediately. Color and material are saved planning metadata; STEP,
                STL and DXF do not assign filament or slicer settings.
              </p>
            </fieldset>

            <fieldset disabled={busy} className="print-group">
              <legend>Detail &amp; parts</legend>
              <div className="print-two-fields">
                <label>
                  Nozzle diameter (mm)
                  <input
                    type="number"
                    min="0.1"
                    max="8"
                    step="0.05"
                    value={design.nozzle_mm || ''}
                    onChange={(event) => setNumber('nozzle_mm', event.target.value)}
                  />
                </label>
                <label>
                  Geometry detail
                  <select
                    value={design.detail_mode}
                    onChange={(event) =>
                      change({ detail_mode: event.target.value as DesignSettings['detail_mode'] })
                    }
                  >
                    <option value="original">Original outline</option>
                    <option value="draft">Draft</option>
                    <option value="balanced">Balanced</option>
                    <option value="fine">Fine</option>
                  </select>
                </label>
              </div>
              <p className="print-field-note">
                {tolerance === 0
                  ? 'Original keeps the traced outline. Other modes simplify actual geometry relative to the nozzle diameter.'
                  : `${design.detail_mode === 'fine' ? 'Fine' : design.detail_mode === 'draft' ? 'Draft' : 'Balanced'} simplifies the outline with ${tolerance.toFixed(3)} mm tolerance. Inspect small holes and edges after building.`}
              </p>
              <label>
                Output
                <select
                  value={design.output_mode}
                  onChange={(event) =>
                    change({ output_mode: event.target.value as DesignSettings['output_mode'] })
                  }
                >
                  <option value="single">Single part</option>
                  <option value="split">Split into parts</option>
                </select>
              </label>
              {design.output_mode === 'split' && (
                <div className="print-two-fields print-split-fields">
                  <label>
                    Columns
                    <input
                      type="number"
                      min="1"
                      max="4"
                      step="1"
                      value={design.split_columns || ''}
                      onChange={(event) => setNumber('split_columns', event.target.value)}
                    />
                  </label>
                  <label>
                    Rows
                    <input
                      type="number"
                      min="1"
                      max="4"
                      step="1"
                      value={design.split_rows || ''}
                      onChange={(event) => setNumber('split_rows', event.target.value)}
                    />
                  </label>
                </div>
              )}
              <p className="print-field-note">
                {design.output_mode === 'split'
                  ? 'A grid of up to 8 cells makes straight cuts through the solid. No joints or connectors are added. Preview shows the assembled positions; Parts ZIP includes separate STEP and STL files.'
                  : 'Build one solid from the outline. Split output can divide a large part into separate files for smaller printer beds.'}
              </p>
            </fieldset>
          </div>

          <fieldset disabled={busy} className="print-group printer-group">
            <legend>
              <Printer size={20} /> Printer &amp; build volume
            </legend>
            <div className="printer-picker">
              <div className="printer-search-field">
                <label htmlFor="printer-search">Search printers</label>
                <span className="printer-search-input">
                  <input
                    ref={searchInput}
                    id="printer-search"
                    type="search"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Brand or model, such as Prusa or Ender"
                    aria-describedby="printer-search-status printer-search-help"
                    aria-controls="printer-model"
                    autoComplete="off"
                    spellCheck={false}
                  />
                  {search && (
                    <button
                      type="button"
                      className="printer-search-clear"
                      aria-label="Clear printer search"
                      onClick={() => {
                        setSearch('');
                        searchInput.current?.focus();
                      }}
                    >
                      <X size={17} aria-hidden="true" />
                    </button>
                  )}
                </span>
              </div>
              <label>
                Printer model
                <select
                  id="printer-model"
                  value={design.printer_id}
                  onChange={(event) => {
                    const printer = catalog?.printers.find(
                      (item) => item.id === event.target.value,
                    );
                    if (!printer) {
                      change({ printer_id: 'custom' });
                      return;
                    }
                    const nozzle = printer.nozzle_diameters_mm.includes(0.4)
                      ? 0.4
                      : printer.default_nozzle_mm;
                    const volume =
                      printer.profiles.find((profile) =>
                        profile.nozzle_diameters_mm.includes(nozzle),
                      )?.build_volume ?? printer.build_volume;
                    change({
                      printer_id: printer.id,
                      nozzle_mm: nozzle,
                      bed_width_mm: volume.x_mm,
                      bed_depth_mm: volume.y_mm,
                      bed_height_mm: volume.z_mm,
                    });
                  }}
                >
                  <option value="custom">Custom printer — enter dimensions</option>
                  {design.printer_id !== 'custom' &&
                    !matches.some((item) => item.id === design.printer_id) && (
                      <option value={design.printer_id}>{printerTitle} (selected)</option>
                    )}
                  {matches.map((printer) => (
                    <option key={printer.id} value={printer.id}>
                      {printer.manufacturer} · {printer.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p id="printer-search-help" className="print-field-note printer-search-help">
              Search narrows the model list below. Your selected printer stays selected until you
              choose another model or edit its dimensions.
            </p>
            <div className="printer-catalog-status">
              <span id="printer-search-status" role="status" aria-atomic="true">
                {loading ? (
                  <>
                    <SpinnerGap size={15} className="spinner" /> Loading printer catalog…
                  </>
                ) : catalog ? (
                  <>
                    {matches.length} matching models · {catalog.printers.length} in the catalog
                  </>
                ) : (
                  'Custom dimensions are always available.'
                )}
              </span>
              {catalogError && (
                <>
                  <p role="status">{catalogError}</p>
                  <button className="text-button" onClick={() => setReload(reload + 1)}>
                    Retry printer catalog
                  </button>
                </>
              )}
            </div>
            {catalog && queryTokens.length > 0 && matches.length === 0 && (
              <p className="printer-search-empty">
                <strong>No printers match “{search.trim()}”.</strong> Try a shorter brand or model
                name, or choose Custom printer and enter your build volume below.
                {design.printer_id !== 'custom' && (
                  <span>Your current selection, {printerTitle}, is still selected.</span>
                )}
              </p>
            )}
            <div className="printer-dimensions">
              <label>
                Bed width (mm)
                <input
                  type="number"
                  min="20"
                  max="5000"
                  step="1"
                  value={design.bed_width_mm || ''}
                  onChange={(event) => setBed('bed_width_mm', event.target.value)}
                />
              </label>
              <label>
                Bed depth (mm)
                <input
                  type="number"
                  min="20"
                  max="5000"
                  step="1"
                  value={design.bed_depth_mm || ''}
                  onChange={(event) => setBed('bed_depth_mm', event.target.value)}
                />
              </label>
              <label>
                Build height (mm)
                <input
                  type="number"
                  min="20"
                  max="5000"
                  step="1"
                  value={design.bed_height_mm || ''}
                  onChange={(event) => setBed('bed_height_mm', event.target.value)}
                />
              </label>
              <label>
                Bed margin (mm)
                <input
                  type="number"
                  min="0"
                  max="30"
                  step="1"
                  value={design.bed_margin_mm}
                  onChange={(event) => setNumber('bed_margin_mm', event.target.value)}
                />
              </label>
            </div>
            <p className="print-field-note">
              Margin reserves space on each side of the bed. Editing width, depth or height switches
              to Custom. Fit checks search all XY turns on a clear rectangular bed.
            </p>
            {selectedPrinter && (
              <details className="printer-facts">
                <summary>Profile facts for {selectedPrinter.name}</summary>
                <p>
                  Listed nozzle profiles:{' '}
                  {selectedPrinter.nozzle_diameters_mm.map((value) => `${value} mm`).join(', ') ||
                    'not specified'}
                  .
                </p>
                {selectedProfile ? (
                  <dl>
                    <div>
                      <dt>Selected nozzle profile</dt>
                      <dd>{selectedProfile.name}</dd>
                    </div>
                    <div>
                      <dt>Bed shape</dt>
                      <dd>{selectedProfile.bed_shape}</dd>
                    </div>
                    <div>
                      <dt>Declared layer heights</dt>
                      <dd>
                        {selectedProfile.min_layer_height_mm !== null &&
                        selectedProfile.max_layer_height_mm !== null
                          ? `${selectedProfile.min_layer_height_mm}–${selectedProfile.max_layer_height_mm} mm`
                          : 'Not specified'}
                      </dd>
                    </div>
                    <div>
                      <dt>Printer structure</dt>
                      <dd>{selectedProfile.printer_structure || 'Not specified'}</dd>
                    </div>
                    <div>
                      <dt>Extruder types</dt>
                      <dd>{selectedProfile.extruder_types.join(', ') || 'Not specified'}</dd>
                    </div>
                    <div>
                      <dt>Single-extruder multi-material profile flag</dt>
                      <dd>
                        {selectedProfile.single_extruder_multi_material_profile === null
                          ? 'Not specified'
                          : selectedProfile.single_extruder_multi_material_profile
                            ? 'Enabled in this profile'
                            : 'Not enabled in this profile'}
                      </dd>
                    </div>
                    <div>
                      <dt>Chamber temperature control profile flag</dt>
                      <dd>
                        {selectedProfile.chamber_temperature_control_profile === null
                          ? 'Not specified'
                          : selectedProfile.chamber_temperature_control_profile
                            ? 'Enabled in this profile'
                            : 'Not enabled in this profile'}
                      </dd>
                    </div>
                  </dl>
                ) : (
                  <p>
                    {sharedBedProfile
                      ? `${matchingProfiles.length} profiles match this nozzle. They describe the same ${sharedBedProfile.bed_shape} bed, which the build-volume check uses; their other slicer settings may differ, so check the profile you print with.`
                      : matchingProfiles.length
                        ? 'More than one profile matches this nozzle, with different beds. The build-volume check needs manual review.'
                        : 'No exact profile matches this nozzle. Check your printer hardware and slicer profile.'}
                  </p>
                )}
                <p>
                  Enclosure, hotend temperature limits, automatic bed leveling and automatic
                  multi-material hardware are not established by this catalog. Profile flags
                  describe slicer settings, not verified hardware. Check your exact printer and
                  material requirements.
                </p>
                {((bedProfile?.bed_shape ?? selectedPrinter.bed_shape) !== 'rectangular' ||
                  (bedProfile?.excluded_areas_mm ?? selectedPrinter.excluded_areas_mm)?.length >
                    0) && (
                  <p>
                    This profile has a shaped bed or excluded areas. Automatic fit may be unknown;
                    check placement in your slicer.
                  </p>
                )}
                {(selectedProfile
                  ? [selectedProfile]
                  : matchingProfiles.length
                    ? matchingProfiles
                    : selectedPrinter.profiles.slice(0, 1)
                ).map((profile) => (
                  <a key={profile.name} href={profile.source_url} target="_blank" rel="noreferrer">
                    View source: {profile.name} <ArrowSquareOut size={14} />
                  </a>
                ))}
              </details>
            )}
            {catalog && (
              <p className="printer-source">
                Profiles from {catalog.source.name}. They are planning references, not printer
                certification.
              </p>
            )}
          </fieldset>

          <div
            className={`print-fit-summary ${fit?.status === 'too_large' ? 'fit-too-large' : ''}`}
            role="status"
          >
            {fit?.status === 'fits' ? (
              <CheckCircle size={19} />
            ) : fit?.status === 'too_large' ? (
              <WarningCircle size={19} />
            ) : (
              <Info size={19} />
            )}
            <div>
              <strong>
                {!current
                  ? 'Build to check printer fit'
                  : fit?.status === 'fits'
                    ? 'Built parts fit the selected build volume'
                    : fit?.status === 'too_large'
                      ? 'A built part exceeds the selected build volume'
                      : 'Printer fit needs review'}
              </strong>
              <p>
                {current
                  ? (fit?.reason ?? 'Choose a printer and build the model to check fit.')
                  : 'The current settings have not been built. Previous geometry and fit results do not describe these changes.'}
              </p>
            </div>
          </div>
          {splitPlan && (
            <section className="split-plan-card" aria-label="Suggested split plan">
              <strong>
                {splitPlan.status === 'suggested'
                  ? `Try a ${splitPlan.columns} × ${splitPlan.rows} split · ${splitPlan.piece_count} pieces`
                  : 'A fitting split needs another plan'}
              </strong>
              <p>{splitPlan.reason}</p>
              {splitPlan.status === 'suggested' && (
                <>
                  <p>
                    Each proposed piece fits separately with the selected margin and a checked XY
                    turn. Apply the cut settings, then rebuild to generate and inspect the pieces.
                    Your measured size stays the same. Straight cuts add no joints or clearance.
                  </p>
                  <button
                    type="button"
                    className="text-button"
                    disabled={busy}
                    onClick={() =>
                      change({
                        output_mode: 'split',
                        split_columns: splitPlan.columns,
                        split_rows: splitPlan.rows,
                      })
                    }
                  >
                    Use suggested split
                  </button>
                </>
              )}
            </section>
          )}
          {printedParts.length > 0 && (
            <div className="print-parts-table">
              <table>
                <caption>Built parts · dimensions in millimeters</caption>
                <thead>
                  <tr>
                    <th>Part</th>
                    <th>Width × height × thickness</th>
                    <th>Printer fit</th>
                  </tr>
                </thead>
                <tbody>
                  {printedParts.map((part) => (
                    <tr key={part.id}>
                      <th scope="row">{part.name}</th>
                      <td>
                        {sizeText(part.dimensions.width)} × {sizeText(part.dimensions.height)} ×{' '}
                        {sizeText(part.dimensions.thickness)}
                      </td>
                      <td>
                        <details className="part-placement">
                          <summary>
                            {part.bed_fit.status === 'fits'
                              ? `Fits${part.bed_fit.rotation_deg ? ` after ≈${part.bed_fit.rotation_deg.toFixed(6).replace(/\.?0+$/, '')}° turn` : ''}`
                              : part.bed_fit.status === 'too_large'
                                ? 'Too large'
                                : 'Check in slicer'}
                          </summary>
                          <p>{part.bed_fit.reason}</p>
                          {part.bed_fit.footprint_mm && (
                            <p>
                              {part.bed_fit.basis === 'curve_envelope'
                                ? 'Conservative rotated footprint: '
                                : 'Rotated footprint: '}
                              {sizeText(part.bed_fit.footprint_mm.width)} ×{' '}
                              {sizeText(part.bed_fit.footprint_mm.depth)} mm.
                              {part.bed_fit.basis === 'bounding_box'
                                ? ' Uses the enclosing rectangle of the fitted curves.'
                                : part.bed_fit.basis === 'curve_envelope'
                                  ? ' Uses an outer enclosure of the fitted curves.'
                                  : ' Uses the built polygon outline.'}
                            </p>
                          )}
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {error && (
            <p className="print-validation" role="alert">
              {error}
            </p>
          )}
          <div className="print-footer">
            <p>
              Turns are suggestions for individual pieces; exports keep their original orientation.
              No toolpaths, supports, temperatures or strength guarantees are generated.
            </p>
            <button
              className="text-button"
              disabled={busy}
              onClick={() => onChange({ ...DEFAULT_DESIGN })}
            >
              Reset design &amp; print
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
