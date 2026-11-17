import type { ReactNode } from 'react';
import {
  ArrowSquareOut,
  BookOpen,
  Cube,
  Flask,
  Images,
  Mountains,
  Ruler,
} from '@phosphor-icons/react';
import CommandLauncher, { type StudioCommand } from './CommandLauncher';

export type Studio = 'workbench' | 'relief' | 'library' | 'knowledge' | 'science';

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
          <a
            className="studio-tab"
            href="#workbench"
            aria-label="Flat-part workbench"
            aria-current={studio === 'workbench' ? 'page' : undefined}
          >
            <Ruler size={23} />
            <span className="label-long">Flat part</span>
            <span className="label-short">Flat part</span>
          </a>
          <a
            className="studio-tab"
            href="#relief"
            aria-label="Relief and lithophane studio"
            aria-current={studio === 'relief' ? 'page' : undefined}
          >
            <Mountains size={23} />
            <span className="label-long">Relief &amp; Lithophane</span>
            <span className="label-short">Relief</span>
          </a>
          <a
            className="studio-tab"
            href="#library"
            aria-label="Photo library"
            aria-current={studio === 'library' ? 'page' : undefined}
          >
            <Images size={23} />
            <span className="label-long">Photo library</span>
            <span className="label-short">Library</span>
          </a>
          <a
            className="studio-tab"
            href="#knowledge"
            aria-current={studio === 'knowledge' ? 'page' : undefined}
          >
            <BookOpen size={21} />
            <span>Knowledge</span>
          </a>
          <a
            className="studio-tab"
            href="#science"
            aria-current={studio === 'science' ? 'page' : undefined}
          >
            <Flask size={21} />
            <span>Science lab</span>
          </a>
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
