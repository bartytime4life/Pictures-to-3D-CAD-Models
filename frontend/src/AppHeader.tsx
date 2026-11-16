import type { ReactNode } from 'react';
import { Cube, Images, Mountains, Ruler } from '@phosphor-icons/react';

export type Studio = 'workbench' | 'relief' | 'library';

/**
 * The header the studios share: the brand, the page's own project-name control, one row of
 * studio tabs (the current one marked with aria-current="page") and the page's own actions.
 * On narrow screens every icon keeps a short visible label instead of becoming a bare icon.
 */
export default function AppHeader({
  studio,
  projectName,
  actions,
}: {
  studio: Studio;
  projectName: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="topbar">
      <a
        className="brand"
        href="#workbench"
        aria-label={
          studio === 'workbench'
            ? 'Pictures to CAD workbench'
            : 'Pictures to CAD flat-part workbench'
        }
      >
        <Cube size={35} weight="light" />
        <span>Pictures to CAD</span>
      </a>
      <div className="project-name">{projectName}</div>
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
          href="/reference-library/index.html#cad"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="OpenSCAD workspace (opens in a new tab)"
        >
          <Cube size={23} />
          <span className="label-long">OpenSCAD</span>
          <span className="label-short">OpenSCAD</span>
        </a>
      </nav>
      {actions && <div className="header-actions">{actions}</div>}
    </header>
  );
}
