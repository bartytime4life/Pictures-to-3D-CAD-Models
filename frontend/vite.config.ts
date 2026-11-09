import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // Loopback by default, like scripts/dev.sh: the /api proxy below would otherwise expose the
    // backend to the local network. dev.sh's PICAD_DEV_HOST (or --host) opts in explicitly.
    host: '127.0.0.1',
    port: 4173,
    strictPort: true,
    allowedHosts: ['terminal.local', 'localhost'],
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // The 3D preview is on the first screen, so three.js loads with the page rather than lazily.
    // Splitting it (≈1.0 MB, ≈270 kB gzip) and the other libraries from the app's own code lets
    // the browser keep them cached across app rebuilds. The limit sits just above that chunk so
    // unexpected growth still warns.
    chunkSizeWarningLimit: 1100,
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'three', test: /node_modules[\\/](three|three-stdlib|@react-three)[\\/]/ },
            { name: 'vendor', test: /node_modules/ },
          ],
        },
      },
    },
  },
});
