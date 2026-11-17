// Types, requests and number formatting for the photo library (backend/library.py).

export type LibraryView = 'all' | 'groups' | 'best' | 'duplicates' | 'failed';
export type LibrarySort = 'added' | 'taken' | 'name' | 'sharp' | 'detail' | 'size';

export type LibraryPhoto = {
  id: number;
  name: string;
  width: number | null;
  height: number | null;
  blur_px: number | null;
  subject_blur_px: number | null;
  detail: number | null;
  taken_at: string | null;
  state: 'pending' | 'ready' | 'failed';
  group_id: number | null;
  dup_set: number | null;
  dup_kind: 'exact' | 'lookalike' | null;
  best: boolean;
  box?: [number, number, number, number];
  score?: number;
};

export type LibraryPhotoDetail = LibraryPhoto & {
  path: string | null;
  source: 'folder' | 'upload';
  bytes: number | null;
  format: string | null;
  camera: string | null;
  focal_35mm: number | null;
  brightness: number | null;
  clipped: number | null;
  error: string | null;
  group_size: number;
  dup_size: number;
  model: string | null;
  subject?: { grid: number; rows: string[]; share: number };
};

export type LibraryGroup = {
  id: number;
  size: number;
  cover: number;
  name: string;
  members: number[];
};

export type LibraryJob = {
  running: boolean;
  label?: string;
  stage?: string;
  done?: number;
  total?: number;
  rate?: number;
  eta_seconds?: number | null;
  error?: string | null;
  /** Unix time the last crunch ended; changes even when the page never saw it running. */
  finished?: number;
  summary?: {
    scan?: { new: number; changed: number; gone: number };
    read?: { read: number; failed: number };
    features?: { described: number; model?: string; skipped?: string };
    organize?: { copies: number; lookalikes: number; groups: number };
  } | null;
};

export type VisionStatus = {
  available: boolean;
  reason: string;
  model: string | null;
  license: string;
  installed: string[];
  standin: boolean;
  runtime: { device: string; device_name: string; precision: string; runtime: string } | null;
};

export type LibraryState = {
  summary: {
    photos: number;
    ready: number;
    pending: number;
    failed: number;
    bytes: number;
    groups: number;
    spare: number;
    best: number;
    described: number;
    uploads: number;
    folders: { id: number; path: string; photos: number }[];
  };
  vision: VisionStatus;
  job: LibraryJob;
  folders_allowed: boolean;
};

export type FolderListing = {
  path: string;
  name: string;
  parent: string | null;
  folders: { name: string; path: string }[];
  photos: number;
  home: string;
  shortcuts: { name: string; path: string }[];
};

export const PAGE = 200;
export const MAX_FILE = 32 * 1024 * 1024;
export const PHOTO_NAME = /\.(png|jpe?g|webp|heic|heif|avif)$/i;

export const SORTS: { value: LibrarySort; label: string }[] = [
  { value: 'added', label: 'Newest added' },
  { value: 'taken', label: 'Date taken' },
  { value: 'name', label: 'Name' },
  { value: 'sharp', label: 'Sharpest edges' },
  { value: 'detail', label: 'Most detail' },
  { value: 'size', label: 'Most pixels' },
];

export const STAGES: { id: string; label: string; unit: string; one: string }[] = [
  { id: 'scan', label: 'Scan', unit: 'files found', one: 'file found' },
  { id: 'read', label: 'Read', unit: 'photos', one: 'photo' },
  { id: 'features', label: 'Describe', unit: 'photos', one: 'photo' },
  { id: 'organize', label: 'Organize', unit: 'comparisons', one: 'comparison' },
];

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new Error('Could not reach the CAD service. Check the connection and try again.');
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === 'string' ? data.detail : `The request failed (${response.status}).`,
    );
  }
  return (await response.json()) as T;
}

export function send<T>(url: string, body: unknown = {}, method = 'POST'): Promise<T> {
  return request<T>(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export const previewUrl = (id: number) => `/api/library/photos/${id}/preview`;

export function count(value: number) {
  return value.toLocaleString('en-US');
}

/** "1 photo", "2 photos", "0 photos": a counted noun in the right number. */
export function plural(value: number, one: string, many: string) {
  return `${count(value)} ${value === 1 ? one : many}`;
}

export function megabytes(bytes: number | null) {
  if (bytes == null) return '—';
  if (bytes === 0) return '0 MB';
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1e3))} kB`;
}

export function megapixels(width: number | null, height: number | null) {
  if (!width || !height) return '—';
  return `${count(width)} × ${count(height)} · ${((width * height) / 1e6).toFixed(1)} MP`;
}

export function duration(seconds: number | null | undefined) {
  if (seconds == null) return '';
  if (seconds < 90) return `about ${Math.max(1, Math.round(seconds))} s left`;
  if (seconds < 5400) return `about ${Math.round(seconds / 60)} min left`;
  return `about ${(seconds / 3600).toFixed(1)} h left`;
}

export function taken(stamp: string | null) {
  if (!stamp) return '—';
  const [date, time] = stamp.split('T');
  return `${date} ${time?.slice(0, 5) ?? ''}`.trim();
}

/** Edge blur of the part when the vision model found it, of the whole picture otherwise. */
export function blurOf(photo: LibraryPhoto) {
  return photo.subject_blur_px ?? photo.blur_px;
}
