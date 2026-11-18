import type { ReactNode } from 'react';
import {
  ArrowSquareOut,
  BookOpen,
  Cube,
  Flask,
  Images,
  House,
  Mountains,
  Ruler,
  Sparkle,
  Shapes,
  Scan,
} from '@phosphor-icons/react';
import CommandLauncher, { type StudioCommand } from './CommandLauncher';

import { STUDIO_CATALOG } from './studioCatalog';
import type { Studio } from './studioCatalog';
export type { Studio } from './studioCatalog';

const studioIcons = {
  start: House,
  designer: Shapes,
  image: Scan,
  workbench: Ruler,
  relief: Mountains,
  library: Images,
  creative: Sparkle,
  knowledge: BookOpen,
  science: Flask,
};

/**
 * The header the studios share: the brand, the page's own project-name control, one row of
 * studio tabs (the current one marked with aria-current="page") and the page's own actions.
 * On narrow screens a labeled workspace picker leaves more room for making.
 */
export default function AppHeader({
  studio,
  projectName,
  actions,
  commands,
}: {
  studio: Studio;
  projectName: ReactNode;
  actions?: ReactNode;
  commands?: StudioCommand[];
}) {
  return (
    <header className="topbar">
      <a
        className="skip-link"
        href={`#${studio}`}
        onClick={(event) => {
          event.preventDefault();
          const main = event.currentTarget.closest('.app-shell')?.querySelector('main');
          if (main) {
            main.tabIndex = -1;
            main.focus();
          }
        }}
      >
        Skip to workspace
      </a>
      <div className="topbar-main">
        <a className="brand" href="#start">
          <span className="brand-symbol">
            <Cube size={29} weight="light" />
          </span>
          <span className="brand-wordmark">
            <strong>Pictures to CAD</strong> <small>PRECISION STUDIO</small>
          </span>
        </a>
        <div className="project-context">
          <span className="project-caption">
            {['start', 'knowledge', 'science', 'image', 'library', 'creative'].includes(studio)
              ? 'WORKSPACE'
              : 'CURRENT PROJECT'}
          </span>
          <div className="project-name">{projectName}</div>
        </div>
        <div className="topbar-tools">
          <CommandLauncher studio={studio} commands={commands} />
          {actions && <div className="header-actions">{actions}</div>}
        </div>
      </div>
      <div className="topbar-navigation">
        <nav className="workspace-navigation" aria-label="Studios">
          <div className="studio-tabs">
            {STUDIO_CATALOG.map((item) => {
              const Icon = studioIcons[item.id];
              return (
                <a
                  key={item.id}
                  className="studio-tab"
                  href={`#${item.id}`}
                  aria-label={item.name}
                  aria-current={studio === item.id ? 'page' : undefined}
                >
                  <Icon size={21} />
                  <span className="label-long">{item.label}</span>
                  <span className="label-short">{item.shortLabel}</span>
                </a>
              );
            })}
            <a
              className="studio-tab"
              href="/reference-library/index.html#cad"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="OpenSCAD workspace (opens in a new tab)"
            >
              <ArrowSquareOut size={19} />
              <span className="label-long">OpenSCAD</span>
              <span className="label-short">OpenSCAD</span>
            </a>
          </div>
          <div className="mobile-workspace-navigation">
            <a
              className="mobile-start"
              href="#start"
              aria-current={studio === 'start' ? 'page' : undefined}
            >
              <House size={20} aria-hidden="true" />
              <span>Start</span>
            </a>
            <label className="workspace-picker">
              <span className="sr-only">Workspace</span>
              <select
                value={studio}
                onChange={(event) => {
                  window.location.hash = `#${event.target.value}`;
                }}
              >
                {STUDIO_CATALOG.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <a
              className="mobile-companion"
              href="/reference-library/index.html#cad"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="OpenSCAD workspace (opens in a new tab)"
            >
              <ArrowSquareOut size={18} aria-hidden="true" />
              <span>OpenSCAD</span>
            </a>
          </div>
        </nav>
        <span className="workspace-local">
          <span aria-hidden="true" />
          Local workspace
        </span>
      </div>
    </header>
  );
}
