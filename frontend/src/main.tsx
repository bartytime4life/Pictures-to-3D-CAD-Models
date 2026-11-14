import { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource-variable/inter';
import '@fontsource-variable/jetbrains-mono';
import './styles.css';
import App from './App';
import ReliefStudio from './ReliefStudio';

// Two independent tools share one page: the flat-part workbench (default) and the
// relief & lithophane studio at #relief. Each keeps its own state.
function Root() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const changed = () => setHash(window.location.hash);
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);
  return hash === '#relief' ? <ReliefStudio /> : <App />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(<Root />);
