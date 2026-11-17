import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource-variable/inter';
import '@fontsource-variable/jetbrains-mono';
import './styles.css';
import App from './App';
import LibraryStudio from './LibraryStudio';
import ReliefStudio from './ReliefStudio';
import KnowledgeStudio from './KnowledgeStudio';
import ScienceStudio from './ScienceStudio';
import { StudioActivity } from './StudioActivity';
import type { Studio } from './AppHeader';

const studios = {
  workbench: App,
  relief: ReliefStudio,
  library: LibraryStudio,
  knowledge: KnowledgeStudio,
  science: ScienceStudio,
};
const TITLES: Record<Studio, string> = {
  workbench: 'Pictures to CAD — Photo to profile workbench',
  relief: 'Pictures to CAD — Relief & lithophane studio',
  library: 'Pictures to CAD — Photo library',
  knowledge: 'Pictures to CAD — Knowledge base',
  science: 'Pictures to CAD — Science lab',
};
function route(): Studio {
  const target = window.location.hash.slice(1).split('?')[0];
  return Object.hasOwn(studios, target) ? (target as Studio) : 'workbench';
}

// Mount a studio when first visited, then preserve its unsaved work during navigation.
// Hidden routes are inert and active context suspends focus, modal and automatic work.
function Root() {
  const [active, setActive] = useState(route);
  const [visited, setVisited] = useState<Studio[]>(() => [route()]);
  const shown = useRef(active);
  const scrollOf = useRef<Partial<Record<Studio, number>>>({});
  useEffect(() => {
    const changed = () => {
      const next = route();
      // Remember where the studio being left was scrolled, before the next one shows.
      if (next !== shown.current) scrollOf.current[shown.current] = window.scrollY;
      setVisited((previous) => (previous.includes(next) ? previous : [...previous, next]));
      setActive(next);
    };
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);
  useLayoutEffect(() => {
    document.title = TITLES[active];
    // A studio opens at its top the first time and where it was left after that, not at the
    // previous studio's scroll position. The first render keeps the browser's own restoration.
    if (shown.current !== active) window.scrollTo(0, scrollOf.current[active] ?? 0);
    shown.current = active;
  }, [active]);
  return visited.map((studio) => {
    const Component = studios[studio];
    return (
      <div
        key={studio}
        className="studio-route"
        data-studio={studio}
        hidden={studio !== active}
        inert={studio !== active}
      >
        <StudioActivity.Provider value={studio === active}>
          <Component />
        </StudioActivity.Provider>
      </div>
    );
  });
}

ReactDOM.createRoot(document.getElementById('root')!).render(<Root />);
