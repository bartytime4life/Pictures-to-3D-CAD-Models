/** Browser-owned downloads; no network or backend write is involved. */
// Nine notes of 10,000 UTF-16 code units can exceed 500 KB when JSON-escaped.
// Keep exported, schema-valid notebooks importable even at that worst case.
export const STUDIO_JSON_MAX_BYTES = 1024 * 1024;

export function studioJsonBlob(value: unknown): Blob {
  return new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' });
}

export function saveStudioJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(studioJsonBlob(value));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function readStudioJson(file: File): Promise<unknown> {
  if (!file.size || file.size > STUDIO_JSON_MAX_BYTES)
    throw new Error('Choose a JSON file between 1 byte and 1 MiB.');
  try {
    return JSON.parse(await file.text()) as unknown;
  } catch {
    throw new Error('This file could not be read as JSON.');
  }
}
