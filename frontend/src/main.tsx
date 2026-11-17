import { useEffect, useState } from 'react';
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
function route(): Studio {
  const target = window.location.hash.slice(1).split('?')[0];
  return Object.hasOwn(studios, target) ? (target as Studio) : 'workbench';
}

// Mount a studio when first visited, then preserve its unsaved work during navigation.
// Hidden routes are inert and active context suspends focus, modal and automatic work.
function Root() {
  const [active, setActive] = useState(route);
  const [visited, setVisited] = useState<Studio[]>(() => [route()]);
  useEffect(() => {
    const changed = () => {
      const next = route();
      setVisited((previous) => (previous.includes(next) ? previous : [...previous, next]));
      setActive(next);
    };
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);
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
