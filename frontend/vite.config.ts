import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { frontendBuildInfo } from '../scripts/frontendBuildInfo.ts';

// Capture once so the embedded UI value and emitted manifest describe the same inputs.
const buildInfo = JSON.stringify(frontendBuildInfo(fileURLToPath(new URL('..', import.meta.url))));

export default defineConfig({
  define: { __PICAD_BUILD_INFO__: buildInfo },
  plugins: [
    react(),
    {
      name: 'picad-build-info',
      apply: 'build',
      generateBundle() {
        this.emitFile({ type: 'asset', fileName: 'build-info.json', source: `${buildInfo}\n` });
      },
    },
  ],
  server: {
    // Loopback by default, like scripts/dev.sh: the /api proxy below would otherwise expose the
    // backend to the local network. dev.sh's PICAD_DEV_HOST (or --host) opts in explicitly.
    host: '127.0.0.1',
    port: 4173,
    strictPort: true,
    allowedHosts: ['terminal.local', 'localhost'],
    proxy: {
      // Keep the browser's Host and Origin aligned for the loopback slicer-launch gate.
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
      '/reference-library': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
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
