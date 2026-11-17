import { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource-variable/inter';
import '@fontsource-variable/jetbrains-mono';
import './styles.css';
import App from './App';
import LibraryStudio from './LibraryStudio';
import ReliefStudio from './ReliefStudio';

// Three independent tools share one page: the flat-part workbench (default), the relief &
// lithophane studio at #relief and the photo library at #library. Each keeps its own state.
function Root() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const changed = () => setHash(window.location.hash);
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);
  if (hash === '#library') return <LibraryStudio />;
  return hash === '#relief' ? <ReliefStudio /> : <App />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(<Root />);
