import { useEffect, useRef, useState } from 'react';
import {
  MagnifyingGlass,
  PushPin,
  BookOpen,
  ArrowUpRight,
  DownloadSimple,
  UploadSimple,
  ArrowCounterClockwise,
  CaretDown,
} from '@phosphor-icons/react';
import AppHeader from './AppHeader';
import {
  EMPTY_NOTEBOOK,
  LOCAL_GUIDES,
  NOTEBOOK_KEY,
  parseNotebook,
  searchGuides,
} from './knowledge';
import type { Notebook } from './knowledge';
import { readStudioJson, saveStudioJson } from './studioFiles';
import './KnowledgeStudio.css';

function queryFromHash(): string | null {
  const hash = window.location.hash.slice(1);
  const separator = hash.indexOf('?');
  if (separator < 0 || hash.slice(0, separator) !== 'knowledge') return null;
  // A plain studio switch preserves the draft search. An explicit search=,
  // including an empty value, is a request from a deep link or the launcher.
  return new URLSearchParams(hash.slice(separator + 1)).get('search');
}
function loadNotebook() {
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(NOTEBOOK_KEY);
    return {
      notebook: raw ? parseNotebook(JSON.parse(raw)) : EMPTY_NOTEBOOK,
      error: '',
      recovery: null,
    };
  } catch {
    return {
      notebook: EMPTY_NOTEBOOK,
      error: raw
        ? 'The saved notebook could not be read. Export its recovery data before starting fresh.'
        : 'Browser storage is unavailable. You can use notes here and export them.',
      recovery: raw,
    };
  }
}

export default function KnowledgeStudio() {
  const [initial] = useState(loadNotebook);
  const [notebook, setNotebook] = useState(initial.notebook);
  const [storageMessage, setStorageMessage] = useState(
    initial.error || 'Notes and pins save in this browser. Export a backup to keep them elsewhere.',
  );
  const [storageFailed, setStorageFailed] = useState(!!initial.error);
  const [recovery, setRecovery] = useState(initial.recovery);
  const [dirty, setDirty] = useState(false);
  const [query, setQuery] = useState(() => queryFromHash() ?? '');
  const [category, setCategory] = useState('All guides');
  const [pinnedOnly, setPinnedOnly] = useState(false);
  const [selectedId, setSelectedId] = useState('capture');
  const [importError, setImportError] = useState('');
  const [importing, setImporting] = useState(false);
  const [undoImport, setUndoImport] = useState<Notebook | null>(null);
  const [showLocal, setShowLocal] = useState(false);
  const [localDocument, setLocalDocument] = useState<{
    slug: string;
    title: string;
    content: string;
  } | null>(null);
  const [localError, setLocalError] = useState('');
  const fileInput = useRef<HTMLInputElement>(null);
  const importSequence = useRef(0);
  useEffect(
    () => () => {
      importSequence.current += 1;
    },
    [],
  );
  const results = searchGuides(query, category, pinnedOnly ? notebook.pins : undefined);
  const article = results.find((item) => item.id === selectedId) ?? results[0];
  const docSlug = article ? (LOCAL_GUIDES[article.doc] ?? article.doc) : '';

  useEffect(() => {
    const update = () => {
      const requested = queryFromHash();
      if (requested !== null) setQuery(requested);
    };
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  useEffect(() => {
    if (!dirty || recovery) return;
    try {
      localStorage.setItem(NOTEBOOK_KEY, JSON.stringify(notebook));
      setStorageMessage(
        'Saved locally in this browser. Export a backup before clearing site data.',
      );
      setStorageFailed(false);
    } catch {
      setStorageMessage(
        'Could not save to browser storage. Your current notes remain in this view; export a notebook now.',
      );
      setStorageFailed(true);
    }
  }, [notebook, dirty, recovery]);
  useEffect(() => {
    if (!showLocal || !docSlug) return;
    const request = new AbortController();
    setLocalDocument(null);
    setLocalError('');
    void (async () => {
      try {
        const response = await fetch(`/api/docs/${encodeURIComponent(docSlug)}`, {
          signal: request.signal,
        });
        if (!response.ok)
          throw new Error(
            'This local guide is unavailable. You can still use the embedded article or open its online source.',
          );
        const data = (await response.json()) as {
          slug?: unknown;
          title?: unknown;
          content?: unknown;
        };
        if (
          data.slug !== docSlug ||
          typeof data.title !== 'string' ||
          typeof data.content !== 'string'
        )
          throw new Error('The local guide returned an unreadable response.');
        if (!request.signal.aborted)
          setLocalDocument({ slug: docSlug, title: data.title, content: data.content });
      } catch (reason) {
        if (!request.signal.aborted)
          setLocalError(
            reason instanceof Error ? reason.message : 'The local guide could not be loaded.',
          );
      }
    })();
    return () => request.abort();
  }, [showLocal, docSlug]);
  function updateNotebook(next: Notebook) {
    setNotebook(next);
    setDirty(true);
    setImportError('');
  }
  async function importNotebook(file?: File) {
    if (!file) return;
    const sequence = ++importSequence.current;
    setImporting(true);
    setImportError('');
    try {
      const next = parseNotebook(await readStudioJson(file));
      if (sequence !== importSequence.current) return;
      setUndoImport(notebook);
      setRecovery(null);
      updateNotebook(next);
    } catch (reason) {
      if (sequence !== importSequence.current) return;
      setImportError(
        reason instanceof Error ? reason.message : 'The notebook could not be imported.',
      );
    } finally {
      if (sequence === importSequence.current) setImporting(false);
    }
  }
  const pinCount = notebook.pins.length;
  return (
    <div className="app-shell knowledge-studio">
      <AppHeader
        studio="knowledge"
        projectName={<span className="studio-project-label">Knowledge base</span>}
      />
      <main id="knowledge" className="knowledge-main">
        <div className="knowledge-heading">
          <div>
            <p className="knowledge-eyebrow">A practical field guide</p>
            <h1>Knowledge base</h1>
            <p>Find the next step. Understand the limits. Keep your own record.</p>
          </div>
          <a className="outlined-button" href="#science">
            Explore Science lab <ArrowUpRight size={18} />
          </a>
        </div>
        <div className="knowledge-searchbar">
          <label className="knowledge-search">
            <MagnifyingGlass size={23} />
            <input
              type="search"
              placeholder="Search capture, measurement, slicing…"
              aria-label="Search knowledge base"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label className="knowledge-category">
            Topic
            <select
              aria-label="Knowledge topic"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              {['All guides', 'Getting started', 'Measurement', 'Printing', 'Recovery'].map(
                (item) => (
                  <option key={item}>{item}</option>
                ),
              )}
            </select>
          </label>
          <label className="knowledge-pinned-filter">
            <input
              type="checkbox"
              checked={pinnedOnly}
              onChange={(event) => setPinnedOnly(event.target.checked)}
            />
            Pinned only <span>{pinCount}</span>
          </label>
        </div>
        <div className="knowledge-layout">
          <aside className="knowledge-index" aria-label="Guide results">
            <p className="knowledge-count" role="status">
              {results.length} {results.length === 1 ? 'guide' : 'guides'}
              {query ? ` matching “${query}”` : ' to explore'}
            </p>
            {results.map((guide) => (
              <button
                key={guide.id}
                aria-pressed={guide.id === article?.id}
                onClick={() => {
                  setSelectedId(guide.id);
                  setShowLocal(false);
                }}
              >
                <span className="knowledge-list-category">
                  {guide.category}
                  {notebook.pins.includes(guide.id) && (
                    <PushPin size={13} weight="fill" aria-label="Pinned" />
                  )}
                </span>{' '}
                <strong>{guide.title}</strong> <span>{guide.summary}</span>
              </button>
            ))}
          </aside>
          {article ? (
            <article className="knowledge-article" aria-labelledby="knowledge-article-title">
              <div className="knowledge-article-heading">
                <div>
                  <p className="knowledge-eyebrow">{article.category}</p>
                  <h2 id="knowledge-article-title">{article.title}</h2>
                  <p>{article.summary}</p>
                </div>
                <button
                  className="knowledge-pin"
                  disabled={!!recovery || importing}
                  aria-pressed={notebook.pins.includes(article.id)}
                  aria-label={notebook.pins.includes(article.id) ? 'Unpin article' : 'Pin article'}
                  onClick={() =>
                    updateNotebook({
                      ...notebook,
                      pins: notebook.pins.includes(article.id)
                        ? notebook.pins.filter((id) => id !== article.id)
                        : [...notebook.pins, article.id],
                    })
                  }
                >
                  <PushPin
                    size={21}
                    weight={notebook.pins.includes(article.id) ? 'fill' : 'regular'}
                  />
                </button>
              </div>
              <ol className="knowledge-steps">
                {article.steps.map((step, index) => (
                  <li key={step}>
                    <span aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
                    <p>{step}</p>
                  </li>
                ))}
              </ol>
              <div className="knowledge-assumptions">
                <h3>Know the limits</h3>
                <p>{article.assumptions}</p>
              </div>
              <div className="knowledge-article-actions">
                <a className="outlined-button" href={article.action.href}>
                  {article.action.label}
                  <ArrowUpRight size={17} />
                </a>
                <button
                  className="text-button"
                  aria-expanded={showLocal}
                  onClick={() => setShowLocal(!showLocal)}
                >
                  <BookOpen size={18} />
                  Read detailed local guide
                  <CaretDown size={16} />
                </button>
              </div>
              {showLocal && (
                <section className="knowledge-local-guide" aria-label="Detailed local guide">
                  <div>
                    <strong>From this installed checkout</strong>
                    <a href={`/api/docs/${encodeURIComponent(docSlug)}/download`} download>
                      Download Markdown <DownloadSimple size={16} />
                    </a>
                  </div>
                  {localError ? (
                    <p role="alert">{localError}</p>
                  ) : localDocument?.slug === docSlug ? (
                    <>
                      <h3>{localDocument.title}</h3>
                      <pre>{localDocument.content}</pre>
                    </>
                  ) : (
                    <p role="status">Loading local guide…</p>
                  )}
                </section>
              )}
              <div className="knowledge-sources">
                <h3>Sources &amp; further reading</h3>
                <a href={`/api/docs/${encodeURIComponent(docSlug)}/download`} download>
                  Installed project guide · Markdown download
                </a>
                {article.sources?.map((source) => (
                  <a key={source.url} href={source.url} target="_blank" rel="noreferrer">
                    {source.label} · online ↗
                  </a>
                ))}
              </div>
              <section className="knowledge-notes" aria-label="Personal notebook">
                <div>
                  <h3>Your field notes</h3>
                  <span>Local to this browser</span>
                </div>
                <label htmlFor="knowledge-note">Your notes for {article.title}</label>
                <textarea
                  id="knowledge-note"
                  value={notebook.notes[article.id] ?? ''}
                  maxLength={10_000}
                  disabled={!!recovery || importing}
                  placeholder="Record your measurements, material, process settings or next test…"
                  onChange={(event) =>
                    updateNotebook({
                      ...notebook,
                      notes: { ...notebook.notes, [article.id]: event.target.value },
                    })
                  }
                />
                <p
                  className={storageFailed ? 'knowledge-save-error' : 'knowledge-save-state'}
                  role="status"
                >
                  {storageMessage}
                </p>
                {recovery && (
                  <div className="knowledge-recovery">
                    <button
                      className="outlined-button"
                      onClick={() =>
                        saveStudioJson(
                          { format: 'unreadable-notebook-recovery', raw: recovery },
                          'pictures-to-cad-notebook-recovery.json',
                        )
                      }
                    >
                      Export recovery data
                    </button>
                    <button
                      className="text-button"
                      disabled={importing}
                      onClick={() => {
                        setRecovery(null);
                        updateNotebook({ ...EMPTY_NOTEBOOK, pins: [], notes: {} });
                      }}
                    >
                      Start a fresh notebook
                    </button>
                  </div>
                )}
                <div className="knowledge-notebook-actions">
                  <button
                    className="outlined-button"
                    onClick={() => saveStudioJson(notebook, 'pictures-to-cad-notebook.json')}
                    disabled={!!recovery || importing}
                  >
                    <DownloadSimple size={17} />
                    Export notebook
                  </button>
                  <button
                    className="outlined-button"
                    onClick={() => fileInput.current?.click()}
                    disabled={importing}
                  >
                    <UploadSimple size={17} />
                    {importing ? 'Importing…' : 'Import notebook'}
                  </button>
                  {undoImport && (
                    <button
                      className="text-button"
                      disabled={importing}
                      onClick={() => {
                        updateNotebook(undoImport);
                        setUndoImport(null);
                      }}
                    >
                      <ArrowCounterClockwise size={17} />
                      Undo notebook import
                    </button>
                  )}
                </div>
                <p className="knowledge-import-hint">
                  Import replaces notes and pins; you can undo the import in this view. Export first
                  to keep a backup.
                </p>
                <input
                  className="sr-only"
                  ref={fileInput}
                  type="file"
                  tabIndex={-1}
                  disabled={importing}
                  accept=".json,application/json"
                  aria-label="Import knowledge notebook JSON"
                  onChange={(event) => {
                    void importNotebook(event.target.files?.[0]);
                    event.target.value = '';
                  }}
                />
                {importError && (
                  <p className="knowledge-save-error" role="alert">
                    {importError}
                  </p>
                )}
              </section>
            </article>
          ) : (
            <section className="knowledge-empty">
              <BookOpen size={46} />
              <h2>No matching guides</h2>
              <p>Try a shorter search or choose another topic. Pin a guide to collect it here.</p>
              <button
                className="outlined-button"
                onClick={() => {
                  setQuery('');
                  setCategory('All guides');
                  setPinnedOnly(false);
                }}
              >
                Show all guides
              </button>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
