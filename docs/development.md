# Development and setup

Run commands from the repository root unless a command explicitly says otherwise. An existing Codex cloud task already has an isolated checkout; use it directly rather than creating another worktree for normal setup.

## Prerequisites

- **Python 3.12** with `venv` and a working package installer, as recorded in `.python-version`. The project intentionally restricts Python to the tested CAD binary dependency combination; do not assume Python 3.13 compatibility.
- Node.js 22.12 or later; Node.js 24 is recommended.
- npm. Setup reuses [uv](https://docs.astral.sh/uv/) if installed or bootstraps its pinned version into `.local/uv-bootstrap`.
- Enough disk space for the Python CAD kernel and frontend dependencies. CadQuery and its OpenCascade runtime are substantially larger than an ordinary web API dependency.
- HTTPS access to the package registries needed by the lockfiles. Preserve the environment's proxy and certificate trust configuration.

The initial pipeline runs on the CPU. It requires neither CUDA nor an external image-generation, photogrammetry, or language-model service.

## Install and run

```bash
./scripts/setup.sh
./scripts/start.sh
```

The setup script installs dependencies from `uv.lock` and `package-lock.json`, then builds the frontend. The start script runs the Python service, which serves the compiled frontend and the API on the same origin.

The normal server uses port 8000. Do not assume a background process will survive a new cloud task or an environment snapshot restore; run the start script again in the restored environment.

The default bind address is `127.0.0.1`. The supported startup settings are:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PICAD_HOST` | `127.0.0.1` | API and built-interface bind address for `start.sh` |
| `PICAD_PORT` | `8000` | API and built-interface port for `start.sh` |
| `PICAD_DEV_HOST` | `127.0.0.1` | Vite bind address for `dev.sh`; the development API remains on port 8000 |
| `PICTURES_CAD_JOB_DIR` | Repository `.local/jobs` | Temporary model artifact directory |

Changing the bind address can expose a service to other machines. Use the intended host access controls; the application itself has no account authentication.

For frontend development:

```bash
./scripts/dev.sh
```

Development uses a Vite frontend on port 4173 and a Python backend on port 8000. Vite proxies `/api` requests to the backend. Start both services; opening Vite alone does not validate conversion or export.

## Project layout

```text
backend/             API, image tracing, validation, CAD conversion and exports
frontend/src/        React workbench and interactive Three.js model viewer
frontend/public/     demonstration image and static assets
scripts/             repeatable setup and startup entry points
tests/               backend and browser validation
docs/                user guides, architecture, limitations and evidence
```

Generated frontend build files, local environments, temporary conversion artifacts, and dependency caches are local outputs rather than source files.

## Validate changes

```bash
./scripts/test.sh
```

Or run the stages separately:

```bash
.venv/bin/python -m pytest -q
npm run build
npm run test:e2e
```

Backend checks should exercise image parsing, geometry validation, dimensional bounds, topology, and exported-file re-imports. Browser checks should exercise the actual conversion path, edits, outdated-result handling, exports, input failures, and responsive navigation.

Treat the recorded results in [validation.md](validation.md) as the test evidence for the current implementation. Do not infer that a test passed merely because its command is listed here.

Browser tests use `PLAYWRIGHT_CHROMIUM_EXECUTABLE` when supplied, otherwise `/usr/bin/chromium` when available, otherwise Playwright's installed Chromium. If neither a system browser nor a Playwright browser is present, install the browser after `npm ci`:

```bash
npx playwright install chromium
```

The test configuration starts the built app on port 8000, or reuses an already running server outside CI. `PICAD_TEST_URL` selects an explicitly managed test server instead. Confirm that a reused server is this checkout's app, particularly after rebuilding. Browser results and failure traces are local generated outputs under `playwright-report/` and `test-results/`.

The browser suite includes automated accessibility checks with `@axe-core/playwright`. Those checks cover the tested rendered states; they do not establish full accessibility conformance or replace keyboard and assistive-technology testing.

## Continuous integration

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) defines the same setup and test sequence on pushes and pull requests, using Python 3.12 and Node.js 24. It installs Chromium, runs Python lint checks, executes `scripts/test.sh`, and retains browser reports and failure traces for seven days.

The workflow has been added to the repository. A remote GitHub Actions run is unverified until a run actually completes; local test results and a workflow definition are separate evidence.

## Dependency changes

Change dependency declarations intentionally and regenerate the corresponding lockfile. Keep lockfiles under version control. Use frozen or clean-install modes for normal setup so a routine startup does not silently select a new CAD kernel or frontend dependency.

After upgrading the geometry stack, rerun dimensional and export re-import tests. After changing the viewer, verify the displayed geometry against the same exported solid, including interior holes and camera reset behavior.

## Cloud environment notes

- A localhost address is local to the machine running the service. Use the host's supported access path from another machine.
- Keep the existing injected Git authentication, HTTP proxy, and certificate trust settings. A missing `GH_TOKEN` is not evidence that GitHub access is unavailable.
- No application secret is required for the included conversion workflow. Do not add API credentials merely to run it.
- A cloud backend receives uploaded photos. See [data handling](privacy-security.md) before describing this deployment as local or private.
- Installation prepares files; startup creates processes. A saved environment snapshot does not preserve live servers.

## Check a running instance

After startup, this smoke check exercises the real sample through the HTTP API, builds a solid, verifies its width and thickness, downloads STEP, and deletes its own temporary model:

```bash
.venv/bin/python scripts/smoke.py
```

To check the development proxy, use `PICAD_BASE_URL=http://127.0.0.1:4173 .venv/bin/python scripts/smoke.py`. The default is the single-service startup on port 8000. This complements the full test suite; it does not replace browser verification.
