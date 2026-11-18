import { useEffect, useRef, useState } from 'react';
import {
  ArrowClockwise,
  ArrowRight,
  Cpu,
  DownloadSimple,
  MagnifyingGlass,
  Sparkle,
  SpinnerGap,
  WarningCircle,
} from '@phosphor-icons/react';
import AppHeader from './AppHeader';
import { useStudioActive } from './StudioActivity';
import { searchStudios } from './studioCatalog';
import { localAIRequest, notesExport } from './creative';
import { readCreativeConnection } from './creativeConnection';
import type { CreativeInput, CreativeReply, CreativeTool } from './creative';
import type { AssistantStatus } from './types';
import './CreativeStudio.css';

type SavedResult = { input: CreativeInput; reply: CreativeReply };

export default function CreativeStudio() {
  const active = useStudioActive();
  const activeRef = useRef(active);
  activeRef.current = active;
  const [tools, setTools] = useState<CreativeTool[]>([]);
  const [tool, setTool] = useState('concepts');
  const [brief, setBrief] = useState('');
  const [constraints, setConstraints] = useState('');
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [model, setModel] = useState('');
  const [checking, setChecking] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [connectionError, setConnectionError] = useState('');
  const [toolError, setToolError] = useState('');
  const [saved, setSaved] = useState<SavedResult | null>(null);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('All');
  const request = useRef<AbortController | null>(null);
  const statusRequest = useRef<AbortController | null>(null);
  const resultRef = useRef<HTMLElement>(null);
  const editorRef = useRef<HTMLElement>(null);
  const briefRef = useRef<HTMLTextAreaElement>(null);
  const toolDefinition = tools.find((item) => item.id === tool);
  const results = searchStudios(query, category);
  const changed =
    saved &&
    (saved.input.tool !== tool ||
      saved.input.brief !== brief.trim() ||
      saved.input.constraints !== constraints.trim());

  async function refresh() {
    statusRequest.current?.abort();
    const controller = new AbortController();
    statusRequest.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    setChecking(true);
    setConnectionError('');
    setToolError('');
    try {
      const result = await readCreativeConnection(controller.signal);
      if (statusRequest.current !== controller) return;
      if (result.tools) {
        const catalog = result.tools;
        setTools(catalog);
        setTool((current) =>
          catalog.some((item) => item.id === current) ? current : (catalog[0]?.id ?? ''),
        );
      }
      const connection = result.status;
      setStatus(connection);
      if (connection)
        setModel((current) =>
          connection.models.some((item) => item.name === current)
            ? current
            : (connection.recommended_model ?? ''),
        );
      setToolError(result.toolError);
      setConnectionError(result.connectionError);
    } catch (err) {
      if (statusRequest.current !== controller) return;
      setStatus(null);
      setConnectionError(
        err instanceof Error && !(err instanceof TypeError) && err.name !== 'AbortError'
          ? err.message
          : 'Could not check local AI. Start the CAD service and Ollama, then refresh.',
      );
    } finally {
      window.clearTimeout(timeout);
      if (statusRequest.current === controller) setChecking(false);
    }
  }

  useEffect(() => {
    void refresh();
    return () => {
      request.current?.abort();
      request.current = null;
      statusRequest.current?.abort();
      statusRequest.current = null;
    };
  }, []);

  async function run() {
    if (!brief.trim() || !model || !toolDefinition || pending || checking || !status?.running)
      return;
    const controller = new AbortController();
    request.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 135000);
    const input = { tool, model, brief: brief.trim(), constraints: constraints.trim() };
    setPending(true);
    setError('');
    try {
      const reply = await localAIRequest<CreativeReply>('/api/creative/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
        signal: controller.signal,
      });
      if (request.current !== controller) return;
      setSaved({ input, reply });
      const focused = document.activeElement;
      if (
        activeRef.current &&
        (!focused || focused === document.body || editorRef.current?.contains(focused))
      )
        requestAnimationFrame(() => {
          if (activeRef.current) resultRef.current?.focus({ preventScroll: true });
        });
    } catch (err) {
      if (request.current !== controller) return;
      setError(
        err instanceof Error && !(err instanceof TypeError) && err.name !== 'AbortError'
          ? err.message
          : 'The request could not finish. Your brief is still here; refresh the connection or try another model.',
      );
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setPending(false);
      }
    }
  }

  function cancel() {
    request.current?.abort();
    request.current = null;
    setPending(false);
    setError(
      'Stopped waiting. Ollama may still finish this request; wait a moment before trying again.',
    );
  }

  function download() {
    if (!saved) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(notesExport(saved.input, saved.reply), null, 2)], {
        type: 'application/json',
      }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = 'creative-notes.json';
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <div className="app-shell creative-shell">
      <AppHeader studio="creative" projectName="Ideas & experiments" />
      <main className="creative-main" id="creative-main">
        <div className="creative-heading">
          <div>
            <p className="creative-eyebrow">CREATIVE WORKSPACE</p>
            <h1>Make room for your next idea.</h1>
            <p>Explore possibilities, refine a direction, then take it into your making tools.</p>
          </div>
          <span className="creative-local">
            <Cpu size={19} /> Powered on your machine
          </span>
        </div>
        <div className="creative-layout">
          <section
            ref={editorRef}
            className="creative-panel creative-editor"
            aria-labelledby="brief-title"
          >
            <p className="creative-eyebrow">01 / THINK IT THROUGH</p>
            <h2 id="brief-title">Start with an idea</h2>
            <div className="creative-tool-options" aria-label="Creative text tools">
              {tools.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={item.id === tool}
                  disabled={pending}
                  onClick={() => setTool(item.id)}
                >
                  {item.name}
                </button>
              ))}
            </div>
            <p className="creative-help">
              {toolDefinition?.description ??
                (checking ? 'Discovering the local creative tools…' : 'Choose a creative tool.')}
            </p>
            {toolError && (
              <p className="creative-error" role="alert">
                {toolError}
              </p>
            )}
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void run();
              }}
            >
              <label htmlFor="creative-brief">What would you like to make?</label>
              <textarea
                ref={briefRef}
                id="creative-brief"
                rows={5}
                maxLength={2400}
                required
                value={brief}
                disabled={pending}
                onChange={(event) => setBrief(event.target.value)}
                placeholder="An object, a mood, a problem to solve. Start anywhere."
              />
              <div className="creative-input-footer">
                <span>{brief.length}/2400</span>
                <button
                  type="button"
                  className="creative-text-button"
                  disabled={!toolDefinition || pending}
                  onClick={() => {
                    setBrief(toolDefinition!.starter);
                    briefRef.current?.focus();
                  }}
                >
                  Try an example
                </button>
              </div>
              <label htmlFor="creative-constraints">
                Constraints & preferences <span>(optional)</span>
              </label>
              <textarea
                id="creative-constraints"
                rows={3}
                maxLength={1600}
                value={constraints}
                disabled={pending}
                onChange={(event) => setConstraints(event.target.value)}
                placeholder="Style, intended use, measured sizes, available materials…"
              />
              <div className="creative-connection">
                <div className="creative-connection-title">
                  <strong>
                    <Cpu size={18} /> Local AI
                  </strong>
                  <button
                    type="button"
                    aria-label="Refresh local AI connection"
                    disabled={checking}
                    onClick={() => void refresh()}
                  >
                    <ArrowClockwise className={checking ? 'creative-spin' : ''} size={18} /> Refresh
                  </button>
                </div>
                <p role="status">
                  {checking
                    ? 'Checking Ollama and local chat models…'
                    : connectionError || status?.detail || 'Local AI is unavailable.'}
                </p>
                <label htmlFor="creative-model">Chat model</label>
                <select
                  id="creative-model"
                  value={model}
                  disabled={pending || checking || !status?.models.length}
                  onChange={(event) => setModel(event.target.value)}
                >
                  {!status?.models.length && <option value="">No verified chat model</option>}
                  {status?.models.map((item) => (
                    <option key={item.name} value={item.name}>
                      {item.name} · {(item.size_bytes / 1e9).toFixed(1)} GB
                    </option>
                  ))}
                </select>
                <details>
                  <summary>Connection & AI requirements</summary>
                  <p>
                    Run Ollama on the CAD service’s machine, then refresh. Check it with{' '}
                    <code>./scripts/ollama.sh check</code>. If it is stopped, run{' '}
                    <code>ollama serve</code>.
                  </p>
                  <p>
                    This workspace sends only your brief and constraints to a local chat model.
                    Photos stay in their studios. Depth estimation and photo similarity use separate
                    optional models.
                  </p>
                </details>
              </div>
              <div className="creative-run">
                <button
                  className="creative-primary"
                  type="submit"
                  disabled={
                    pending ||
                    checking ||
                    !brief.trim() ||
                    !model ||
                    !toolDefinition ||
                    !status?.running
                  }
                >
                  {pending ? (
                    <SpinnerGap className="creative-spin" size={20} />
                  ) : (
                    <Sparkle size={20} />
                  )}{' '}
                  {pending ? 'Exploring your idea…' : 'Generate creative notes'}
                </button>
                {pending && (
                  <button type="button" onClick={cancel}>
                    Stop waiting
                  </button>
                )}
              </div>
              <p className="creative-help">
                Your draft stays here when switching studios. Save generated notes to keep a copy.
              </p>
              {error && (
                <p className="creative-error" role="alert">
                  <WarningCircle size={18} />
                  {error}
                </p>
              )}
            </form>
          </section>
          <section
            className="creative-panel creative-result"
            aria-labelledby="notes-title"
            ref={resultRef}
            tabIndex={-1}
          >
            <div className="creative-result-heading">
              <p className="creative-eyebrow">02 / FIND A DIRECTION</p>
              {saved && (
                <button type="button" onClick={download}>
                  <DownloadSimple size={18} /> Save notes
                </button>
              )}
            </div>
            <h2 id="notes-title">
              {saved?.reply.notes.title ?? 'A little spark. A practical next step.'}
            </h2>
            {saved ? (
              <>
                {changed && (
                  <p className="creative-notice">
                    These notes belong to your earlier brief. Generate again to explore your
                    changes.
                  </p>
                )}
                <p>{saved.reply.notes.summary}</p>
                {saved.reply.notes.sections.map((section, index) => (
                  <article className="creative-note" key={index}>
                    <span className="creative-note-number">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <div>
                      <h3>{section.title}</h3>
                      <p>{section.body}</p>
                    </div>
                  </article>
                ))}
                <h3>Next steps</h3>
                <ol className="creative-steps">
                  {saved.reply.notes.next_steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ol>
                <details className="creative-source">
                  <summary>Brief behind these notes</summary>
                  <p>{saved.input.brief}</p>
                  {saved.input.constraints && <p>{saved.input.constraints}</p>}
                </details>
                <p className="creative-help">
                  {saved.reply.model} · {saved.reply.elapsed_seconds.toFixed(1)} seconds
                </p>
                {saved.reply.warnings.map((warning) => (
                  <p className="creative-help" key={warning}>
                    {warning}
                  </p>
                ))}
              </>
            ) : (
              <div className="creative-empty">
                <Sparkle size={48} weight="light" />
                <p>
                  Describe what you’re imagining. Local AI will help turn it into directions you can
                  compare, questions to resolve, and steps you can try.
                </p>
                <div className="creative-empty-tags">
                  <span>Objects & patterns</span>
                  <span>Photo reliefs</span>
                  <span>Making experiments</span>
                </div>
                <p className="creative-help">
                  Creative notes are concepts. Review dimensions, fit and material choices before
                  making.
                </p>
              </div>
            )}
            <p className="sr-only" role="status">
              {saved ? 'Creative notes are ready.' : pending ? 'Generating creative notes.' : ''}
            </p>
          </section>
        </div>
        <section className="creative-toolkit" aria-labelledby="toolkit-title">
          <div className="creative-toolkit-heading">
            <div>
              <p className="creative-eyebrow">03 / KEEP MAKING</p>
              <h2 id="toolkit-title">Your creative toolkit</h2>
              <p>Find the right workspace for the next part of your project.</p>
            </div>
            <label className="creative-search">
              <MagnifyingGlass size={20} />
              <span className="sr-only">Find a creative workspace</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search tools, ideas, outputs…"
              />
            </label>
          </div>
          <div className="creative-filters" aria-label="Workspace categories">
            {['All', 'Make', 'Collect', 'Explore'].map((item) => (
              <button
                key={item}
                type="button"
                aria-pressed={category === item}
                onClick={() => setCategory(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <div className="creative-cards">
            {results.map((item) => (
              <a className="creative-card" href={`#${item.id}`} key={item.id}>
                <span className="creative-card-category">
                  {item.category}
                  <ArrowRight size={20} />
                </span>
                <h3>{item.name}</h3>
                <p>{item.description}</p>
                <span className="creative-requirement">{item.requirement}</span>
              </a>
            ))}
          </div>
          {!results.length && (
            <p role="status">No workspaces match. Try another search or category.</p>
          )}
        </section>
      </main>
    </div>
  );
}
