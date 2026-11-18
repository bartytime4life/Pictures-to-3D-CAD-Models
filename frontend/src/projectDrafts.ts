import type {
  LibraryProject,
  PrintAttempt,
  PrintStatus,
  ProjectDetailsUpdate,
} from './projectLibrary.ts';
import type { ProjectRecipe } from './types.ts';

export type ProjectDraft = {
  status: PrintStatus;
  tags: string;
  notes: string;
  date: string;
  outcome: PrintAttempt['outcome'];
  attemptNotes: string;
};
type DraftEntry = {
  snapshot: string;
  fields: Partial<ProjectDraft>;
  edits: Partial<Record<keyof ProjectDraft, symbol>>;
};
export type ProjectDraftMap = ReadonlyMap<number, DraftEntry>;
type WriteEntry = { snapshot: string; active: readonly number[] };
export type ProjectWriteMap = ReadonlyMap<number, WriteEntry>;
export type ProjectWrite = { id: number; snapshot: string; token: number };
export const PROJECT_DRAFT_LIMIT = 100;
const DETAIL_FIELDS = ['status', 'tags', 'notes'] as const;
const ATTEMPT_FIELDS = ['date', 'outcome', 'attemptNotes'] as const;

// A recipe can contain many contour points. Serialize once per loaded snapshot object.
const recipeKeys = new WeakMap<ProjectRecipe, string>();
function snapshotKey(project: LibraryProject) {
  let recipe = recipeKeys.get(project.recipe);
  if (!recipe) {
    recipe = JSON.stringify(project.recipe);
    recipeKeys.set(project.recipe, recipe);
  }
  return `${project.savedAt}:${recipe}`;
}

export function readProjectDraft(
  project: LibraryProject,
  drafts: ProjectDraftMap,
  today: string,
): ProjectDraft {
  const entry = drafts.get(project.id);
  return {
    status: project.status,
    tags: project.tags.join(', '),
    notes: project.notes,
    date: today,
    outcome: 'Printed',
    attemptNotes: '',
    ...(entry?.snapshot === snapshotKey(project) ? entry.fields : {}),
  };
}

export function patchProjectDraft(
  drafts: ProjectDraftMap,
  project: LibraryProject,
  patch: Partial<ProjectDraft>,
  today: string,
  writes: ProjectWriteMap = new Map(),
): ProjectDraftMap {
  const snapshot = snapshotKey(project);
  const entry = drafts.get(project.id);
  const fields = { ...(entry?.snapshot === snapshot ? entry.fields : {}), ...patch };
  const edits = { ...(entry?.snapshot === snapshot ? entry.edits : {}) };
  for (const key of Object.keys(patch) as (keyof ProjectDraft)[]) edits[key] = Symbol(key);
  const defaults = readProjectDraft(project, new Map(), today);
  // A visible old default may be the user's deliberate revert of an in-flight write.
  // Keep that intent until a fresh read confirms what was actually stored.
  if (writes.get(project.id)?.snapshot !== snapshot)
    for (const key of Object.keys(fields) as (keyof ProjectDraft)[])
      if (fields[key] === defaults[key]) {
        delete fields[key];
        delete edits[key];
      }
  const next = new Map(drafts);
  if (Object.keys(fields).length === 0) next.delete(project.id);
  else {
    if (!next.has(project.id) && next.size >= PROJECT_DRAFT_LIMIT)
      throw new Error(
        `You have unsaved edits in ${PROJECT_DRAFT_LIMIT} projects. Save some before editing another project.`,
      );
    next.set(project.id, { snapshot, fields, edits });
  }
  return next;
}

export function beginProjectWrite(writes: ProjectWriteMap, project: LibraryProject, token: number) {
  const write = { id: project.id, snapshot: snapshotKey(project), token };
  const previous = writes.get(project.id);
  const active = previous?.snapshot === write.snapshot ? previous.active : [];
  const next = new Map(writes);
  next.set(project.id, { snapshot: write.snapshot, active: [...active, token] });
  return { writes: next as ProjectWriteMap, write };
}

export function finishProjectWrite(writes: ProjectWriteMap, write: ProjectWrite): ProjectWriteMap {
  const current = writes.get(write.id);
  if (current?.snapshot !== write.snapshot || !current.active.includes(write.token)) return writes;
  const next = new Map(writes);
  // An empty active list still protects reverts until an up-to-date read is acknowledged.
  next.set(write.id, {
    ...current,
    active: current.active.filter((token) => token !== write.token),
  });
  return next;
}

/** Only a read begun after the last write settled may release its baseline protection. */
export function acknowledgeProjectWrites(
  drafts: ProjectDraftMap,
  writes: ProjectWriteMap,
  observed: ProjectWriteMap,
  projects: LibraryProject[],
  today: string,
) {
  let nextDrafts = drafts;
  let nextWrites = writes;
  for (const [id, entry] of observed) {
    if (entry.active.length || writes.get(id) !== entry) continue;
    const project = projects.find((item) => item.id === id);
    if (
      project &&
      snapshotKey(project) === entry.snapshot &&
      nextDrafts.get(id)?.snapshot === entry.snapshot
    ) {
      // Nothing is pending for this snapshot, and these defaults came from the completed read.
      nextDrafts = patchProjectDraft(nextDrafts, project, {}, today);
    }
    const remaining = new Map(nextWrites);
    remaining.delete(id);
    nextWrites = remaining;
  }
  return { drafts: nextDrafts, writes: nextWrites };
}

/** Clear only the form whose write succeeded; failed saves leave the map untouched. */
export function clearProjectDraft(
  drafts: ProjectDraftMap,
  id: number,
  section: 'details' | 'attempt' | 'all',
): ProjectDraftMap {
  const next = new Map(drafts);
  const entry = next.get(id);
  if (!entry) return next;
  if (section === 'all') next.delete(id);
  else {
    const fields = { ...entry.fields };
    const edits = { ...entry.edits };
    for (const key of section === 'details' ? DETAIL_FIELDS : ATTEMPT_FIELDS) {
      delete fields[key];
      delete edits[key];
    }
    if (Object.keys(fields).length) next.set(id, { ...entry, fields, edits });
    else next.delete(id);
  }
  return next;
}

/** Clear the exact submitted edit, including A-B-A changes that repeat its value later. */
export function clearSavedProjectDraft(
  drafts: ProjectDraftMap,
  submitted: ProjectDraftMap,
  id: number,
  section: 'details' | 'attempt',
): ProjectDraftMap {
  const current = drafts.get(id),
    before = submitted.get(id);
  if (!current || !before || current.snapshot !== before.snapshot) return drafts;
  const fields = { ...current.fields };
  const edits = { ...current.edits };
  for (const key of section === 'details' ? DETAIL_FIELDS : ATTEMPT_FIELDS)
    if (fields[key] === before.fields[key] && edits[key] === before.edits[key]) {
      delete fields[key];
      delete edits[key];
    }
  const next = new Map(drafts);
  if (Object.keys(fields).length) next.set(id, { ...current, fields, edits });
  else next.delete(id);
  return next;
}

export function projectDetailsUpdate(
  project: LibraryProject,
  draft: ProjectDraft,
  explicit: Partial<ProjectDraft> = {},
): ProjectDetailsUpdate {
  const distinctTags = new Map<string, string>();
  for (const tag of draft.tags
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean))
    if (!distinctTags.has(tag.toLowerCase())) distinctTags.set(tag.toLowerCase(), tag);
  const tags = [...distinctTags.values()];
  const update: ProjectDetailsUpdate = {};
  if (draft.status !== project.status || explicit.status !== undefined)
    update.status = draft.status;
  if (tags.join(', ') !== project.tags.join(', ') || explicit.tags !== undefined)
    update.tags = tags;
  if (draft.notes.trim() !== project.notes || explicit.notes !== undefined)
    update.notes = draft.notes.trim();
  return update;
}

/** Explicit reverts must be written even when an older loaded snapshot shows the same value. */
export function projectDetailsWrite(
  project: LibraryProject,
  drafts: ProjectDraftMap,
  today: string,
  writes: ProjectWriteMap,
) {
  const snapshot = snapshotKey(project),
    entry = drafts.get(project.id);
  const explicit =
    writes.get(project.id)?.snapshot === snapshot && entry?.snapshot === snapshot
      ? entry.fields
      : {};
  return projectDetailsUpdate(project, readProjectDraft(project, drafts, today), explicit);
}

export function projectDraftChanged(
  project: LibraryProject,
  drafts: ProjectDraftMap,
  today: string,
  writes: ProjectWriteMap = new Map(),
) {
  const draft = readProjectDraft(project, drafts, today);
  const entry = drafts.get(project.id);
  const pendingIntent =
    writes.get(project.id)?.snapshot === snapshotKey(project) &&
    entry?.snapshot === snapshotKey(project) &&
    Object.keys(entry.fields).length > 0;
  return (
    pendingIntent ||
    Object.keys(projectDetailsUpdate(project, draft)).length > 0 ||
    draft.date !== today ||
    draft.outcome !== 'Printed' ||
    draft.attemptNotes.trim() !== ''
  );
}
