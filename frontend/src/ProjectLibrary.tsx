import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { ArrowSquareOut, DownloadSimple, Plus, Trash } from '@phosphor-icons/react';
import {
  listLibraryProjects,
  PRINT_OUTCOMES,
  PRINT_STATUSES,
  removeLibraryProject,
  saveLibraryProject,
  updateLibraryProject,
} from './projectLibrary';
import type { LibraryProject, PrintStatus, ProjectUpdate } from './projectLibrary';
import {
  acknowledgeProjectWrites,
  beginProjectWrite,
  clearProjectDraft,
  clearSavedProjectDraft,
  finishProjectWrite,
  patchProjectDraft,
  projectDetailsUpdate,
  projectDetailsWrite,
  projectDraftChanged,
  readProjectDraft,
} from './projectDrafts';
import type { ProjectDraft, ProjectDraftMap, ProjectWriteMap } from './projectDrafts';
import { downloadProjectRecipe, profileBounds } from './projectRecipe';
import type { Profile, ProjectRecipe } from './types';
import './ProjectLibrary.css';

// The modal unmounts on close. Keep its unsaved text in this tab until it is saved,
// its snapshot is deleted, or the page reloads. No drafts are written to storage.
let draftCache: { drafts: ProjectDraftMap; writes: ProjectWriteMap; revision: number } = {
  drafts: new Map(),
  writes: new Map(),
  revision: 0,
};
let writeToken = 0;
const draftSubscribers = new Set<() => void>();
function subscribeDrafts(listener: () => void) {
  draftSubscribers.add(listener);
  return () => {
    draftSubscribers.delete(listener);
  };
}
const readDraftCache = () => draftCache;
function keepDrafts(drafts: ProjectDraftMap, saved = false, writes = draftCache.writes) {
  if (drafts === draftCache.drafts && writes === draftCache.writes && !saved) return;
  draftCache = { drafts, writes, revision: draftCache.revision + Number(saved) };
  for (const listener of draftSubscribers) listener();
}

function OutlineThumbnail({ profile }: { profile: Profile }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (!ctx) return;
    const { width, height, x, y } = profileBounds(profile);
    ctx.clearRect(0, 0, 96, 76);
    if (width <= 0 || height <= 0) return;
    const scale = Math.min(80 / width, 60 / height);
    const left = (96 - width * scale) / 2;
    const top = (76 - height * scale) / 2;
    ctx.beginPath();
    for (const loop of [profile.outer, ...profile.holes]) {
      loop.forEach(([px, py], index) => {
        const sx = left + (px - x) * scale;
        const sy = top + (py - y) * scale;
        if (index === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      });
      ctx.closePath();
    }
    ctx.fillStyle = '#285568';
    ctx.fill('evenodd');
    ctx.strokeStyle = '#8ce9f5';
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }, [profile]);
  return <canvas ref={canvas} width={96} height={76} aria-hidden="true" />;
}

function localDate() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

function snapshotDimensions(recipe: ProjectRecipe) {
  const width = (recipe.width_mm * (recipe.design?.scale_percent ?? 100)) / 100;
  const thickness = (recipe.thickness_mm * (recipe.design?.thickness_percent ?? 100)) / 100;
  return `${Number(width.toFixed(2))} mm wide · ${Number(thickness.toFixed(2))} mm thick`;
}

function ProjectDetails({
  project,
  draft,
  unsaved,
  onDraftChange,
  disabled,
  canOpen,
  onOpen,
  onUpdate,
  onRemove,
}: {
  project: LibraryProject;
  draft: ProjectDraft;
  unsaved: boolean;
  onDraftChange: (patch: Partial<ProjectDraft>) => void;
  disabled: boolean;
  canOpen: boolean;
  onOpen: (recipe: ProjectRecipe) => void;
  onUpdate: (update: ProjectUpdate, message: string) => Promise<boolean>;
  onRemove: () => void;
}) {
  const { status, tags, notes, date, outcome, attemptNotes } = draft;
  const [confirmRemove, setConfirmRemove] = useState(false);
  const { recipe } = project;

  return (
    <section className="project-library-details" aria-label="Selected project details">
      <div className="project-library-record">
        <h3>{recipe.name}</h3>
        <p>
          Saved{' '}
          {new Date(project.savedAt).toLocaleString(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
          })}
        </p>
        <div className="project-library-actions">
          <button
            type="button"
            className="primary-button"
            disabled={disabled || !canOpen}
            onClick={() => onOpen(recipe)}
          >
            <ArrowSquareOut size={17} aria-hidden="true" /> Open in workbench
          </button>
          <button
            type="button"
            className="outlined-button"
            disabled={disabled}
            onClick={() => downloadProjectRecipe(recipe)}
          >
            <DownloadSimple size={17} aria-hidden="true" /> Download recipe
          </button>
        </div>
        <p>Opening replaces the current workbench draft after the saved version rebuilds.</p>
        {unsaved && (
          <p role="status">
            Unsaved edits stay in this tab when switching projects or closing the project library.
            Save details or record the print attempt to keep them after a page reload.
          </p>
        )}
      </div>

      <form
        className="project-library-form"
        onSubmit={(event) => {
          event.preventDefault();
          void onUpdate(projectDetailsUpdate(project, draft), 'Project details saved.');
        }}
      >
        <h4>Project details</h4>
        <fieldset disabled={disabled}>
          <label>
            Print status
            <select
              value={status}
              onChange={(event) => onDraftChange({ status: event.target.value as PrintStatus })}
            >
              {PRINT_STATUSES.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <label>
            Tags (comma separated)
            <input
              value={tags}
              maxLength={240}
              onChange={(event) => onDraftChange({ tags: event.target.value })}
            />
          </label>
          <label>
            Project notes
            <textarea
              rows={2}
              value={notes}
              maxLength={1600}
              onChange={(event) => onDraftChange({ notes: event.target.value })}
            />
          </label>
          <button type="submit" className="outlined-button">
            Save details
          </button>
        </fieldset>
      </form>

      <form
        className="project-library-form"
        onSubmit={(event) => {
          event.preventDefault();
          void onUpdate(
            { attempt: { date, outcome, notes: attemptNotes.trim() } },
            'Print attempt recorded.',
          );
        }}
      >
        <h4>Print history</h4>
        {project.attempts.length > 0 && (
          <ul className="project-library-attempts" aria-label="Recorded print attempts">
            {[...project.attempts].reverse().map((attempt, index) => (
              <li key={project.attempts.length - index}>
                <time dateTime={attempt.date}>{attempt.date}</time>
                <strong>{attempt.outcome}</strong>
                {attempt.notes && <p>{attempt.notes}</p>}
              </li>
            ))}
          </ul>
        )}
        <fieldset disabled={disabled}>
          <label>
            Print date
            <input
              type="date"
              required
              value={date}
              onChange={(event) => onDraftChange({ date: event.target.value })}
            />
          </label>
          <label>
            Outcome
            <select
              value={outcome}
              onChange={(event) =>
                onDraftChange({ outcome: event.target.value as ProjectDraft['outcome'] })
              }
            >
              {PRINT_OUTCOMES.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <label>
            Print notes
            <textarea
              rows={2}
              value={attemptNotes}
              maxLength={1600}
              onChange={(event) => onDraftChange({ attemptNotes: event.target.value })}
            />
          </label>
          <button type="submit" className="outlined-button">
            Record print attempt
          </button>
        </fieldset>
      </form>

      <div className="project-library-actions">
        {confirmRemove ? (
          <>
            <span>Remove this snapshot and its print history?</span>
            <button
              type="button"
              className="outlined-button"
              disabled={disabled}
              onClick={onRemove}
            >
              Remove snapshot
            </button>
            <button
              type="button"
              className="text-button"
              disabled={disabled}
              onClick={() => setConfirmRemove(false)}
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            type="button"
            className="text-button"
            disabled={disabled}
            onClick={() => setConfirmRemove(true)}
          >
            <Trash size={17} aria-hidden="true" /> Remove from library
          </button>
        )}
      </div>
    </section>
  );
}

export default function ProjectLibrary({
  canSave,
  canOpen,
  getRecipe,
  onOpen,
}: {
  canSave: boolean;
  canOpen: boolean;
  getRecipe: () => ProjectRecipe;
  onOpen: (recipe: ProjectRecipe) => void;
}) {
  const [projects, setProjects] = useState<LibraryProject[]>([]);
  const completedRead = useRef<{ projects: LibraryProject[]; writes: ProjectWriteMap } | null>(
    null,
  );
  const { drafts, writes, revision } = useSyncExternalStore(subscribeDrafts, readDraftCache);
  const [today] = useState(localDate);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<PrintStatus | ''>('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [pending, setPending] = useState(false);
  const pendingRef = useRef(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  function editDraft(project: LibraryProject, patch: Partial<ProjectDraft>) {
    try {
      keepDrafts(patchProjectDraft(draftCache.drafts, project, patch, today, draftCache.writes));
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not keep these edits.');
    }
  }

  useEffect(() => {
    let active = true;
    const observed = draftCache.writes;
    void listLibraryProjects().then(
      (list) => {
        if (!active) return;
        completedRead.current = { projects: list, writes: observed };
        setProjects(list);
        setLoadError(false);
        setLoading(false);
      },
      () => {
        if (!active) return;
        setLoadError(true);
        setLoading(false);
      },
    );
    return () => {
      active = false;
    };
  }, [revision]);

  useEffect(() => {
    const read = completedRead.current;
    if (!read || read.projects !== projects) return;
    completedRead.current = null;
    const acknowledged = acknowledgeProjectWrites(
      draftCache.drafts,
      draftCache.writes,
      read.writes,
      projects,
      today,
    );
    keepDrafts(acknowledged.drafts, false, acknowledged.writes);
  }, [projects, today]);

  const words = query.trim().toLowerCase().split(/\s+/);
  const visible = projects.filter((project) => {
    const searchable = [project.recipe.name, ...project.tags].join(' ').toLowerCase();
    return (
      (!filter || filter === project.status) && words.every((word) => searchable.includes(word))
    );
  });
  const selected = visible.find(({ id }) => id === selectedId) ?? visible[0];

  async function run(operation: () => Promise<void>) {
    if (pendingRef.current) return false;
    pendingRef.current = true;
    setPending(true);
    setFeedback('');
    setError('');
    try {
      await operation();
      return true;
    } catch (err) {
      setError(
        err instanceof Error && err.name === 'Error'
          ? err.message
          : 'The library could not save this change. Check browser storage and try again.',
      );
      return false;
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  }

  function keepProject(project: LibraryProject) {
    setProjects((previous) => {
      if (previous.some(({ id }) => id === project.id))
        return previous.map((entry) => (entry.id === project.id ? project : entry));
      return [project, ...previous];
    });
  }

  return (
    <div className="project-library">
      <div className="project-library-toolbar">
        <p>Keep editable flat-part snapshots and print records in this browser.</p>
        <button
          type="button"
          className="primary-button"
          disabled={!canSave || loading || loadError || pending}
          onClick={() =>
            void run(async () => {
              const { project, created } = await saveLibraryProject(getRecipe());
              keepProject(project);
              keepDrafts(draftCache.drafts, true);
              setSelectedId(project.id);
              setQuery('');
              setFilter('');
              setFeedback(
                created ? 'Project snapshot saved.' : 'This snapshot is already in your library.',
              );
            })
          }
        >
          <Plus size={18} aria-hidden="true" /> Save current snapshot
        </button>
      </div>
      {error && (
        <p role="alert" className="project-library-error">
          {error}
        </p>
      )}
      {feedback && (
        <p role="status" className="project-library-feedback">
          {feedback}
        </p>
      )}
      {loading ? (
        <p role="status">Loading saved projects…</p>
      ) : loadError ? (
        <p role="alert" className="project-library-error">
          Could not read the project library. Check that this browser allows site storage.
        </p>
      ) : projects.length === 0 ? (
        <p className="project-library-empty">
          No saved projects yet. Save a snapshot once your outline and dimensions are ready.
        </p>
      ) : (
        <div className="project-library-grid">
          <aside aria-label="Browse saved projects">
            <div className="project-library-filters">
              <label>
                Search projects
                <input
                  type="search"
                  placeholder="Name or tag"
                  value={query}
                  disabled={pending}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              <label>
                Filter by print status
                <select
                  value={filter}
                  disabled={pending}
                  onChange={(event) => setFilter(event.target.value as PrintStatus | '')}
                >
                  <option value="">All statuses</option>
                  {PRINT_STATUSES.map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
            </div>
            {visible.length > 0 ? (
              <ul className="project-library-list" aria-label="Saved projects">
                {visible.map((project) => (
                  <li key={project.id}>
                    <button
                      type="button"
                      aria-pressed={project.id === selected?.id}
                      disabled={pending}
                      onClick={() => setSelectedId(project.id)}
                    >
                      <OutlineThumbnail profile={project.recipe.profile} />
                      <span>
                        <strong>{project.recipe.name}</strong>
                        <small>{snapshotDimensions(project.recipe)}</small>
                        <small>{project.status}</small>
                        {project.tags.length > 0 && <small>{project.tags.join(', ')}</small>}
                        {projectDraftChanged(project, drafts, today, writes) && (
                          <small>Unsaved edits</small>
                        )}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="project-library-empty" role="status">
                No projects match your filters.
              </p>
            )}
          </aside>
          {selected && (
            <ProjectDetails
              key={selected.id}
              project={selected}
              draft={readProjectDraft(selected, drafts, today)}
              unsaved={projectDraftChanged(selected, drafts, today, writes)}
              onDraftChange={(patch) => editDraft(selected, patch)}
              disabled={pending}
              canOpen={canOpen}
              onOpen={onOpen}
              onUpdate={(update, message) =>
                run(async () => {
                  const submitted = draftCache.drafts;
                  const requestedUpdate =
                    'attempt' in update
                      ? update
                      : projectDetailsWrite(selected, submitted, today, draftCache.writes);
                  const begun = beginProjectWrite(draftCache.writes, selected, ++writeToken);
                  keepDrafts(draftCache.drafts, false, begun.writes);
                  try {
                    const updated = await updateLibraryProject(selected.id, requestedUpdate);
                    if (!updated) {
                      setProjects((previous) => previous.filter(({ id }) => id !== selected.id));
                      throw new Error('This snapshot was removed in another tab.');
                    }
                    keepProject(updated);
                    keepDrafts(
                      clearSavedProjectDraft(
                        draftCache.drafts,
                        submitted,
                        selected.id,
                        'attempt' in update ? 'attempt' : 'details',
                      ),
                    );
                    setFeedback(message);
                  } finally {
                    keepDrafts(
                      draftCache.drafts,
                      true,
                      finishProjectWrite(draftCache.writes, begun.write),
                    );
                  }
                })
              }
              onRemove={() =>
                void run(async () => {
                  await removeLibraryProject(selected.id);
                  keepDrafts(clearProjectDraft(draftCache.drafts, selected.id, 'all'), true);
                  setProjects((previous) => previous.filter(({ id }) => id !== selected.id));
                  setFeedback('Project snapshot removed.');
                })
              }
            />
          )}
        </div>
      )}
    </div>
  );
}
