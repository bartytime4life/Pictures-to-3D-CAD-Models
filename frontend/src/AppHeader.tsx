import type { ReactNode } from 'react';
import {
  ArrowSquareOut,
  BookOpen,
  Cube,
  Flask,
  Images,
  Mountains,
  Ruler,
  Sparkle,
  Shapes,
} from '@phosphor-icons/react';
import CommandLauncher, { type StudioCommand } from './CommandLauncher';

import { STUDIO_CATALOG } from './studioCatalog';
import type { Studio } from './studioCatalog';
export type { Studio } from './studioCatalog';

const studioIcons = {
  designer: Shapes,
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
 * On narrow screens every icon keeps a short visible label instead of becoming a bare icon.
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
        <a className="brand" href="#workbench">
          <span className="brand-symbol">
            <Cube size={29} weight="light" />
          </span>
          <span className="brand-wordmark">
            <strong>Pictures to CAD</strong> <small>PRECISION STUDIO</small>
          </span>
        </a>
        <div className="project-context">
          <span className="project-caption">
            {studio === 'knowledge' || studio === 'science' ? 'EXPLORE' : 'CURRENT PROJECT'}
          </span>
          <div className="project-name">{projectName}</div>
        </div>
        <div className="topbar-tools">
          <CommandLauncher studio={studio} commands={commands} />
          {actions && <div className="header-actions">{actions}</div>}
        </div>
      </div>
      <div className="topbar-navigation">
        <nav className="studio-tabs" aria-label="Studios">
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
        </nav>
        <span className="workspace-local">
          <span aria-hidden="true" />
          Local workspace
        </span>
      </div>
    </header>
  );
}
