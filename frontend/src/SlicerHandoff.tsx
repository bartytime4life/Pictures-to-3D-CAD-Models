import { useEffect, useRef, useState } from 'react';
import {
  ArrowSquareOut,
  CheckCircle,
  Cube,
  DownloadSimple,
  Info,
  Printer,
  SpinnerGap,
} from '@phosphor-icons/react';
import type { ModelResult, SlicerDiscovery, SlicerId, SlicerLaunch } from './types';
import './SlicerHandoff.css';

const targets = [
  {
    id: 'bambu' as const,
    name: 'Bambu Studio',
    version: '2.9.1',
    release: 'https://github.com/bambulab/BambuStudio/releases/tag/v02.09.01.70',
  },
  {
    id: 'prusa' as const,
    name: 'PrusaSlicer',
    version: '2.9.7',
    release: 'https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.9.7',
  },
];

export default function SlicerHandoff({
  model,
  selected,
  onSelect,
  downloading,
  onDownload,
  onLaunch,
}: {
  model: ModelResult;
  selected: SlicerId;
  onSelect: (id: SlicerId) => void;
  downloading: string | null;
  onDownload: (id: SlicerId) => void;
  onLaunch: (id: SlicerId) => Promise<SlicerLaunch>;
}) {
  const [discovery, setDiscovery] = useState<SlicerDiscovery | null>(null);
  const [checking, setChecking] = useState(true);
  const [discoveryError, setDiscoveryError] = useState('');
  const [reload, setReload] = useState(0);
  const [launching, setLaunching] = useState(false);
  const [launchMessage, setLaunchMessage] = useState('');
  const [launchError, setLaunchError] = useState('');
  const launchPending = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 10000);
    let active = true;
    setChecking(true);
    setDiscoveryError('');
    void fetch('/api/slicers', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('unavailable');
        return (await response.json()) as SlicerDiscovery;
      })
      .then((result) => {
        if (active) setDiscovery(result);
      })
      .catch(() => {
        if (active) {
          setDiscovery(null);
          setDiscoveryError('Could not check this computer. Your handoff downloads are available.');
        }
      })
      .finally(() => {
        window.clearTimeout(timer);
        if (active) setChecking(false);
      });
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [reload]);

  const target = targets.find((item) => item.id === selected)!;
  const program = discovery?.programs.find((item) => item.id === selected);
  const count = model.parts?.length || 1;
  const ready = !!model.downloads[selected];
  const disabled = !!downloading || launching;

  async function openSlicer() {
    if (disabled || launchPending.current || !program?.launch_available || !ready) return;
    launchPending.current = true;
    setLaunching(true);
    setLaunchMessage('');
    setLaunchError('');
    try {
      const result = await onLaunch(selected);
      if (mounted.current)
        setLaunchMessage(
          `${result.name}: launch requested. Check the application to confirm import.`,
        );
    } catch (error) {
      if (mounted.current)
        setLaunchError(
          error instanceof Error
            ? error.message
            : 'Could not open the slicer. Download the handoff ZIP instead.',
        );
    } finally {
      launchPending.current = false;
      if (mounted.current) setLaunching(false);
    }
  }

  return (
    <section className="slicer-handoff" aria-labelledby="slicer-handoff-title">
      <div className="slicer-heading">
        <span className="slicer-heading-icon" aria-hidden="true">
          <Printer size={24} />
        </span>
        <div>
          <p className="slicer-eyebrow">NEXT · PRINT PREPARATION</p>
          <h3 id="slicer-handoff-title">Prepare in your slicer</h3>
        </div>
      </div>
      <p className="slicer-intro">
        Take the built part and its measurement notes into your preferred slicer.
      </p>
      <fieldset className="slicer-choices" disabled={disabled}>
        <legend>Choose a slicer</legend>
        {targets.map((item) => (
          <label
            className={`slicer-choice ${selected === item.id ? 'is-selected' : ''}`}
            key={item.id}
          >
            <input
              type="radio"
              name="slicer"
              value={item.id}
              checked={selected === item.id}
              onChange={() => {
                onSelect(item.id);
                setLaunchMessage('');
                setLaunchError('');
              }}
            />
            <span>
              <strong>{item.name}</strong>
              <small>Target release {item.version}</small>
            </span>
            {selected === item.id && <CheckCircle size={20} aria-hidden="true" />}
          </label>
        ))}
      </fieldset>

      <div className="slicer-package">
        <div className="slicer-package-title">
          <Cube size={22} aria-hidden="true" />
          <strong>{count === 1 ? 'One built object' : `${count} separate built objects`}</strong>
          <span>3MF + notes</span>
        </div>
        <p>
          Geometry uses millimeters.
          {count > 1
            ? ' Split pieces stay separate so you can arrange them on the bed.'
            : ' Verify the imported dimensions before slicing.'}
        </p>
        {model.design && (
          <p className="slicer-plan">
            Your plan: {model.design.material.toUpperCase()} · {model.design.nozzle_mm} mm nozzle ·{' '}
            {model.design.bed_width_mm} × {model.design.bed_depth_mm} mm bed
          </p>
        )}
        <button
          className="primary-button slicer-download"
          disabled={disabled || !ready}
          onClick={() => onDownload(selected)}
        >
          {downloading === selected ? (
            <SpinnerGap className="spinner" size={20} />
          ) : (
            <DownloadSimple size={20} />
          )}
          {downloading === selected
            ? 'Downloading handoff…'
            : `Download ${target.name} handoff ZIP`}
        </button>
        <p className="slicer-unpack">
          Unzip the package, open its 3MF in {target.name}, then follow the included notes.
        </p>
      </div>

      <div className="slicer-local">
        <div className="slicer-local-status" role="status" aria-live="polite">
          {checking ? (
            <>
              <SpinnerGap size={16} className="spinner" /> Checking this computer…
            </>
          ) : discoveryError ? (
            discoveryError
          ) : program ? (
            <>
              <span
                className={`slicer-status-dot ${program.detected ? 'is-detected' : ''}`}
                aria-hidden="true"
              />
              {program.detected
                ? `${target.name} found · installed version not checked`
                : `${target.name} not found on this computer`}
            </>
          ) : (
            'Local application status is unavailable.'
          )}
        </div>
        {!checking && program && <p className="slicer-launch-reason">{program.launch_reason}</p>}
        {!checking && program?.launch_available && (
          <button
            className="outlined-button slicer-open"
            disabled={disabled || !ready}
            onClick={() => void openSlicer()}
          >
            {launching ? (
              <SpinnerGap size={18} className="spinner" />
            ) : (
              <ArrowSquareOut size={18} />
            )}
            {launching ? 'Requesting launch…' : `Open in ${target.name}`}
          </button>
        )}
        {discoveryError && (
          <button className="text-button" onClick={() => setReload((value) => value + 1)}>
            Check again
          </button>
        )}
        {launchMessage && (
          <p className="slicer-launch-message" role="status">
            {launchMessage}
          </p>
        )}
        {launchError && (
          <p className="slicer-launch-error" role="alert">
            {launchError}
          </p>
        )}
        <a
          className="slicer-release"
          href={program?.release_url || target.release}
          target="_blank"
          rel="noreferrer"
        >
          {target.name} {program?.target_version || target.version} release &amp; downloads{' '}
          <ArrowSquareOut size={14} aria-hidden="true" />
        </a>
      </div>
      <div className="slicer-review">
        <Info size={19} aria-hidden="true" />
        <p>
          Choose and review your printer, nozzle, material, placement and supports in the native
          slicer. No print preset is embedded. Opening a slicer does not start a print.
        </p>
      </div>
    </section>
  );
}
