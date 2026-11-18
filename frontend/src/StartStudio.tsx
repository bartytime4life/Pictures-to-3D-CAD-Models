import { useEffect, useRef, useState } from 'react';
import {
  ArrowClockwise,
  ArrowRight,
  BookOpen,
  CheckCircle,
  Flask,
  FolderOpen,
  Images,
  Mountains,
  Ruler,
  Scan,
  Shapes,
  Sparkle,
  UploadSimple,
} from '@phosphor-icons/react';
import AppHeader from './AppHeader';
import { useStudioActive } from './StudioActivity';
import { parseRuntimeStatus } from './runtimeStatus';
import type { RuntimeStatus } from './runtimeStatus';
import './StartStudio.css';

const makingTasks = [
  {
    href: '#designer',
    Icon: Shapes,
    title: 'Design a flat part',
    description: 'Combine common shapes, cut holes and watch the CAD preview update.',
    need: 'Start with dimensions. No photograph needed.',
    action: 'Open shape designer',
  },
  {
    href: '#workbench?open=photo',
    Icon: Ruler,
    title: 'Trace a photo into CAD',
    description: 'Turn a clear outline into a measured, constant-thickness solid.',
    need: 'Bring a front-on photo, a measured size and thickness.',
    action: 'Choose a photo',
  },
  {
    href: '#relief',
    Icon: Mountains,
    title: 'Make a relief or lithophane',
    description: 'Give a picture raised depth or make a panel that reveals it in light.',
    need: 'Start with an image or heightmap. Samples are included.',
    action: 'Open relief studio',
  },
];

const supportingTools = [
  {
    href: '#image',
    Icon: Scan,
    title: 'Inspect an image',
    detail: 'Check exposure, contrast and regions, or compare two images.',
    requirement: 'No AI needed',
  },
  {
    href: '#library',
    Icon: Images,
    title: 'Organize source photos',
    detail: 'Browse, measure and choose photographs for a project.',
    requirement: 'Optional vision model for similarity',
  },
  {
    href: '#creative',
    Icon: Sparkle,
    title: 'Explore an idea with AI',
    detail: 'Develop directions, critique a concept or plan the making.',
    requirement: 'Requires a local Ollama chat model',
  },
  {
    href: '#knowledge',
    Icon: BookOpen,
    title: 'Find a guide',
    detail: 'Learn a workflow, resolve a problem and keep reading notes.',
    requirement: 'No AI needed',
  },
  {
    href: '#science',
    Icon: Flask,
    title: 'Explore measurements',
    detail: 'Try scale, print-layer and clearance scenarios.',
    requirement: 'No AI needed',
  },
];

export default function StartStudio() {
  const active = useStudioActive();
  const activeRef = useRef(active);
  activeRef.current = active;
  const request = useRef<AbortController | null>(null);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState('');

  async function refreshRuntime() {
    if (!activeRef.current) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 12000);
    setChecking(true);
    setError('');
    try {
      const response = await fetch('/api/runtime', { signal: controller.signal });
      if (!response.ok) throw new Error('Could not read the local setup requirements.');
      const result = parseRuntimeStatus(await response.json());
      if (request.current !== controller || !activeRef.current) return;
      setRuntime(result);
    } catch {
      if (request.current !== controller || !activeRef.current) return;
      setRuntime(null);
      setError('Could not check setup. Make sure the local CAD service is running, then refresh.');
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setChecking(false);
      }
    }
  }

  useEffect(() => {
    if (active) void refreshRuntime();
    return () => {
      request.current?.abort();
      request.current = null;
    };
  }, [active]);

  return (
    <div className="app-shell start-shell">
      <AppHeader studio="start" projectName="Choose your next step" />
      <main className="start-main" id="start" tabIndex={-1}>
        <div className="start-intro">
          <p className="start-eyebrow">YOUR LOCAL MAKING STUDIO</p>
          <h1>What would you like to make?</h1>
          <p>
            Start from common shapes, a measured photograph or a picture with depth. The core making
            tools work without AI.
          </p>
        </div>

        <section className="start-making" aria-label="Start a making task">
          {makingTasks.map(({ href, Icon, title, description, need, action }) => (
            <a className="start-task" href={href} key={href}>
              <span className="start-task-icon" aria-hidden="true">
                <Icon size={28} weight="light" />
              </span>
              <h2>{title}</h2>
              <p>{description}</p>
              <span className="start-task-need">{need}</span>
              <span className="start-task-action">
                {action} <ArrowRight size={18} aria-hidden="true" />
              </span>
            </a>
          ))}
        </section>

        <section className="start-continue" aria-labelledby="start-continue-title">
          <div>
            <h2 id="start-continue-title">Continue your work</h2>
            <p>Reopen a saved flat-part snapshot or a downloaded project file.</p>
          </div>
          <div className="start-continue-actions">
            <a className="outlined-button" href="#workbench?open=projects">
              <FolderOpen size={19} aria-hidden="true" /> Saved flat-part projects
            </a>
            <a className="start-text-link" href="#workbench?open=photo">
              <UploadSimple size={18} aria-hidden="true" /> Open a downloaded project
            </a>
          </div>
          <p className="start-save-note">
            Switching workspaces keeps current drafts in this page. Save or download your work
            before reloading or closing it. Browser snapshots stay in this browser.
          </p>
        </section>

        <section className="start-tools" aria-labelledby="start-tools-title">
          <div className="start-section-heading">
            <div>
              <p className="start-eyebrow">MORE WAYS TO WORK</p>
              <h2 id="start-tools-title">Inspect, organize and explore</h2>
            </div>
            <span>Find any workspace with Search commands or Ctrl/Cmd+K.</span>
          </div>
          <div className="start-tool-grid">
            {supportingTools.map(({ href, Icon, title, detail, requirement }) => (
              <a className="start-tool" href={href} key={href}>
                <Icon size={23} aria-hidden="true" />
                <h3>{title}</h3>
                <p>{detail}</p>
                <span>{requirement}</span>
              </a>
            ))}
          </div>
        </section>

        <div className="start-help-grid">
          <section className="start-help" aria-labelledby="start-sample-title">
            <p className="start-eyebrow">FIRST TIME HERE?</p>
            <h2 id="start-sample-title">Learn with a sample</h2>
            <p>
              Inspect the included mounting plate, change its dimensions and follow it through to an
              export. Sample measurements are for demonstration.
            </p>
            <a className="start-text-link" href="#workbench?open=sample">
              Try the flat-part sample <ArrowRight size={18} aria-hidden="true" />
            </a>
          </section>
          <section className="start-help start-runtime" aria-labelledby="start-runtime-title">
            <div className="start-runtime-heading">
              <h2 id="start-runtime-title">Local setup</h2>
              <button
                type="button"
                className="start-refresh"
                aria-label="Refresh setup"
                onClick={() => void refreshRuntime()}
                disabled={checking}
              >
                <ArrowClockwise size={17} aria-hidden="true" /> Refresh
              </button>
            </div>
            <p className="start-runtime-summary" role={error ? 'alert' : 'status'}>
              {checking ? (
                'Checking local requirements…'
              ) : error ? (
                error
              ) : runtime ? (
                <>
                  {runtime.ready && <CheckCircle size={18} aria-hidden="true" />}
                  {runtime.ready
                    ? 'Core requirements found'
                    : 'Review the setup requirements below'}
                </>
              ) : (
                'Setup has not been checked.'
              )}
            </p>
            <p>
              A setup check finds installed requirements. Try a sample to check a complete CAD
              workflow. Optional AI tools have their own model requirements.
            </p>
            {runtime && (
              <details className="start-setup-details">
                <summary>Setup details</summary>
                <ul>
                  {runtime.checks.map((check) => (
                    <li key={check.id}>
                      <div className="start-check-heading">
                        <strong>{check.label}</strong>
                        <span className={`start-check-status start-check-${check.status}`}>
                          {check.status === 'ready'
                            ? 'Found'
                            : check.status === 'limited'
                              ? 'Limited'
                              : check.required
                                ? 'Needed'
                                : 'Optional'}
                        </span>
                      </div>
                      <p>{check.detail}</p>
                      {check.action && (
                        <div className="start-setup-action">
                          <span>{check.action.label}</span>
                          <code>{check.action.command}</code>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
