import { useEffect, useRef, useState } from 'react';
import { ArrowSquareOut, DownloadSimple, Plus, Trash } from '@phosphor-icons/react';
import {
  listLibraryProjects,
  PRINT_OUTCOMES,
  PRINT_STATUSES,
  removeLibraryProject,
  saveLibraryProject,
  updateLibraryProject,
} from './projectLibrary';
import type {
  LibraryProject,
  PrintAttempt,
  PrintStatus,
  ProjectDetailsUpdate,
  ProjectUpdate,
} from './projectLibrary';
import { downloadProjectRecipe, profileBounds } from './projectRecipe';
import type { Profile, ProjectRecipe } from './types';
import './ProjectLibrary.css';

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
  disabled,
  canOpen,
  onOpen,
  onUpdate,
  onRemove,
}: {
  project: LibraryProject;
  disabled: boolean;
  canOpen: boolean;
  onOpen: (recipe: ProjectRecipe) => void;
  onUpdate: (update: ProjectUpdate, message: string) => Promise<boolean>;
  onRemove: () => void;
}) {
  const [status, setStatus] = useState(project.status);
  const storedTags = project.tags.join(', ');
  const [tags, setTags] = useState(storedTags);
  const [notes, setNotes] = useState(project.notes);
  const [date, setDate] = useState(localDate);
  const [outcome, setOutcome] = useState<PrintAttempt['outcome']>('Printed');
  const [attemptNotes, setAttemptNotes] = useState('');
  const [confirmRemove, setConfirmRemove] = useState(false);
  const { recipe } = project;

  useEffect(() => {
    setStatus(project.status);
  }, [project.status]);
  useEffect(() => {
    setTags(storedTags);
  }, [storedTags]);
  useEffect(() => {
    setNotes(project.notes);
  }, [project.notes]);

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
      </div>

      <form
        className="project-library-form"
        onSubmit={(event) => {
          event.preventDefault();
          const distinctTags = new Map<string, string>();
          for (const tag of tags
            .split(',')
            .map((value) => value.trim())
            .filter(Boolean)) {
            if (!distinctTags.has(tag.toLowerCase())) distinctTags.set(tag.toLowerCase(), tag);
          }
          const savedTags = [...distinctTags.values()];
          const update: ProjectDetailsUpdate = {};
          if (status !== project.status) update.status = status;
          if (savedTags.join(', ') !== storedTags) update.tags = savedTags;
          if (notes.trim() !== project.notes) update.notes = notes.trim();
          void onUpdate(update, 'Project details saved.');
        }}
      >
        <h4>Project details</h4>
        <fieldset disabled={disabled}>
          <label>
            Print status
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value as PrintStatus)}
            >
              {PRINT_STATUSES.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <label>
            Tags (comma separated)
            <input value={tags} maxLength={240} onChange={(event) => setTags(event.target.value)} />
          </label>
          <label>
            Project notes
            <textarea
              rows={2}
              value={notes}
              maxLength={1600}
              onChange={(event) => setNotes(event.target.value)}
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
          ).then((saved) => {
            if (saved) setAttemptNotes('');
          });
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
              onChange={(event) => setDate(event.target.value)}
            />
          </label>
          <label>
            Outcome
            <select
              value={outcome}
              onChange={(event) => setOutcome(event.target.value as PrintAttempt['outcome'])}
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
              onChange={(event) => setAttemptNotes(event.target.value)}
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
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<PrintStatus | ''>('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [pending, setPending] = useState(false);
  const pendingRef = useRef(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    void listLibraryProjects().then(
      (list) => {
        if (!active) return;
        setProjects(list);
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
  }, []);

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
                {visible.map(({ id, recipe, tags, status }) => (
                  <li key={id}>
                    <button
                      type="button"
                      aria-pressed={id === selected?.id}
                      disabled={pending}
                      onClick={() => setSelectedId(id)}
                    >
                      <OutlineThumbnail profile={recipe.profile} />
                      <span>
                        <strong>{recipe.name}</strong>
                        <small>{snapshotDimensions(recipe)}</small>
                        <small>{status}</small>
                        {tags.length > 0 && <small>{tags.join(', ')}</small>}
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
              disabled={pending}
              canOpen={canOpen}
              onOpen={onOpen}
              onUpdate={(update, message) =>
                run(async () => {
                  const updated = await updateLibraryProject(selected.id, update);
                  if (!updated) {
                    setProjects((previous) => previous.filter(({ id }) => id !== selected.id));
                    throw new Error('This snapshot was removed in another tab.');
                  }
                  keepProject(updated);
                  setFeedback(message);
                })
              }
              onRemove={() =>
                void run(async () => {
                  await removeLibraryProject(selected.id);
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
