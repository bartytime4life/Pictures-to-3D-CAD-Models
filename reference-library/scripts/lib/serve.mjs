// How the browser checks open index.html: from file:// (the default, exactly as a reader
// opens it) or from a private loopback HTTP server when CAD_REFERENCE_BROWSER_TRANSPORT=http,
// for browsers whose policy blocks local-file navigation. Shared by check-library.mjs and
// check-photos.mjs so both test the same page over the same transport.
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { ROOT } from './runtime.mjs';

export const TRANSPORTS = Object.freeze(['file', 'http']);

// Serve only published reader content. Never expose scripts, dependencies,
// environment files, or the parent repository; realpath also excludes symlinks
// escaping the library. The two Python examples are downloadable source text.
const publishedFiles = new Set([
  'index.html', 'HANDBOOK.md', 'REFERENCES.md', 'sources.csv', 'cadkit/README.md',
  'examples/build_plate.py', 'examples/calculate.py', 'examples/calculation-results.json',
  'examples/clearance-coupon.scad', 'examples/plate-parameters.csv',
  'examples/two-hole-plate.scad', 'examples/two-hole-plate.svg',
  'output/pdf/pictures-to-printable-cad.pdf',
]);
const mimeTypes = {
  '.html': 'text/html; charset=utf-8', '.svg': 'image/svg+xml',
  '.pdf': 'application/pdf', '.json': 'application/json', '.csv': 'text/csv; charset=utf-8',
};

export function servePublishedFile(request, response) {
  if (!['GET', 'HEAD'].includes(request.method)) {
    response.writeHead(405, { Allow: 'GET, HEAD' }).end();
    return;
  }
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const relative = pathname === '/' ? 'index.html' : pathname.slice(1);
    const allowed = publishedFiles.has(relative)
      || /^assets\/figures\/[a-z0-9-]+\.svg$/.test(relative)
      || /^templates\/[a-zA-Z0-9-]+\.(md|csv)$/.test(relative);
    if (!allowed) { response.writeHead(404).end(); return; }
    const realFile = fs.realpathSync(path.join(ROOT, relative));
    if (!realFile.startsWith(fs.realpathSync(ROOT) + path.sep) || !fs.statSync(realFile).isFile()) {
      response.writeHead(404).end(); return;
    }
    const body = fs.readFileSync(realFile);
    response.writeHead(200, {
      'Content-Type': mimeTypes[path.extname(realFile)] || 'text/plain; charset=utf-8',
      'Content-Length': body.length, 'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
    });
    response.end(request.method === 'HEAD' ? undefined : body);
  } catch {
    response.writeHead(404).end();
  }
}

/** The transport named by CAD_REFERENCE_BROWSER_TRANSPORT; throws on anything else. */
export function browserTransport(env = process.env) {
  const transport = env.CAD_REFERENCE_BROWSER_TRANSPORT || 'file';
  if (!TRANSPORTS.includes(transport)) throw new Error('CAD_REFERENCE_BROWSER_TRANSPORT must be file or http.');
  return transport;
}

/**
 * Resolve the page URL for `transport`. For http, start a server on a free loopback
 * port. Always call `close()` (it is a no-op for file://), including after a failure.
 */
export async function openTransport(transport) {
  if (transport === 'file') {
    return { pageUrl: pathToFileURL(path.join(ROOT, 'index.html')).href, close: async () => {} };
  }
  const server = http.createServer(servePublishedFile);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  return {
    pageUrl: `http://127.0.0.1:${server.address().port}/index.html`,
    close: async () => {
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    },
  };
}
