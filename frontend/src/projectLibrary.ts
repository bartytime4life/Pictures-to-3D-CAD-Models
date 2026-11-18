import type { ProjectRecipe } from './types';
import { KeyedTaskQueue } from './keyedTaskQueue.ts';

export const PRINT_OUTCOMES = ['Printed', 'Failed'] as const;
export const PRINT_STATUSES = ['Unprinted', 'Queued', 'Printing', ...PRINT_OUTCOMES] as const;
export type PrintStatus = (typeof PRINT_STATUSES)[number];
export type PrintAttempt = {
  date: string;
  outcome: (typeof PRINT_OUTCOMES)[number];
  notes: string;
};
export type LibraryProject = {
  id: number;
  recipe: ProjectRecipe;
  savedAt: number;
  status: PrintStatus;
  tags: string[];
  notes: string;
  attempts: PrintAttempt[];
};

const STORE = 'projects';
// Keep submission order explicit across modal instances, including delayed storage acquisition.
const projectUpdates = new KeyedTaskQueue<number>();

function openLibrary(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('pictures-to-cad-project-library', 1);
    request.onupgradeneeded = () => {
      const store = request.result.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true });
      store.createIndex('name', 'recipe.name');
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function transact<T>(
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore, setResult: (value: T) => void) => void,
): Promise<T> {
  const db = await openLibrary();
  try {
    return await new Promise<T>((resolve, reject) => {
      const transaction = db.transaction(STORE, mode);
      let result: T;
      transaction.oncomplete = () => resolve(result);
      transaction.onabort = () => reject(transaction.error);
      operation(transaction.objectStore(STORE), (value) => {
        result = value;
      });
    });
  } finally {
    db.close();
  }
}

export function listLibraryProjects() {
  return transact<LibraryProject[]>('readonly', (store, setResult) => {
    const request = store.getAll();
    request.onsuccess = () => setResult((request.result as LibraryProject[]).reverse());
  });
}

export function saveLibraryProject(recipe: ProjectRecipe) {
  const serialized = JSON.stringify(recipe);
  return transact<{ project: LibraryProject; created: boolean }>(
    'readwrite',
    (store, setResult) => {
      const matches = store.index('name').getAll(recipe.name);
      matches.onsuccess = () => {
        const existing = (matches.result as LibraryProject[]).find(
          (project) => JSON.stringify(project.recipe) === serialized,
        );
        if (existing) {
          setResult({ project: existing, created: false });
          return;
        }
        const snapshot = {
          recipe,
          savedAt: Date.now(),
          status: 'Unprinted' as const,
          tags: [],
          notes: '',
          attempts: [],
        };
        const request = store.add(snapshot);
        request.onsuccess = () =>
          setResult({ project: { id: Number(request.result), ...snapshot }, created: true });
      };
    },
  );
}

export type ProjectDetailsUpdate = Partial<Pick<LibraryProject, 'status' | 'tags' | 'notes'>>;
export type ProjectUpdate = ProjectDetailsUpdate | { attempt: PrintAttempt };

export function updateLibraryProject(id: number, update: ProjectUpdate) {
  return projectUpdates.run(id, () =>
    transact<LibraryProject | null>('readwrite', (store, setResult) => {
      const request = store.get(id);
      request.onsuccess = () => {
        const current = request.result as LibraryProject | undefined;
        if (!current) {
          setResult(null);
          return;
        }
        const updated =
          'attempt' in update
            ? {
                ...current,
                status: update.attempt.outcome,
                attempts: [...current.attempts, update.attempt],
              }
            : { ...current, ...update };
        store.put(updated);
        setResult(updated);
      };
    }),
  );
}

export function removeLibraryProject(id: number) {
  return transact<void>('readwrite', (store) => {
    store.delete(id);
  });
}
