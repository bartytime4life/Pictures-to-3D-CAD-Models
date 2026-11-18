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
type DraftEntry = { snapshot: string; fields: Partial<ProjectDraft> };
export type ProjectDraftMap = ReadonlyMap<number, DraftEntry>;
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
): ProjectDraftMap {
  const snapshot = snapshotKey(project);
  const entry = drafts.get(project.id);
  const fields = { ...(entry?.snapshot === snapshot ? entry.fields : {}), ...patch };
  const defaults = readProjectDraft(project, new Map(), today);
  for (const key of Object.keys(fields) as (keyof ProjectDraft)[])
    if (fields[key] === defaults[key]) delete fields[key];
  const next = new Map(drafts);
  if (Object.keys(fields).length === 0) next.delete(project.id);
  else {
    if (!next.has(project.id) && next.size >= PROJECT_DRAFT_LIMIT)
      throw new Error(
        `You have unsaved edits in ${PROJECT_DRAFT_LIMIT} projects. Save some before editing another project.`,
      );
    next.set(project.id, { snapshot, fields });
  }
  return next;
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
    for (const key of section === 'details' ? DETAIL_FIELDS : ATTEMPT_FIELDS) delete fields[key];
    if (Object.keys(fields).length) next.set(id, { ...entry, fields });
    else next.delete(id);
  }
  return next;
}

/** A save finishing after the modal reopens cannot clear edits made after submission. */
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
  for (const key of section === 'details' ? DETAIL_FIELDS : ATTEMPT_FIELDS)
    if (fields[key] === before.fields[key]) delete fields[key];
  const next = new Map(drafts);
  if (Object.keys(fields).length) next.set(id, { ...current, fields });
  else next.delete(id);
  return next;
}

export function projectDetailsUpdate(
  project: LibraryProject,
  draft: ProjectDraft,
): ProjectDetailsUpdate {
  const distinctTags = new Map<string, string>();
  for (const tag of draft.tags
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean))
    if (!distinctTags.has(tag.toLowerCase())) distinctTags.set(tag.toLowerCase(), tag);
  const tags = [...distinctTags.values()];
  const update: ProjectDetailsUpdate = {};
  if (draft.status !== project.status) update.status = draft.status;
  if (tags.join(', ') !== project.tags.join(', ')) update.tags = tags;
  if (draft.notes.trim() !== project.notes) update.notes = draft.notes.trim();
  return update;
}

export function projectDraftChanged(
  project: LibraryProject,
  drafts: ProjectDraftMap,
  today: string,
) {
  const draft = readProjectDraft(project, drafts, today);
  return (
    Object.keys(projectDetailsUpdate(project, draft)).length > 0 ||
    draft.date !== today ||
    draft.outcome !== 'Printed' ||
    draft.attemptNotes.trim() !== ''
  );
}
