/** Successful server-wide deletion invalidates every retained studio in this page. */
let generation = 0;
const listeners = new Set<() => void>();

export function temporaryExportGeneration() {
  return generation;
}

export function onTemporaryExportsCleared(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Publish only after DELETE /api/models succeeds; failed requests preserve exports. */
export function publishTemporaryExportsCleared() {
  generation += 1;
  for (const listener of listeners) listener();
}
