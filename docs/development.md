# Development and setup

Run commands from the repository root unless a command explicitly says otherwise. An existing Codex cloud task already has an isolated checkout; use it directly rather than creating another worktree for normal setup.

See the [documentation index](README.md) for usage and method guides, and
[Contributing](contributing.md) for change scope, review and evidence practices.

## Prerequisites

- **Python 3.12** with `venv` and a working package installer, as recorded in `.python-version`. The project intentionally restricts Python to the tested CAD binary dependency combination; do not assume Python 3.13 compatibility. `python3` does not have to be 3.12: setup uses `PICAD_PYTHON` when set, otherwise the first of `python3.12` and `python3` that is 3.12, and prints the interpreter it chose.
- Node.js 22.12 or later; Node.js 24 is recommended.
- npm. Setup reuses [uv](https://docs.astral.sh/uv/) if installed or bootstraps its pinned version into `.local/uv-bootstrap`.
- GNU Make for the root command entry point. The component scripts remain available when running a workbench-only workflow.
- Enough disk space for the Python CAD kernel and frontend dependencies. CadQuery and its OpenCascade runtime are substantially larger than an ordinary web API dependency.
- HTTPS access to the package registries needed by the lockfiles. Preserve the environment's proxy and certificate trust configuration.

The initial pipeline runs on the CPU. It requires neither CUDA nor an external image-generation, photogrammetry, or language-model service.

The companion library uses the `python3` and `node` found on `PATH` (it needs Python 3.10+ and Node.js 20+; `make setup` additionally requires the workbench's Python 3.12 and Node.js 22.12+), with its own `reference-library/.venv` and Node dependencies. Rebuilding its PDF also requires DejaVu fonts. Browser checks need Chrome/Chromium; OpenSCAD is needed to execute all library rendering checks. Setup installs neither these system tools nor model weights. Reading the committed library HTML/PDF needs none of the development tools.

## Install and run

```bash
make setup
make start
```

`make setup` prepares both components. Workbench setup uses `uv.lock` and the root `package-lock.json`, then builds the frontend. HEIC decoding comes from the `pi-heif` wheel (BSD-3-Clause), which bundles libheif and libde265 (LGPL-3.0) and needs no system package; it can read HEIC but not write it, so the HEIC files in `tests/fixtures/` were written with `pillow-heif`. Library setup creates `reference-library/.venv`, installs its PDF requirements, and runs `npm ci` against the library's own lockfile. The environments and dependency declarations remain separate.

`make start` runs the Python workbench service, which serves the compiled frontend, API, and published reference library on the same origin. The app header opens `/reference-library/index.html#cad` separately. The library route only serves an explicit set of reader files; personal native builds, temporary outputs, scripts, and environments remain outside it. `make setup-app` and the existing `./scripts/setup.sh` prepare only that workbench; `./scripts/start.sh` remains the direct startup command. A library-only contributor can use `make setup-library`.

The normal server uses port 8000. Do not assume a background process will survive a new cloud task or an environment snapshot restore; run the start script again in the restored environment.

The default bind address is `127.0.0.1`. Runtime and verification settings are:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PICAD_PYTHON` | first 3.12 of `python3.12`, `python3` | Python 3.12 interpreter that `setup.sh` builds `.venv` from |
| `PICAD_HOST` | `127.0.0.1` | API and built-interface bind address for `start.sh` |
| `PICAD_PORT` | `8000` | API and built-interface port for `start.sh` |
| `PICAD_DEV_HOST` | `127.0.0.1` | Vite bind address for `dev.sh`; the development API remains on port 8000 |
| `PICAD_BASE_URL` | `http://127.0.0.1:8000` | Existing server used by `make smoke`; not a startup setting |
| `PICAD_TEST_URL` | Playwright-managed local server | Explicit existing server for workbench browser tests; verify its source revision |
| `PICTURES_CAD_JOB_DIR` | Repository `.local/jobs` | Temporary model artifact directory |
| `PICTURES_CAD_OLLAMA_URL` | `http://127.0.0.1:11434` | Optional assistant's HTTP loopback endpoint on the backend host |
| `PICTURES_CAD_OLLAMA_MODEL` | `qwen3:1.7b` | Preferred installed assistant model; otherwise selects that default if installed, then the smallest local model |

Changing the bind address can expose a service to other machines. Use the intended host access controls; the application itself has no account authentication.

The optional assistant accepts only an HTTP loopback Ollama endpoint; remote URLs and cloud models are not supported. See [local AI setup](ollama.md) for the separate runtime/model installation and resource controls. Neither ordinary app setup nor CI downloads model weights. Existing CAD tests run without an Ollama installation; assistant integration tests use explicit test doubles and do not establish live model quality.

For frontend development:

```bash
make dev
```

`make dev` starts both the Vite frontend on port 4173 and Python backend on port
8000. Open http://127.0.0.1:4173 on that host. Vite proxies `/api` and
`/reference-library` requests to the backend. If starting components manually,
run both; opening Vite alone does not validate conversion or export.

## Project layout

```text
backend/             API, image tracing, validation, CAD conversion and exports
frontend/src/        React workbench and interactive Three.js model viewer
frontend/public/     demonstration image and static assets
scripts/             repeatable setup and startup entry points
studies/             declared experiments, source-bound results and independent checks
tests/               backend and browser validation
docs/                user guides, architecture, limitations and evidence
data/                pinned printer catalog and source attribution
reference-library/   offline handbook, calculators, examples, and independent build/test tools
```

Generated frontend build files, local environments, temporary conversion artifacts, and dependency caches are local outputs rather than source files.

The reference library intentionally commits generated HTML, figures, and its PDF alongside their sources. Rebuilding that component can update tracked outputs; review them with the source change rather than treating them as workbench build artifacts.

## Root commands

Run `make` for help. Component targets delegate to the existing scripts and library Makefile.

Use the [developer-tool catalog](developer-tools.md) for numerical CLI versions,
study/audit commands, output handling and optional plotting requirements. A
successful developer study is separate from a successful workbench build.

| Command | Scope |
| --- | --- |
| `make setup` | Prepare both components; no system tools, browser, or model downloads |
| `make start` / `make dev` | Run the production workbench / workbench with hot reload |
| `make build` | Build the workbench and library outputs, including the library PDF |
| `make test` | Workbench Python/build/browser checks, then library Python/Node/browser checks |
| `make lint` | Workbench Ruff and frontend/browser-source formatting checks |
| `make smoke` | Check an already running workbench through its real trace/build/export API |
| `make photo-benchmark PHOTOS=folder` | Trace a folder of your own reference-sheet photos and compare them with your caliper measurements ([guide](photo-benchmark.md)) |
| `make corner-sweep` | Fit synthetic blurred filleted corners and report radius error; it does not measure a real camera or part |
| `make material-gradient-study OUTPUT=new-folder` | Run the crossed local-profile study, retaining all measurements/rejections; [method and limits](material-gradients.md) |
| `make wall-gradient-study OUTPUT=new-folder` | Run bounded source fits, constructive wall/edge ambiguity and actual local wall-fit comparisons; [method and limits](wall-gradients.md) |
| `make wall-localization-study OUTPUT=new-folder` | Compare actual segmentation/subpixel/wall correction against the plan's pinned local Git baseline; [method and limits](wall-localization.md) |
| `make profile-noise-study OUTPUT=new.json` | Check supplied correlated noise, sample density, repetition and local information; [method](profile-observations.md) |
| `make postblur-operator-study OUTPUT=new.json` | Compare a declared finite filter plus final signed sampling with scalar approximations; [method](profile-observations.md) |
| `make warp-observation-study OUTPUT=new.json` | Compare known raw-image rectification, smoothing and final sampling, retaining stage rounding; [method](warp-observations.md) |
| `make raw-source-fit-study OUTPUT=new.json` | Fit a supplied raw Gaussian edge in fixed retained source modes, with bounded brightness and explicit numerical diagnostics; [method](raw-source-fit.md) |
| `make response-calibration-study OUTPUT=new.json` | Check exact common-response consistency and finite edge/calibration ambiguity; [method](response-calibration.md) |
| `make response-rectangles-study OUTPUT=new.json` | Compare both input quantifiers with outward Gaussian input covers and retain undetermined cases; [method](response-rectangles.md) |
| `.venv/bin/python scripts/response_calibration.py INPUT.json --output new.json` | Check exact calibration constraints without a server; [complete input example](response-calibration.md#run-an-exact-example) |
| `.venv/bin/python -m pytest -q tests/test_edge_crossings.py` | Check nearest-crossing decisions, exact ranking, unresolved contacts and rejected-point preservation; [method](edge-crossings.md) |
| `.venv/bin/python scripts/corner_feasibility.py --demo` | Run a bounded synthetic radius-set analysis; [input contract and limits](corner-feasibility.md) |
| `.venv/bin/python scripts/corner_feasibility.py pixel-input.json --output pixel-result.json` | Analyze supplied known uniform pixel means; [version-3 example](pixel-apertures.md) |
| `.venv/bin/python scripts/corner_feasibility.py signed-input.json --output signed-result.json` | Analyze a declared fixed signed operator; [version-4 example](signed-stencils.md) |
| `make freecad` | Check fitted synthetic STEP/DXF imports using a separately installed `FREECADCMD` |
| `make slicers` | Inspect executable discovery without starting a slicer |
| `make setup-app` / `make setup-library` | Prepare one component |
| `make build-app` / `make build-library` | Build one component |
| `make test-app` / `make test-library` | Validate one component |

The library's full build requires its PDF dependencies and fonts. The root library browser target uses an ephemeral loopback HTTP server; the standalone library check defaults to `file://`. `CAD_REFERENCE_BROWSER_TRANSPORT=file` or `http` selects that transport when invoking the library directly. This is a test mechanism; the distributed HTML still opens offline. See [library build instructions](../reference-library/BUILD.md) for its additional release, archive, and optional network-check targets.

## Validate changes

The hosted workbench job has a 45-minute overall budget for setup, Python,
build and the serial browser suite. The [runtime-budget record](validation/ci-runtime-budget.md)
explains the observed incomplete 30-minute run and the retained per-test limits.

```bash
make test
make lint
```

For just the workbench, use `make test-app` or the existing `./scripts/test.sh`. Its individual stages remain:

```bash
.venv/bin/python -m pytest -q
npm run build
npm run test:e2e
```

`make test-library` runs the independent library tests and browser checks without rerunning CAD workbench tests. Native OpenSCAD checks report skips if the tool is absent; those skips do not establish that rendering passed. Workbench source export does not require the executable. When it is available, `tests/test_mesh_interop.py` renders exported SCAD and compares simplified/scaled single and split-piece geometry, volume, and holes with the built CAD result. The library CI installs OpenSCAD and executes the required plate pipeline separately.

Backend checks should exercise image parsing, geometry validation, dimensional bounds, topology, and exported-file re-imports. Browser checks should exercise the actual conversion path, edits, outdated-result handling, exports, input failures, and responsive navigation.

For response-calibration changes, start with the two focused files and the
independent graph oracle. The [guide](response-calibration.md#repeat-the-edge-and-calibration-controls)
also supplies the finite study and its separate certificate auditor:

```bash
.venv/bin/python -m pytest -q tests/test_response_calibration.py tests/test_response_calibration_cli.py
.venv/bin/python studies/verification/response-calibration-oracle-v1.py --output .local/response-oracle-new.json
```

These checks require no CAD server. They establish the supplied mathematical
contract; they do not replace affected product tests or measured-camera evidence.

Design/print checks should also verify that XY and thickness percentages preserve measured inputs, that relative-detail approximation remains valid, and that generated split solids have consistent volumes and per-part exports. Check continuous-angle placement witnesses, conservative curve enclosures and unknown-fit cases rather than just 0°/90°. Cover version 2 polygon and version 3 fitted/reference recipe round-trips, version 1 import defaults, and browser-held measurement notes separately from server handoff recipes. Color/material preview must not alter mesh coordinates or imply material/strength simulation. Test assistant Apply/Undo, stale advice-only answers and invalid-setting recovery separately from live model quality.

For workflow changes, check guide, navigation and footer consistency through
missing input, invalid design, processing, stale and current states. Keep keyboard
focus after builds and recipe errors. Specialist export formats must remain
reachable through **Drawings & source files**. The [guided-workbench audit](validation/guided-workbench.md)
provides concrete regression examples.

Use the revision-bound records in [validation.md](validation.md) to identify which
implementation was checked. A historical pass does not establish a later head,
and listing a command here does not establish that it ran.
For a bounded API-only exercise, use the [synthetic example](api-examples.md#build-a-synthetic-rectangle).
For documentation changes, follow the [documentation maintenance procedure](contributing.md#documentation-maintenance).

Browser tests use `PLAYWRIGHT_CHROMIUM_EXECUTABLE` when supplied, otherwise `/usr/bin/chromium` when available, otherwise Playwright's installed Chromium, otherwise an installed Google Chrome (`/usr/bin/google-chrome`, `google-chrome-stable`, or the macOS application). If none of these is present, install the browser after `npm ci`:

```bash
npx playwright install chromium
```

For a library-only install, run `npx playwright install chromium` from `reference-library/`, or use the installed browser selected by `CAD_REFERENCE_CHROME`. The workbench uses `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. The two packages keep their own Playwright versions, so install each package's browser when not using a shared system Chrome/Chromium.

The test configuration starts the built app on port 8000, or reuses an already running server outside CI. `PICAD_TEST_URL` selects an explicitly managed test server instead. Confirm that a reused server is this checkout's app, particularly after rebuilding. Browser results and failure traces are local generated outputs under `playwright-report/` and `test-results/`.

Each checkout also needs its own root `.venv`: browser export inspectors invoke
`.venv/bin/python` relative to the checkout. Starting the API with another
worktree's interpreter does not prepare those helpers. Run `make setup-app` in
the test checkout; preserve earlier reports before a rerun replaces them.

The browser suite includes automated accessibility checks with `@axe-core/playwright`. Those checks cover the tested rendered states; they do not establish full accessibility conformance or replace keyboard and assistive-technology testing.

## Continuous integration

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) validates the workbench using Python 3.12 and Node.js 24. It installs Chromium, runs Ruff and Prettier checks (`make lint`), executes the workbench test sequence, and retains browser reports and failure traces for seven days. [The reference-library workflow](../.github/workflows/reference-library.yml) separately regenerates its committed outputs, runs its tests, renders its OpenSCAD plate, and checks its browser interface.

Use [project status](project-status.md#evidence-by-scope) for the latest recorded
exact-head workflow observations and [validation results](validation.md) for
separate local and remote evidence. The earlier [workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42528803054)
and [reference-library run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42528803055)
both passed at merge commit `5d6a446d6175e4ad1bd0c01c0166b05e0d1e393a`;
those historical passes do not validate a later revision.

## Dependency changes

Change dependency declarations intentionally and regenerate the corresponding lockfile. Keep lockfiles under version control. Use frozen or clean-install modes for normal setup so a routine startup does not silently select a new CAD kernel or frontend dependency.

After upgrading the geometry stack, rerun dimensional and export re-import tests. After changing the viewer, verify the displayed geometry against the same exported solid, including interior holes and camera reset behavior.

Printer data is a pinned, locally bundled snapshot. Follow [catalog reproduction and update instructions](printer-catalog.md#reproduce-the-snapshot) to regenerate it; review its source commit, attribution, profile inheritance, skips, geometry changes, and unknown-value handling. App startup does not silently refresh printer specifications from the network.

## Cloud environment notes

- A localhost address is local to the machine running the service. Use the host's supported access path from another machine.
- Keep the existing injected Git authentication, HTTP proxy, and certificate trust settings. A missing `GH_TOKEN` is not evidence that GitHub access is unavailable.
- No application secret is required for the included conversion workflow. Do not add API credentials merely to run it.
- A cloud backend receives uploaded photos. See [data handling](privacy-security.md) before describing this deployment as local or private.
- Installation prepares files; startup creates processes. A saved environment snapshot does not preserve live servers.

## Check a running instance

After startup, this smoke check exercises the real sample through the HTTP API, builds a solid, verifies its width and thickness, downloads STEP, and deletes its own temporary model:

```bash
make smoke
```

The direct `.venv/bin/python scripts/smoke.py` command remains available. To check the development proxy, use `PICAD_BASE_URL=http://127.0.0.1:4173 make smoke`. The default is the single-service startup on port 8000. This complements the full test suite; it does not replace browser verification.

## Optional slicer programs

`make slicers` reports filesystem discovery for Bambu Studio and PrusaSlicer without starting them. Configure `PICAD_ENABLE_SLICER_LAUNCH=1` and absolute `PICAD_BAMBU_STUDIO` / `PICAD_PRUSA_SLICER` executable paths before startup to permit explicit local GUI handoff. Programs on PATH and common app locations are also checked. Direct opening requires loopback and same-origin JSON; configure remotely hosted workbenches for downloads instead. Retained copies live in `.local/slicer-handoffs/` or `PICAD_SLICER_HANDOFF_DIR`, outside temporary job cleanup. See [slicer integration](slicers.md) for version targets and installation details.
