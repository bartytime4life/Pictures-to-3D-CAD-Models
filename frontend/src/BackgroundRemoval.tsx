import { useEffect, useRef, useState } from 'react';
import { DownloadSimple, MagicWand, SpinnerGap } from '@phosphor-icons/react';
import { createBackgroundCutout } from './background';
import type { TraceResult } from './types';
import './BackgroundRemoval.css';

export type BackgroundPreview = { trace: TraceResult; dataUrl: string };

export default function BackgroundRemoval({
  trace,
  name,
  disabled = false,
  onPreviewChange,
}: {
  trace: TraceResult | null;
  name: string;
  disabled?: boolean;
  onPreviewChange: (preview: BackgroundPreview | null) => void;
}) {
  const [cutout, setCutout] = useState<BackgroundPreview | null>(null);
  const [removed, setRemoved] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const currentTrace = useRef(trace);
  currentTrace.current = trace;
  const onPreview = useRef(onPreviewChange);
  onPreview.current = onPreviewChange;
  const controller = useRef<AbortController | null>(null);
  const ownedUrl = useRef<string | null>(null);
  const active = cutout?.trace === trace ? cutout : null;

  useEffect(() => {
    setCutout(null);
    setRemoved(false);
    setProcessing(false);
    setError('');
    onPreview.current(null);
    return () => {
      controller.current?.abort();
      if (ownedUrl.current) URL.revokeObjectURL(ownedUrl.current);
      ownedUrl.current = null;
    };
  }, [trace]);

  async function removeBackground() {
    if (!trace || disabled || processing) return;
    const source = trace;
    const request = new AbortController();
    controller.current?.abort();
    controller.current = request;
    setProcessing(true);
    setError('');
    try {
      const blob = await createBackgroundCutout(source, request.signal);
      if (request.signal.aborted || currentTrace.current !== source) return;
      const dataUrl = URL.createObjectURL(blob);
      if (ownedUrl.current) URL.revokeObjectURL(ownedUrl.current);
      ownedUrl.current = dataUrl;
      const result = { trace: source, dataUrl };
      setCutout(result);
      setRemoved(true);
      onPreview.current(result);
    } catch (reason) {
      if (!request.signal.aborted && currentTrace.current === source)
        setError(
          reason instanceof Error ? reason.message : 'Background removal failed. Try again.',
        );
    } finally {
      if (!request.signal.aborted && currentTrace.current === source) setProcessing(false);
    }
  }

  function showCutout(value: boolean) {
    setRemoved(value);
    onPreview.current(value ? active : null);
  }

  if (!trace?.image.data_url) return null;
  const filename = `${name.replace(/[^a-zA-Z0-9_-]+/g, '-').slice(0, 60) || 'part'}-transparent.png`;

  return (
    <div className="background-removal" aria-label="Photo background">
      <div className="background-actions">
        {active ? (
          <div className="background-toggle" role="group" aria-label="Background preview">
            <button
              type="button"
              aria-pressed={!removed}
              disabled={disabled}
              onClick={() => showCutout(false)}
            >
              Original
            </button>
            <button
              type="button"
              aria-pressed={removed}
              disabled={disabled}
              onClick={() => showCutout(true)}
            >
              Background removed
            </button>
          </div>
        ) : (
          <button
            className="text-button"
            type="button"
            disabled={disabled || processing}
            onClick={() => void removeBackground()}
          >
            {processing ? <SpinnerGap size={18} className="spinner" /> : <MagicWand size={18} />}
            {processing ? 'Removing background…' : 'Remove background'}
          </button>
        )}
        {active && (
          <a className="background-download" href={active.dataUrl} download={filename}>
            <DownloadSimple size={17} aria-hidden="true" />
            Save transparent PNG
          </a>
        )}
      </div>
      <p className="background-hint">
        {active
          ? `${trace.image.width} × ${trace.image.height} px · Through holes stay transparent. Your original photo is kept.`
          : 'Optional: cut out the part using the current outline. Adjust the outline first if needed.'}
      </p>
      {error && (
        <p className="background-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
