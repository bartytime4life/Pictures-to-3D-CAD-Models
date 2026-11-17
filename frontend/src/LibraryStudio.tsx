import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, ReactNode } from 'react';
import {
  ArrowLeft,
  ArrowsClockwise,
  CaretRight,
  CheckCircle,
  Copy,
  Cpu,
  DownloadSimple,
  FolderOpen,
  FolderPlus,
  House,
  Images,
  MagnifyingGlass,
  Mountains,
  Ruler,
  SpinnerGap,
  Star,
  Trash,
  UploadSimple,
  WarningCircle,
  X,
} from '@phosphor-icons/react';
import AppHeader from './AppHeader';
import { useStudioActive } from './StudioActivity';
import { handOff } from './handoff';
import type { HandoffTarget } from './handoff';
import {
  MAX_FILE,
  PAGE,
  PHOTO_NAME,
  SORTS,
  STAGES,
  blurOf,
  count,
  duration,
  megabytes,
  megapixels,
  previewUrl,
  request,
  send,
  taken,
} from './library';
import type {
  FolderListing,
  LibraryGroup,
  LibraryPhoto,
  LibraryPhotoDetail,
  LibrarySort,
  LibraryState,
  LibraryView,
} from './library';
import './LibraryStudio.css';

const CELL_MIN = 168;
const GAP = 10;
const CAPTION = 44;
const MIME: Record<string, string> = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
  heic: 'image/heic',
  heif: 'image/heif',
  avif: 'image/avif',
};

type Similar = { title: string; photos: LibraryPhoto[]; model: string };
type Filter = { kind: 'group' | 'dup'; id: number; size: number } | null;

function errorText(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong. Try again.';
}

/** One number of the summary strip. */
function Stat({ value, label, hint }: { value: string; label: string; hint?: string }) {
  return (
    <div className="library-stat" title={hint}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

/**
 * A grid that draws only the rows on screen, so a library of any size scrolls the same.
 * Photos are addressed by position; positions not loaded yet show a placeholder and are
 * requested through `need`.
 */
function PhotoGrid({
  total,
  photoAt,
  need,
  selected,
  onSelect,
  resetKey,
}: {
  total: number;
  photoAt: (index: number) => LibraryPhoto | undefined;
  need: (first: number, last: number) => void;
  selected: number | null;
  onSelect: (photo: LibraryPhoto) => void;
  resetKey: string;
}) {
  const box = useRef<HTMLDivElement>(null);
  const inner = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 600 });
  const [scroll, setScroll] = useState(0);

  useEffect(() => {
    const element = box.current;
    const content = inner.current;
    if (!element || !content) return;
    // The cells are laid out across the inner width (inside the padding and beside the
    // scrollbar), so that is what is measured, and watched: it changes when the detail
    // panel opens.
    const measure = () => setSize({ width: content.clientWidth, height: element.clientHeight });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    observer.observe(content);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (box.current) box.current.scrollTop = 0;
    setScroll(0);
  }, [resetKey]);

  const columns = Math.max(2, Math.floor((size.width + GAP) / (CELL_MIN + GAP)));
  const cell = Math.max(60, (size.width - GAP * (columns - 1)) / columns);
  const rowHeight = cell + CAPTION + GAP;
  const rows = Math.ceil(total / columns);
  const firstRow = Math.max(0, Math.floor(scroll / rowHeight) - 2);
  const lastRow = Math.min(rows - 1, Math.ceil((scroll + size.height) / rowHeight) + 2);
  const first = firstRow * columns;
  const last = Math.min(total, (lastRow + 1) * columns);

  useEffect(() => {
    if (size.width > 0 && last > first) need(first, last);
  }, [first, last, need, size.width]);

  const cells: ReactNode[] = [];
  for (let index = first; index < last; index++) {
    const photo = photoAt(index);
    const style = {
      left: (index % columns) * (cell + GAP),
      top: Math.floor(index / columns) * rowHeight,
      width: cell,
      height: cell + CAPTION,
    };
    if (!photo) {
      cells.push(<div key={`wait-${index}`} className="library-cell waiting" style={style} />);
      continue;
    }
    const blur = blurOf(photo);
    cells.push(
      <button
        key={photo.id}
        type="button"
        className="library-cell"
        style={style}
        aria-pressed={selected === photo.id}
        aria-label={`${photo.name}${photo.best ? ', best shot of its group' : ''}`}
        onClick={() => onSelect(photo)}
      >
        <span className="library-thumb">
          {photo.state === 'ready' ? (
            <img
              src={previewUrl(photo.id)}
              alt=""
              loading="lazy"
              decoding="async"
              draggable={false}
            />
          ) : photo.state === 'failed' ? (
            <WarningCircle size={30} aria-hidden />
          ) : (
            <span className="library-pending" />
          )}
          {photo.best && (
            <span className="library-badge best">
              <Star size={13} weight="fill" aria-hidden /> Best
            </span>
          )}
          {photo.dup_kind && (
            <span className="library-badge copy">
              {photo.dup_kind === 'exact' ? 'Copy' : 'Look-alike'}
            </span>
          )}
          {photo.score != null && (
            <span className="library-badge score">{Math.round(photo.score * 100)}%</span>
          )}
        </span>
        <span className="library-caption">
          <span className="library-name">{photo.name}</span>
          <span className="library-meta">
            {blur != null
              ? `${blur.toFixed(1)} px blur`
              : photo.state === 'failed'
                ? 'Not read'
                : ''}
          </span>
        </span>
      </button>,
    );
  }

  return (
    <div
      ref={box}
      className="library-grid"
      onScroll={(event) => setScroll(event.currentTarget.scrollTop)}
      role="group"
      aria-label={`${count(total)} photos`}
    >
      <div
        ref={inner}
        className="library-grid-inner"
        style={{ height: Math.max(rows * rowHeight - GAP, 0) }}
      >
        {cells}
      </div>
    </div>
  );
}

/** The preview with the model's subject lit and the rest dimmed. */
function SubjectView({ detail, show }: { detail: LibraryPhotoDetail; show: boolean }) {
  const subject = detail.subject;
  const runs = useMemo(() => {
    const found: { x: number; y: number; width: number }[] = [];
    subject?.rows.forEach((line, y) => {
      for (let x = 0; x < line.length;) {
        if (line[x] !== '1') {
          x++;
          continue;
        }
        let end = x;
        while (end < line.length && line[end] === '1') end++;
        found.push({ x, y, width: end - x });
        x = end;
      }
    });
    return found;
  }, [subject]);
  const lit = show && subject && runs.length > 0;
  return (
    <div className="library-preview">
      <img src={previewUrl(detail.id)} alt={`Preview of ${detail.name}`} />
      {lit && (
        <svg
          viewBox={`0 0 ${subject.grid} ${subject.grid}`}
          preserveAspectRatio="none"
          aria-hidden
          data-testid="subject-overlay"
        >
          <defs>
            <filter id={`soft-${detail.id}`}>
              <feGaussianBlur stdDeviation="0.45" />
            </filter>
            <mask id={`lit-${detail.id}`}>
              <rect width={subject.grid} height={subject.grid} fill="#fff" />
              <g filter={`url(#soft-${detail.id})`}>
                {runs.map((run) => (
                  <rect
                    key={`${run.x}-${run.y}`}
                    x={run.x}
                    y={run.y}
                    width={run.width}
                    height={1.02}
                  />
                ))}
              </g>
            </mask>
          </defs>
          <rect
            width={subject.grid}
            height={subject.grid}
            fill="#0b0f12"
            opacity="0.66"
            mask={`url(#lit-${detail.id})`}
          />
          {detail.box && (
            <rect
              x={detail.box[0] * subject.grid}
              y={detail.box[1] * subject.grid}
              width={(detail.box[2] - detail.box[0]) * subject.grid}
              height={(detail.box[3] - detail.box[1]) * subject.grid}
              fill="none"
              stroke="#27c9ef"
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
      )}
    </div>
  );
}

export default function LibraryStudio() {
  const active = useStudioActive();
  const activeRef = useRef(active);
  activeRef.current = active;
  const [state, setState] = useState<LibraryState | null>(null);
  const [offline, setOffline] = useState('');
  const [view, setView] = useState<LibraryView>('all');
  const [sort, setSort] = useState<LibrarySort>('added');
  const [typed, setTyped] = useState('');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<Filter>(null);
  const [similar, setSimilar] = useState<Similar | null>(null);
  const [revision, setRevision] = useState(0);
  const [pages, setPages] = useState<Map<number, LibraryPhoto[]>>(new Map());
  const [total, setTotal] = useState(0);
  const [groups, setGroups] = useState<LibraryGroup[]>([]);
  const [groupTotal, setGroupTotal] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<LibraryPhotoDetail | null>(null);
  const [showSubject, setShowSubject] = useState(true);
  const [picker, setPicker] = useState<FolderListing | null>(null);
  const [pickerPath, setPickerPath] = useState('');
  const [pickerError, setPickerError] = useState('');
  const [uploading, setUploading] = useState<{ done: number; total: number } | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [dragging, setDragging] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const pickerDialog = useRef<HTMLDialogElement>(null);
  const clearDialog = useRef<HTMLDialogElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const loading = useRef(new Set<number>());
  const wasRunning = useRef(false);

  const running = !!state?.job.running;
  const summary = state?.summary;
  const vision = state?.vision;
  const listKey = `${view}|${sort}|${query}|${filter?.kind ?? ''}${filter?.id ?? ''}|${revision}`;
  const listKeyRef = useRef(listKey);
  listKeyRef.current = listKey;

  // ------------------------------------------------------------------ status

  const refresh = useCallback(async () => {
    try {
      const next = await request<LibraryState>('/api/library');
      setState(next);
      setOffline('');
      return next;
    } catch (err) {
      setOffline(errorText(err));
      return null;
    }
  }, []);

  useEffect(() => {
    if (active) void refresh();
    else {
      pickerDialog.current?.close();
      clearDialog.current?.close();
    }
  }, [refresh, active]);

  useEffect(() => {
    // Follow a running crunch closely; otherwise look in now and then, so a crunch
    // started from another window, or a model installed meanwhile, shows up.
    if (!active) return;
    const timer = window.setInterval(() => void refresh(), running ? 700 : 5000);
    return () => window.clearInterval(timer);
  }, [running, refresh, active]);

  useEffect(() => {
    // A crunch just ended: show what it did and reload the photos.
    if (wasRunning.current && !running && state) {
      const job = state.job;
      setRevision((value) => value + 1);
      if (job.error) setError(job.error);
      else if (job.stage === 'cancelled') setNotice('Cancelled. Crunch again to finish the rest.');
      else if (job.summary) {
        const parts: string[] = [];
        const { read, features, organize } = job.summary;
        if (read?.read) parts.push(`${count(read.read)} photos read`);
        if (read?.failed) parts.push(`${count(read.failed)} could not be read`);
        if (features?.described) parts.push(`${count(features.described)} described`);
        if (organize)
          parts.push(
            `${count(organize.groups)} groups`,
            `${count(organize.copies + organize.lookalikes)} copies and look-alikes`,
          );
        setNotice(parts.length ? `Done: ${parts.join(' · ')}.` : 'Done. Nothing had changed.');
      }
    }
    wasRunning.current = running;
  }, [running, state]);

  // While a crunch runs the list follows it: photos appear once found, then gain their
  // previews and groups as each stage ends.
  const liveStage = running ? state?.job.stage : undefined;
  useEffect(() => {
    if (liveStage) setRevision((value) => value + 1);
  }, [liveStage]);

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(typed.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [typed]);

  // ------------------------------------------------------------------ photos

  useEffect(() => {
    loading.current = new Set();
    setPages(new Map());
    setTotal(0);
  }, [listKey]);

  const need = useCallback(
    (first: number, last: number) => {
      if (similar || (view === 'groups' && !filter)) return;
      const key = listKeyRef.current;
      for (let page = Math.floor(first / PAGE); page <= Math.floor((last - 1) / PAGE); page++) {
        if (loading.current.has(page)) continue;
        loading.current.add(page);
        const parameters = new URLSearchParams({
          view: view === 'groups' ? 'all' : view,
          sort,
          q: query,
          offset: String(page * PAGE),
          limit: String(PAGE),
        });
        if (filter) parameters.set(filter.kind, String(filter.id));
        request<{ total: number; photos: LibraryPhoto[] }>(`/api/library/photos?${parameters}`)
          .then((result) => {
            if (key !== listKeyRef.current) return;
            setTotal(result.total);
            setPages((current) => new Map(current).set(page, result.photos));
          })
          .catch((err) => {
            if (key !== listKeyRef.current) return;
            loading.current.delete(page);
            setError(errorText(err));
          });
      }
    },
    [filter, query, similar, sort, view],
  );

  useEffect(() => {
    // The first page gives the count before the grid knows how many rows it has.
    if (!(view === 'groups' && !filter) && !similar) need(0, 1);
  }, [filter, listKey, need, similar, view]);

  useEffect(() => {
    if (view !== 'groups') return;
    let current = true;
    request<{ total: number; groups: LibraryGroup[] }>('/api/library/groups?limit=120')
      .then((result) => {
        if (!current) return;
        setGroups(result.groups);
        setGroupTotal(result.total);
      })
      .catch((err) => current && setError(errorText(err)));
    return () => {
      current = false;
    };
  }, [view, revision]);

  const photoAt = useCallback(
    (index: number) =>
      similar ? similar.photos[index] : pages.get(Math.floor(index / PAGE))?.[index % PAGE],
    [pages, similar],
  );

  useEffect(() => {
    if (selected == null) {
      setDetail(null);
      return;
    }
    let current = true;
    request<LibraryPhotoDetail>(`/api/library/photos/${selected}`)
      .then((result) => current && setDetail(result))
      .catch(() => {
        if (!current) return;
        setSelected(null); // Removed meanwhile.
      });
    return () => {
      current = false;
    };
  }, [selected, revision]);

  // ----------------------------------------------------------------- actions

  async function act(label: string, work: () => Promise<void>) {
    setBusy(label);
    setError('');
    setNotice('');
    try {
      await work();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy('');
    }
  }

  function changeView(next: LibraryView) {
    setView(next);
    setFilter(null);
    setSimilar(null);
  }

  const crunch = () =>
    act('Starting…', async () => {
      await send('/api/library/crunch');
      await refresh();
    });

  const cancel = () =>
    act('Cancelling…', async () => {
      await send('/api/library/cancel');
      await refresh();
    });

  async function openPicker(path?: string) {
    setPickerError('');
    try {
      const listing = await send<FolderListing>('/api/library/browse', path ? { path } : {});
      setPicker(listing);
      setPickerPath(listing.path);
      if (activeRef.current && !pickerDialog.current?.open) pickerDialog.current?.showModal();
    } catch (err) {
      if (pickerDialog.current?.open) setPickerError(errorText(err));
      else setError(errorText(err));
    }
  }

  async function addFolder() {
    if (!picker) return;
    setPickerError('');
    try {
      await send('/api/library/folders', { path: picker.path });
      pickerDialog.current?.close();
      setNotice('');
      setError('');
      await refresh();
    } catch (err) {
      setPickerError(errorText(err));
    }
  }

  const removeFolder = (id: number) =>
    act('Removing…', async () => {
      await request(`/api/library/folders/${id}`, { method: 'DELETE' });
      setSelected(null);
      await refresh();
    });

  async function upload(files: File[]) {
    const accepted = files.filter((file) => PHOTO_NAME.test(file.name) && file.size <= MAX_FILE);
    const skipped = files.length - accepted.length;
    if (!accepted.length) {
      setError('Choose PNG, JPEG, WebP, HEIC or AVIF images under 32 MiB.');
      return;
    }
    setError('');
    setNotice('');
    setUploading({ done: 0, total: accepted.length });
    let done = 0;
    let failed = 0;
    const queue = [...accepted];
    const worker = async () => {
      for (let file = queue.shift(); file; file = queue.shift()) {
        const body = new FormData();
        body.append('file', file);
        try {
          await request('/api/library/uploads', { method: 'POST', body });
        } catch {
          failed++;
        }
        done++;
        setUploading({ done, total: accepted.length });
      }
    };
    await Promise.all([worker(), worker(), worker()]);
    setUploading(null);
    if (failed || skipped)
      setError(
        `${count(failed + skipped)} of ${count(files.length)} files were not added (not a supported image, over 32 MiB, or refused).`,
      );
    if (done > failed) {
      try {
        await send('/api/library/crunch');
      } catch (err) {
        setError(errorText(err));
      }
      await refresh();
    }
  }

  function onFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = '';
    if (files.length) void upload(files);
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    const files = Array.from(event.dataTransfer.files ?? []);
    if (files.length) void upload(files);
  }

  const findSimilar = (photo: LibraryPhotoDetail) =>
    act('Finding similar photos…', async () => {
      const result = await request<{ photos: LibraryPhoto[]; model: string }>(
        `/api/library/photos/${photo.id}/similar?limit=120`,
      );
      setSimilar({ title: photo.name, ...result });
      setFilter(null);
      if (view === 'groups') setView('all');
    });

  function onSearchPicture(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    void act('Searching by picture…', async () => {
      const body = new FormData();
      body.append('file', file);
      const result = await request<{ photos: LibraryPhoto[]; model: string }>(
        '/api/library/search',
        {
          method: 'POST',
          body,
        },
      );
      setSimilar({ title: `your picture ${file.name}`, ...result });
      setFilter(null);
      setSelected(null);
      if (view === 'groups') setView('all');
    });
  }

  const openIn = (target: HandoffTarget, photo: LibraryPhotoDetail) =>
    act('Opening…', async () => {
      const response = await fetch(`/api/library/photos/${photo.id}/original`);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          typeof data.detail === 'string' ? data.detail : 'The photo could not be opened.',
        );
      }
      const extension = photo.name.split('.').pop()?.toLowerCase() ?? '';
      const file = new File([await response.blob()], photo.name, {
        type: MIME[extension] ?? 'application/octet-stream',
      });
      handOff(target, file);
    });

  const removePhoto = (photo: LibraryPhotoDetail) =>
    act('Removing…', async () => {
      await request(`/api/library/photos/${photo.id}`, { method: 'DELETE' });
      setSelected(null);
      setSimilar(null);
      await refresh();
    });

  const clearLibrary = () =>
    act('Clearing…', async () => {
      clearDialog.current?.close();
      setConfirmClear(false);
      await request('/api/library', { method: 'DELETE' });
      setSelected(null);
      setSimilar(null);
      setFilter(null);
      setRevision((value) => value + 1);
      await refresh();
    });

  useEffect(() => {
    if (active && confirmClear && !clearDialog.current?.open) clearDialog.current?.showModal();
  }, [confirmClear, active]);

  // ------------------------------------------------------------------ render

  const job = state?.job;
  const stageIndex = STAGES.findIndex((stage) => stage.id === job?.stage);
  const percent = job?.total
    ? Math.min(100, Math.round(((job.done ?? 0) / job.total) * 100))
    : null;
  const empty = !!summary && summary.photos === 0 && !running && !uploading;
  const shownTotal = similar ? similar.photos.length : total;
  const stage = STAGES[stageIndex];

  return (
    <div
      className={`app-shell library-studio${dragging ? ' dragging' : ''}`}
      onDragOver={(event) => {
        if (!event.dataTransfer.types.includes('Files')) return;
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(event) => {
        if (event.currentTarget === event.target) setDragging(false);
      }}
      onDrop={onDrop}
    >
      <AppHeader
        studio="library"
        projectName={<span className="library-title">Photo library</span>}
      />

      <main id="library">
        <h1 className="sr-only">Photo library</h1>
        <input
          ref={fileInput}
          type="file"
          multiple
          hidden
          aria-label="Add photos"
          accept="image/png,image/jpeg,image/webp,image/heic,image/heif,image/avif,.heic,.heif,.avif"
          onChange={onFiles}
        />
        <input
          ref={searchInput}
          type="file"
          hidden
          aria-label="Search by picture"
          accept="image/png,image/jpeg,image/webp,image/heic,image/heif,image/avif,.heic,.heif,.avif"
          onChange={onSearchPicture}
        />

        <section className="library-hero" aria-label="Library summary">
          <div className="library-stats">
            <Stat value={summary ? count(summary.photos) : '—'} label="photos" />
            <Stat
              value={summary ? count(summary.groups) : '—'}
              label="groups"
              hint="Sets of photos that show the same subject"
            />
            <Stat
              value={summary ? count(summary.spare) : '—'}
              label="spare copies"
              hint="Exact copies and look-alikes beyond the first of each set"
            />
            <Stat value={summary ? megabytes(summary.bytes) : '—'} label="indexed" />
          </div>
          <div className="library-engine" data-testid="vision-status">
            {vision?.available ? (
              <span className="library-chip on">
                <Cpu size={18} aria-hidden />
                {vision.model}
                {vision.runtime ? ` · ${vision.runtime.device_name}` : ' · ready'}
              </span>
            ) : (
              <details className="library-chip off">
                <summary>
                  <Cpu size={18} aria-hidden /> Vision model off
                </summary>
                <p>
                  Photos are still indexed, measured and checked for exact copies. Similar-photo
                  search, groups, look-alikes and subject detection need the optional DINOv3 model.
                </p>
                <p>
                  Request the weights from Meta, then run{' '}
                  <code>./scripts/vision-model.sh install --weights FOLDER</code> and restart the
                  workbench. See <code>docs/photo-library.md</code>.
                </p>
                {vision?.reason && <p className="library-reason">{vision.reason}</p>}
              </details>
            )}
          </div>
          <div className="library-actions">
            {state?.folders_allowed && (
              <button
                className="primary-button"
                disabled={running || !!busy}
                onClick={() => void openPicker()}
              >
                <FolderPlus size={21} aria-hidden /> Add folder
              </button>
            )}
            <button
              className={state?.folders_allowed ? 'outlined-button' : 'primary-button'}
              disabled={!!uploading || !!busy}
              onClick={() => fileInput.current?.click()}
            >
              <UploadSimple size={20} aria-hidden /> Add photos
            </button>
            <button
              className="outlined-button"
              disabled={running || !!busy || !summary?.photos}
              onClick={crunch}
              title="Look for new, changed and removed files, and finish any work left over"
            >
              <ArrowsClockwise size={20} aria-hidden /> Rescan
            </button>
            <a
              className={`outlined-button${summary?.photos ? '' : ' disabled'}`}
              href="/api/library/export?format=csv"
              download
              aria-disabled={!summary?.photos}
              onClick={(event) => !summary?.photos && event.preventDefault()}
            >
              <DownloadSimple size={20} aria-hidden /> Export CSV
            </a>
          </div>
        </section>

        {(running || uploading) && (
          <section className="library-crunch" role="status" aria-live="polite" data-testid="crunch">
            <div className="library-crunch-head">
              <SpinnerGap size={22} className="spinner" aria-hidden />
              {uploading ? (
                <strong>
                  Adding photos · {count(uploading.done)} of {count(uploading.total)}
                </strong>
              ) : (
                <>
                  <ol className="library-stages">
                    {STAGES.map((item, index) => (
                      <li
                        key={item.id}
                        className={index < stageIndex ? 'done' : index === stageIndex ? 'now' : ''}
                        aria-current={index === stageIndex ? 'step' : undefined}
                      >
                        {item.label}
                      </li>
                    ))}
                  </ol>
                  <span className="library-crunch-numbers">
                    {job?.stage === 'model'
                      ? 'Starting the vision model…'
                      : stage
                        ? `${count(job?.done ?? 0)}${job?.total ? ` of ${count(job.total)}` : ''} ${stage.unit}`
                        : 'Starting…'}
                    {stage && job?.rate && job.stage !== 'organize'
                      ? ` · ${count(Math.round(job.rate))} per second`
                      : ''}
                    {job?.eta_seconds != null ? ` · ${duration(job.eta_seconds)}` : ''}
                  </span>
                  <button className="text-button" onClick={cancel} disabled={!!busy}>
                    <X size={18} aria-hidden /> Cancel
                  </button>
                </>
              )}
            </div>
            <div
              className={`library-bar${percent == null && !uploading ? ' unknown' : ''}`}
              role="progressbar"
              aria-label="Crunch progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={
                uploading
                  ? Math.round((uploading.done / uploading.total) * 100)
                  : (percent ?? undefined)
              }
            >
              <span
                style={{
                  width: `${uploading ? (uploading.done / uploading.total) * 100 : (percent ?? 100)}%`,
                }}
              />
            </div>
          </section>
        )}

        {offline && (
          <p className="library-message error" role="alert">
            <WarningCircle size={20} aria-hidden /> {offline}
          </p>
        )}
        {error && (
          <p className="library-message error" role="alert">
            <WarningCircle size={20} aria-hidden /> {error}
            <button className="icon-button" aria-label="Dismiss" onClick={() => setError('')}>
              <X size={18} />
            </button>
          </p>
        )}
        {notice && (
          <p className="library-message" role="status">
            <CheckCircle size={20} aria-hidden /> {notice}
            <button className="icon-button" aria-label="Dismiss" onClick={() => setNotice('')}>
              <X size={18} />
            </button>
          </p>
        )}

        {empty ? (
          <section className="library-empty">
            <Images size={54} weight="light" aria-hidden />
            <h2>Crunch a whole folder of photos</h2>
            <p>
              Point the library at your photos and it reads every one: size, sharpness, exact copies
              {vision?.available ? ', what each picture shows and which shots belong together' : ''}
              . Then open the best shot of a part straight in the workbench.
            </p>
            <div className="library-empty-actions">
              {state?.folders_allowed && (
                <button className="primary-button" onClick={() => void openPicker()}>
                  <FolderPlus size={21} aria-hidden /> Add a folder on this computer
                </button>
              )}
              <button
                className={state?.folders_allowed ? 'outlined-button' : 'primary-button'}
                onClick={() => fileInput.current?.click()}
              >
                <UploadSimple size={20} aria-hidden /> Add photos
              </button>
            </div>
            <p className="library-hint">
              You can also drop photos anywhere on this page. Originals are only read, never changed
              or moved. Nothing leaves this computer.
            </p>
          </section>
        ) : (
          summary && (
            <section className="library-body">
              <div className="library-toolbar">
                <div className="library-views" role="tablist" aria-label="Views">
                  {(
                    [
                      ['all', 'All photos', summary.photos - summary.failed],
                      ['groups', 'Groups', summary.groups],
                      ['best', 'Best shots', summary.best],
                      ['duplicates', 'Copies', null],
                      ...(summary.failed ? [['failed', 'Not read', summary.failed] as const] : []),
                    ] as const
                  ).map(([id, label, number]) => (
                    <button
                      key={id}
                      role="tab"
                      aria-selected={view === id && !similar}
                      onClick={() => changeView(id)}
                    >
                      {label}
                      {number != null && <span>{count(number)}</span>}
                    </button>
                  ))}
                </div>
                {view !== 'groups' && !similar && (
                  <>
                    <label className="library-field">
                      <span className="sr-only">Sort by</span>
                      <select
                        value={sort}
                        onChange={(event) => setSort(event.target.value as LibrarySort)}
                      >
                        {SORTS.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="library-field search">
                      <MagnifyingGlass size={18} aria-hidden />
                      <span className="sr-only">Filter by file name</span>
                      <input
                        type="search"
                        placeholder="Filter by name"
                        value={typed}
                        maxLength={200}
                        onChange={(event) => setTyped(event.target.value)}
                      />
                    </label>
                  </>
                )}
                {vision?.available && (
                  <button
                    className="text-button"
                    disabled={!!busy || !summary.described}
                    onClick={() => searchInput.current?.click()}
                    title="Choose any picture to find the photos that look like it. The picture is not added."
                  >
                    <MagnifyingGlass size={18} aria-hidden /> Search by picture
                  </button>
                )}
                {busy && (
                  <span className="library-busy" role="status">
                    <SpinnerGap size={18} className="spinner" aria-hidden /> {busy}
                  </span>
                )}
              </div>

              {(similar || filter) && (
                <p className="library-filter" data-testid="filter">
                  {similar ? (
                    <>
                      <strong>{count(similar.photos.length)}</strong> photos most like{' '}
                      <em>{similar.title}</em>, closest first ({similar.model}).
                    </>
                  ) : filter?.kind === 'group' ? (
                    <>
                      One group: <strong>{count(filter.size)}</strong> photos of the same subject.
                    </>
                  ) : (
                    <>
                      One set of <strong>{count(filter?.size ?? 0)}</strong> copies and look-alikes.
                    </>
                  )}
                  <button
                    className="text-button"
                    onClick={() => {
                      setSimilar(null);
                      setFilter(null);
                    }}
                  >
                    <ArrowLeft size={17} aria-hidden /> Back to{' '}
                    {view === 'groups' ? 'groups' : 'the list'}
                  </button>
                </p>
              )}

              <div className={`library-content${detail ? ' with-detail' : ''}`}>
                {view === 'groups' && !filter && !similar ? (
                  <div className="library-groups">
                    {groups.length === 0 && (
                      <p className="library-none">
                        {vision?.available
                          ? 'No groups yet. Groups appear when two or more photos show the same subject.'
                          : 'Groups need the vision model. Exact copies are still found without it.'}
                      </p>
                    )}
                    {groups.map((group) => (
                      <button
                        key={group.id}
                        className="library-group"
                        aria-label={`Group of ${group.size} photos, best shot ${group.name}`}
                        onClick={() => setFilter({ kind: 'group', id: group.id, size: group.size })}
                      >
                        <span
                          className="library-collage"
                          data-count={Math.min(group.members.length, 4)}
                        >
                          {group.members.slice(0, 4).map((id) => (
                            <img
                              key={id}
                              src={previewUrl(id)}
                              alt=""
                              loading="lazy"
                              decoding="async"
                            />
                          ))}
                        </span>
                        <span className="library-group-text">
                          <strong>{count(group.size)} photos</strong>
                          <span>{group.name}</span>
                        </span>
                      </button>
                    ))}
                    {groupTotal > groups.length && (
                      <p className="library-none">
                        Showing the {count(groups.length)} largest of {count(groupTotal)} groups.
                        Every group is in the CSV export.
                      </p>
                    )}
                  </div>
                ) : shownTotal === 0 && (similar || pages.has(0)) ? (
                  <p className="library-none">
                    {query
                      ? 'No photo name contains that text.'
                      : view === 'duplicates'
                        ? 'No copies or look-alikes were found.'
                        : view === 'best'
                          ? 'Best shots appear once photos form groups.'
                          : 'Nothing to show here.'}
                  </p>
                ) : (
                  <PhotoGrid
                    total={shownTotal}
                    photoAt={photoAt}
                    need={need}
                    selected={selected}
                    onSelect={(photo) => setSelected(photo.id === selected ? null : photo.id)}
                    resetKey={similar ? `similar-${similar.title}` : listKey}
                  />
                )}

                {detail && (
                  <aside className="library-detail" aria-label={`Details of ${detail.name}`}>
                    <div className="library-detail-head">
                      <h2>{detail.name}</h2>
                      <button
                        className="icon-button"
                        aria-label="Close details"
                        onClick={() => setSelected(null)}
                      >
                        <X size={20} />
                      </button>
                    </div>
                    {detail.state === 'ready' ? (
                      <SubjectView detail={detail} show={showSubject} />
                    ) : (
                      <p className="library-message error">
                        <WarningCircle size={20} aria-hidden />{' '}
                        {detail.error ?? 'This file has not been read yet.'}
                      </p>
                    )}
                    {detail.subject && (
                      <label className="library-toggle">
                        <input
                          type="checkbox"
                          checked={showSubject}
                          onChange={(event) => setShowSubject(event.target.checked)}
                        />
                        Light up the subject the model found
                      </label>
                    )}
                    {detail.state === 'ready' && (
                      <div className="library-detail-actions">
                        <button
                          className="primary-button"
                          disabled={!!busy}
                          onClick={() => void openIn('workbench', detail)}
                        >
                          <Ruler size={20} aria-hidden /> Open in Flat part
                        </button>
                        <button
                          className="outlined-button"
                          disabled={!!busy}
                          onClick={() => void openIn('relief', detail)}
                        >
                          <Mountains size={20} aria-hidden /> Open in Relief
                        </button>
                        {detail.model && (
                          <button
                            className="outlined-button"
                            disabled={!!busy}
                            onClick={() => void findSimilar(detail)}
                          >
                            <MagnifyingGlass size={20} aria-hidden /> Find similar
                          </button>
                        )}
                      </div>
                    )}
                    <dl className="library-facts">
                      <dt>Size</dt>
                      <dd>{megapixels(detail.width, detail.height)}</dd>
                      <dt>File</dt>
                      <dd>
                        {megabytes(detail.bytes)}
                        {detail.format ? ` · ${detail.format}` : ''}
                      </dd>
                      {detail.taken_at && (
                        <>
                          <dt>Taken</dt>
                          <dd>{taken(detail.taken_at)}</dd>
                        </>
                      )}
                      {detail.camera && (
                        <>
                          <dt>Camera</dt>
                          <dd>
                            {detail.camera}
                            {detail.focal_35mm
                              ? ` · ${Math.round(detail.focal_35mm)} mm equiv.`
                              : ''}
                          </dd>
                        </>
                      )}
                      {blurOf(detail) != null && (
                        <>
                          <dt>Edge blur</dt>
                          <dd>
                            {blurOf(detail)?.toFixed(2)} px{' '}
                            <small>
                              {detail.subject_blur_px != null ? 'on the subject' : 'whole picture'};
                              lower is sharper
                            </small>
                          </dd>
                        </>
                      )}
                      {detail.detail != null && (
                        <>
                          <dt>Detail</dt>
                          <dd>
                            {count(Math.round(detail.detail))}{' '}
                            <small>blur widths across the {detail.box ? 'subject' : 'frame'}</small>
                          </dd>
                        </>
                      )}
                      {detail.subject && (
                        <>
                          <dt>Subject</dt>
                          <dd>
                            {Math.round(detail.subject.share * 100)}% <small>of the frame</small>
                          </dd>
                        </>
                      )}
                      {detail.clipped != null && detail.clipped >= 0.02 && (
                        <>
                          <dt>Clipped</dt>
                          <dd>
                            {Math.round(detail.clipped * 100)}%{' '}
                            <small>of pixels at or near pure black or white</small>
                          </dd>
                        </>
                      )}
                      {detail.group_id != null && (
                        <>
                          <dt>Group</dt>
                          <dd>
                            {detail.best ? 'Best shot of ' : 'One of '}
                            {count(detail.group_size)}{' '}
                            <button
                              className="library-link"
                              onClick={() => {
                                setSimilar(null);
                                setFilter({
                                  kind: 'group',
                                  id: detail.group_id!,
                                  size: detail.group_size,
                                });
                                if (view === 'groups') return;
                                setView('all');
                              }}
                            >
                              Show group <CaretRight size={13} aria-hidden />
                            </button>
                          </dd>
                        </>
                      )}
                      {detail.dup_set != null && (
                        <>
                          <dt>Copies</dt>
                          <dd>
                            {detail.dup_kind === 'exact' ? 'Exact copy' : 'Look-alike'} in a set of{' '}
                            {count(detail.dup_size)}{' '}
                            <button
                              className="library-link"
                              onClick={() => {
                                setSimilar(null);
                                setView('duplicates');
                                setFilter({
                                  kind: 'dup',
                                  id: detail.dup_set!,
                                  size: detail.dup_size,
                                });
                              }}
                            >
                              Show set <CaretRight size={13} aria-hidden />
                            </button>
                          </dd>
                        </>
                      )}
                      {detail.path && (
                        <>
                          <dt>Path</dt>
                          <dd className="library-path">
                            {detail.path}{' '}
                            <button
                              className="library-link"
                              onClick={() => void navigator.clipboard?.writeText(detail.path ?? '')}
                            >
                              <Copy size={13} aria-hidden /> Copy
                            </button>
                          </dd>
                        </>
                      )}
                    </dl>
                    {detail.model && (
                      <p className="library-hint">
                        Subject, groups and matches are estimates from {detail.model} features at a
                        resolution of 1/28 of the frame. They help you choose a photo; they are not
                        measurements.
                      </p>
                    )}
                    {detail.source === 'upload' ? (
                      <button
                        className="text-button danger"
                        disabled={running || !!busy}
                        onClick={() => void removePhoto(detail)}
                      >
                        <Trash size={18} aria-hidden /> Remove from library
                      </button>
                    ) : (
                      <p className="library-hint">
                        From an added folder. The library never deletes your files; remove the
                        folder below to forget its photos.
                      </p>
                    )}
                  </aside>
                )}
              </div>

              <details className="library-storage">
                <summary>Folders and storage</summary>
                {summary.folders.length === 0 && summary.uploads === 0 && <p>No folders yet.</p>}
                <ul>
                  {summary.folders.map((folder) => (
                    <li key={folder.id}>
                      <FolderOpen size={19} aria-hidden />
                      <span className="library-path">{folder.path}</span>
                      <span>{count(folder.photos)} photos</span>
                      <button
                        className="text-button"
                        disabled={running || !!busy}
                        onClick={() => void removeFolder(folder.id)}
                        aria-label={`Remove ${folder.path} from the library`}
                      >
                        <X size={17} aria-hidden /> Remove
                      </button>
                    </li>
                  ))}
                  {summary.uploads > 0 && (
                    <li>
                      <UploadSimple size={19} aria-hidden />
                      <span className="library-path">
                        Added through the browser (kept in the library)
                      </span>
                      <span>{count(summary.uploads)} photos</span>
                    </li>
                  )}
                </ul>
                <p className="library-hint">
                  The library keeps a 512-pixel preview and measurements of each photo on this
                  computer. Removing a folder forgets those; it never touches the folder. Location
                  data in photos is never read.
                </p>
                <div className="library-storage-actions">
                  <a className="text-button" href="/api/library/export?format=json" download>
                    <DownloadSimple size={18} aria-hidden /> Export JSON
                  </a>
                  <button
                    className="text-button danger"
                    disabled={running || !!busy || !summary.photos}
                    onClick={() => setConfirmClear(true)}
                  >
                    <Trash size={18} aria-hidden /> Clear library…
                  </button>
                </div>
              </details>
            </section>
          )
        )}
      </main>

      <dialog
        ref={pickerDialog}
        className="modal library-picker"
        aria-labelledby="library-picker-title"
        onClose={() => setPicker(null)}
      >
        <div className="modal-header">
          <h2 id="library-picker-title">Add a folder</h2>
          <button
            className="icon-button close-button"
            aria-label="Close"
            onClick={() => pickerDialog.current?.close()}
          >
            <X size={22} />
          </button>
        </div>
        {picker && (
          <>
            <form
              className="library-picker-path"
              onSubmit={(event) => {
                event.preventDefault();
                void openPicker(pickerPath);
              }}
            >
              <label htmlFor="library-picker-input" className="sr-only">
                Folder path
              </label>
              <input
                id="library-picker-input"
                value={pickerPath}
                maxLength={4096}
                spellCheck={false}
                onChange={(event) => setPickerPath(event.target.value)}
              />
              <button className="outlined-button" type="submit">
                Go
              </button>
            </form>
            <div className="library-picker-shortcuts">
              {picker.parent && (
                <button
                  className="text-button"
                  onClick={() => void openPicker(picker.parent ?? undefined)}
                >
                  <ArrowLeft size={17} aria-hidden /> Up
                </button>
              )}
              <button className="text-button" onClick={() => void openPicker(picker.home)}>
                <House size={17} aria-hidden /> Home
              </button>
              {picker.shortcuts.map((shortcut) => (
                <button
                  key={shortcut.path}
                  className="text-button"
                  onClick={() => void openPicker(shortcut.path)}
                >
                  {shortcut.name}
                </button>
              ))}
            </div>
            <ul className="library-picker-list" aria-label={`Folders in ${picker.name}`}>
              {picker.folders.length === 0 && (
                <li className="library-none">No folders inside this one.</li>
              )}
              {picker.folders.map((folder) => (
                <li key={folder.path}>
                  <button onClick={() => void openPicker(folder.path)}>
                    <FolderOpen size={19} aria-hidden /> {folder.name}
                    <CaretRight size={15} aria-hidden />
                  </button>
                </li>
              ))}
            </ul>
            {pickerError && (
              <p className="library-message error" role="alert">
                <WarningCircle size={20} aria-hidden /> {pickerError}
              </p>
            )}
            <div className="modal-footer library-picker-footer">
              <span>
                {count(picker.photos)} pictures directly in <strong>{picker.name}</strong>. Folders
                inside it are included.
              </span>
              <button className="primary-button" onClick={() => void addFolder()}>
                <FolderPlus size={20} aria-hidden /> Add this folder
              </button>
            </div>
          </>
        )}
      </dialog>

      <dialog
        ref={clearDialog}
        className="modal library-clear"
        aria-labelledby="library-clear-title"
        onClose={() => setConfirmClear(false)}
      >
        <div className="modal-header">
          <h2 id="library-clear-title">Clear the library?</h2>
        </div>
        <p>
          This forgets every folder, preview, measurement and feature, and deletes photos that were
          added through the browser from the library’s storage. Files in your own folders are not
          touched.
        </p>
        <div className="modal-footer library-picker-footer">
          <button className="outlined-button" onClick={() => clearDialog.current?.close()}>
            Keep it
          </button>
          <button className="primary-button danger" onClick={() => void clearLibrary()}>
            <Trash size={19} aria-hidden /> Clear library
          </button>
        </div>
      </dialog>

      {dragging && (
        <div className="library-drop" aria-hidden>
          <UploadSimple size={44} weight="light" />
          <strong>Drop photos to add them</strong>
        </div>
      )}
    </div>
  );
}
