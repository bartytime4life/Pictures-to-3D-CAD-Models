import { useEffect, useRef, useState } from 'react';
import {
  ArrowClockwise,
  ArrowCounterClockwise,
  ArrowUp,
  CaretDown,
  CheckCircle,
  Cpu,
  Info,
  Sparkle,
  SpinnerGap,
} from '@phosphor-icons/react';
import type { AssistantContext, AssistantProposal, AssistantReply, AssistantStatus } from './types';
import { DESIGN_KEYS, DESIGN_LABELS, formatDesignValue } from './design';

const starters = [
  [
    'Improve my trace',
    'How can I improve my outline? Explain which trace settings to try and why.',
  ],
  ['Check my measurements', 'What measurements should I verify before building this part?'],
  [
    'Choose an export',
    'Which export should I use for CAD editing, 3D printing, or a flat cutting template?',
  ],
  [
    'Fit my printer',
    'Review my current design size and printer settings. Suggest changes only if needed to fit the build volume.',
  ],
  [
    'Change my design',
    'Help me choose size, color, material and detail settings. Explain the tradeoffs before proposing changes.',
  ],
];

const detailLabel = { coarse: 'Simplified', standard: 'Standard', fine: 'Fine' };
const thresholdLabel = (value: number) => (value === -1 ? 'Auto' : String(value));
const polarityLabel = (value: boolean) => (value ? 'Light part on dark' : 'Dark part on light');

async function assistantRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : 'The local assistant could not respond. Try again.',
    );
  return data as T;
}

export default function LocalAssistant({
  context,
  revision,
  busy,
  canUndo,
  onApply,
  onUndo,
}: {
  context: AssistantContext;
  revision: string;
  busy: boolean;
  canUndo: boolean;
  onApply: (proposal: AssistantProposal) => Promise<boolean>;
  onUndo: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [checking, setChecking] = useState(false);
  const [model, setModel] = useState('');
  const [question, setQuestion] = useState('');
  const [reply, setReply] = useState<AssistantReply | null>(null);
  const [askedQuestion, setAskedQuestion] = useState('');
  const [replyRevision, setReplyRevision] = useState('');
  const [replyContext, setReplyContext] = useState<AssistantContext | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [applied, setApplied] = useState(false);
  const [applying, setApplying] = useState(false);
  const questionInput = useRef<HTMLTextAreaElement>(null);
  const request = useRef<AbortController | null>(null);
  const statusRequest = useRef<AbortController | null>(null);
  const replyRef = useRef<HTMLDivElement>(null);
  const sectionRef = useRef<HTMLElement>(null);
  const [announcement, setAnnouncement] = useState('');

  useEffect(
    () => () => {
      request.current?.abort();
      request.current = null;
      statusRequest.current?.abort();
      statusRequest.current = null;
    },
    [],
  );

  useEffect(() => {
    if (!reply) return;
    // Move focus to the answer only from the assistant itself (or from nowhere, as when the
    // disabled Ask button dropped it). Someone who kept working elsewhere while waiting keeps
    // their place and typing; the answer is announced instead.
    const active = document.activeElement;
    if (!active || active === document.body || sectionRef.current?.contains(active)) {
      setAnnouncement('');
      replyRef.current?.focus({ preventScroll: true });
    } else setAnnouncement('The local AI answer is ready in the assistant panel.');
  }, [reply]);

  async function refresh() {
    statusRequest.current?.abort();
    const controller = new AbortController();
    statusRequest.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    setChecking(true);
    setError('');
    try {
      const result = await assistantRequest<AssistantStatus>('/api/assistant/status', {
        signal: controller.signal,
      });
      setStatus(result);
      setModel((current) =>
        result.models.some((item) => item.name === current)
          ? current
          : (result.recommended_model ?? result.models[0]?.name ?? ''),
      );
    } catch (err) {
      if (statusRequest.current !== controller) return;
      setStatus(null);
      setError(
        err instanceof DOMException && err.name === 'AbortError'
          ? 'Checking Ollama took too long. Start it on the CAD service’s machine, then refresh.'
          : err instanceof Error && !(err instanceof TypeError)
            ? err.message
            : 'Could not reach the local assistant. Check the CAD service, then refresh.',
      );
    } finally {
      window.clearTimeout(timeout);
      if (statusRequest.current === controller) setChecking(false);
    }
  }

  function toggle() {
    setExpanded((open) => !open);
    if (!expanded && !status && !checking) void refresh();
  }

  async function ask() {
    if (!question.trim() || !model || pending || busy || !status?.running) return;
    const controller = new AbortController();
    request.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 135000);
    setPending(true);
    setError('');
    setReply(null);
    setAnnouncement('');
    setApplied(false);
    setAskedQuestion(question.trim());
    const sentRevision = revision;
    const sentContext = { ...context };
    try {
      const result = await assistantRequest<AssistantReply>('/api/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, question: question.trim(), context: sentContext }),
        signal: controller.signal,
      });
      if (request.current !== controller) return;
      setReply(result);
      setReplyRevision(sentRevision);
      setReplyContext(sentContext);
    } catch (err) {
      if (request.current !== controller) return;
      setError(
        err instanceof DOMException && err.name === 'AbortError'
          ? 'The response took too long. Your CAD work is unchanged. Try a smaller model or a shorter question.'
          : err instanceof Error && !(err instanceof TypeError)
            ? err.message
            : 'Could not reach the local assistant. Your CAD work is unchanged. Refresh its connection and try again.',
      );
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller) {
        setPending(false);
        request.current = null;
      }
    }
  }

  function stopWaiting() {
    const controller = request.current;
    request.current = null;
    controller?.abort();
    setPending(false);
    setError('Stopped waiting. Ollama may still finish this request. Your CAD work is unchanged.');
  }

  const selected = status?.models.find((item) => item.name === model);
  const proposal = reply?.proposal;
  const changes: { label: string; before: string; after: string }[] = [];
  if (proposal && replyContext) {
    if (proposal.threshold !== undefined && proposal.threshold !== replyContext.threshold)
      changes.push({
        label: 'Contrast threshold',
        before: thresholdLabel(replyContext.threshold),
        after: thresholdLabel(proposal.threshold),
      });
    if (proposal.inverted !== undefined && proposal.inverted !== replyContext.inverted)
      changes.push({
        label: 'Background',
        before: polarityLabel(replyContext.inverted),
        after: polarityLabel(proposal.inverted),
      });
    if (proposal.detail !== undefined && proposal.detail !== replyContext.detail)
      changes.push({
        label: 'Outline detail',
        before: detailLabel[replyContext.detail],
        after: detailLabel[proposal.detail],
      });
    for (const key of DESIGN_KEYS) {
      const next = proposal[key];
      if (next !== undefined && next !== replyContext.design[key])
        changes.push({
          label: DESIGN_LABELS[key],
          before: formatDesignValue(key, replyContext.design[key]),
          after: formatDesignValue(key, next),
        });
    }
  }
  const changesTrace =
    !!proposal &&
    !!replyContext &&
    ((proposal.threshold !== undefined && proposal.threshold !== replyContext.threshold) ||
      (proposal.inverted !== undefined && proposal.inverted !== replyContext.inverted) ||
      (proposal.detail !== undefined && proposal.detail !== replyContext.detail));
  const outdated = !!reply && revision !== replyRevision;
  const ready = !!status?.running && !!selected;

  return (
    <section
      ref={sectionRef}
      className={`local-assistant ${expanded ? 'expanded' : ''}`}
      aria-label="Local AI assistant"
    >
      <p className="sr-only" role="status">
        {announcement}
      </p>
      <button
        className="assistant-toggle"
        aria-expanded={expanded}
        aria-controls="assistant-content"
        onClick={toggle}
      >
        <Sparkle size={23} />
        <span className="assistant-title">Local AI assistant</span>
        <span className="assistant-toggle-hint">
          Guidance for every step. You decide what changes.
        </span>
        <span className="assistant-local-label">Optional · free</span>
        <CaretDown size={19} className="assistant-chevron" />
      </button>
      <div id="assistant-content" hidden={!expanded}>
        <div className="assistant-content">
          <div className="assistant-connection">
            <div className="assistant-status" role="status">
              {checking ? (
                <SpinnerGap size={18} className="spinner" />
              ) : ready ? (
                <CheckCircle size={18} />
              ) : (
                <Cpu size={19} />
              )}
              <span>
                {checking
                  ? 'Checking Ollama…'
                  : ready
                    ? 'Ollama connected'
                    : status?.running
                      ? 'Ollama connected · download a local model'
                      : 'Connect Ollama to get started'}
              </span>
            </div>
            <button
              className="text-button"
              onClick={() => void refresh()}
              disabled={checking || pending}
            >
              <ArrowClockwise size={17} />
              Refresh connection
            </button>
          </div>

          {!checking && !ready && (
            <div className="assistant-setup">
              <p>{status?.detail || 'Run Ollama on the same machine as this CAD service.'}</p>
              <p>
                Install the free{' '}
                <a href="https://ollama.com/download" target="_blank" rel="noreferrer">
                  Ollama app
                </a>
                , start it, then download a local model in your terminal. Refresh the connection
                when it is ready.
              </p>
              <code>ollama pull qwen3:1.7b</code>
              <p>Downloads can be several GB. All CAD tools work without AI.</p>
            </div>
          )}

          {ready && (
            <div className="assistant-model-row">
              <label htmlFor="assistant-model">Local model</label>
              <select
                id="assistant-model"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                disabled={pending}
              >
                {status.models.map((item) => (
                  <option key={item.name} value={item.name}>
                    {item.name}
                    {item.name === status.recommended_model ? ' · suggested' : ''}
                  </option>
                ))}
              </select>
              {selected && <span>{(selected.size_bytes / 1e9).toFixed(1)} GB on disk</span>}
            </div>
          )}

          <p className="assistant-privacy">
            <Info size={17} />
            <span>
              Your question and current settings go to Ollama on this CAD service’s machine. No
              photo is shared with AI. No paid API or cloud model is used.
            </span>
          </p>
          <details className="assistant-context">
            <summary>See the project details AI receives</summary>
            <p>
              Width: {context.width_mm === null ? 'not set' : `${context.width_mm} mm`} · Thickness:{' '}
              {context.thickness_mm === null ? 'not set' : `${context.thickness_mm} mm`} · Through
              holes: {context.hole_count ?? 'not traced'} · Threshold:{' '}
              {thresholdLabel(context.threshold)} · {polarityLabel(context.inverted)} · Detail:{' '}
              {detailLabel[context.detail]}.
            </p>
            <p>
              Design: {context.design.scale_percent}% XY scale, {context.design.thickness_percent}%
              thickness scale, {context.design.material.toUpperCase()}, {context.design.color},{' '}
              {context.design.detail_mode} detail, {context.design.nozzle_mm} mm nozzle,{' '}
              {context.design.output_mode === 'single'
                ? 'single part'
                : `${context.design.split_columns} × ${context.design.split_rows} split grid`}
              .
            </p>
            <p>
              Printer: {context.design.printer_id}. Build volume: {context.design.bed_width_mm} ×{' '}
              {context.design.bed_depth_mm} × {context.design.bed_height_mm} mm;{' '}
              {context.design.bed_margin_mm} mm margin.{' '}
              {context.geometry
                ? 'Current built dimensions and individual part sizes are included.'
                : 'There is no current built geometry to check.'}
            </p>
            <p>
              Also includes whether a photo and current model are available, plus trace and build
              notes. Your photo, outline coordinates and project name are excluded. Each question
              starts a fresh conversation.
            </p>
          </details>

          <div className="assistant-question-area">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void ask();
              }}
            >
              <label htmlFor="assistant-question">What would you like help with?</label>
              <div className="assistant-starters">
                {starters.map(([label, prompt]) => (
                  <button
                    type="button"
                    key={label}
                    disabled={pending}
                    onClick={() => {
                      setQuestion(prompt);
                      questionInput.current?.focus();
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <textarea
                id="assistant-question"
                ref={questionInput}
                rows={3}
                maxLength={1600}
                value={question}
                disabled={pending}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="For example: the outline misses a small hole. What should I try?"
                aria-describedby="assistant-question-help"
              />
              <div className="assistant-send-row">
                <p id="assistant-question-help">AI suggests. You review, apply and build.</p>
                <button
                  className="primary-button"
                  type="submit"
                  disabled={!ready || !question.trim() || pending || busy}
                >
                  {pending ? <SpinnerGap size={19} className="spinner" /> : <ArrowUp size={18} />}
                  {pending ? 'Thinking locally…' : 'Ask local AI'}
                </button>
              </div>
            </form>
            {pending && (
              <div className="assistant-wait">
                <p role="status">
                  The first answer may take a little longer while the model loads. You can keep
                  using the workbench.
                </p>
                <button className="text-button" onClick={stopWaiting}>
                  Stop waiting
                </button>
              </div>
            )}
            {error && (
              <p className="assistant-error" role="alert">
                {error}
              </p>
            )}
          </div>

          {reply && (
            <div className="assistant-reply" ref={replyRef} tabIndex={-1} aria-label="AI response">
              <div className="assistant-reply-heading">
                <strong>
                  <Sparkle size={18} /> Suggested next step
                </strong>
                <span>
                  {reply.model} · {reply.elapsed_seconds.toFixed(1)}s
                </span>
              </div>
              <p className="assistant-asked">{askedQuestion}</p>
              <p className="assistant-answer">{reply.answer}</p>
              {changes.length > 0 && (
                <div className="assistant-proposal">
                  <h3>Review proposed changes</h3>
                  <table>
                    <thead>
                      <tr>
                        <th>Setting</th>
                        <th>Before</th>
                        <th>Suggested</th>
                      </tr>
                    </thead>
                    <tbody>
                      {changes.map((change) => (
                        <tr key={change.label}>
                          <th scope="row">{change.label}</th>
                          <td>{change.before}</td>
                          <td>{change.after}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p>
                    Your physical reference and thickness stay the same. Retracing with a feature
                    reference recalculates outside width. Apply the changes you want, then build to
                    review the resulting geometry and printer fit.
                  </p>
                  <div className="assistant-proposal-actions">
                    <button
                      className="outlined-button"
                      disabled={
                        busy ||
                        applying ||
                        applied ||
                        outdated ||
                        (changesTrace && !context.has_image)
                      }
                      onClick={async () => {
                        if (!proposal) return;
                        setApplying(true);
                        try {
                          if (await onApply(proposal)) setApplied(true);
                        } finally {
                          setApplying(false);
                        }
                      }}
                    >
                      {applying ? (
                        <SpinnerGap size={17} className="spinner" />
                      ) : (
                        <CheckCircle size={17} />
                      )}
                      {applied ? 'Suggestion applied' : 'Apply suggestion'}
                    </button>
                    {!applied && (
                      <button
                        className="text-button"
                        disabled={applying}
                        onClick={() => setReply({ ...reply, proposal: null })}
                      >
                        Keep current settings
                      </button>
                    )}
                    {canUndo && (
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() => {
                          onUndo();
                          setApplied(false);
                        }}
                      >
                        <ArrowCounterClockwise size={17} />
                        Undo suggestion
                      </button>
                    )}
                  </div>
                  {!applied && outdated && (
                    <p className="assistant-stale">
                      Your project changed after this answer. Ask again for a fresh suggestion.
                    </p>
                  )}
                  {changesTrace && !context.has_image && (
                    <p className="assistant-stale">Load a source photo to apply trace changes.</p>
                  )}
                </div>
              )}
              {reply.warnings.length > 0 && (
                <ul className="assistant-cautions">
                  {reply.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {canUndo && changes.length === 0 && (
            <button className="text-button" disabled={busy} onClick={onUndo}>
              <ArrowCounterClockwise size={17} />
              Undo suggestion
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
