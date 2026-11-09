# Validation results

Validated November 8, 2026, in the managed Linux environment. The original CAD release and subsequent optional Ollama integration have separate evidence below. A freshly published cloud task has not been validated.

## Review fixes: recovery, tracing accuracy, and input checks

Separate code reviews of the backend, frontend, and reference library found 30 defects. This change set fixes them, removes the warnings from CI and the test runs, and adds a regression test for every code fix. The run below used the local workstation: Python 3.12.3, Node.js 22.13.1, Google Chrome 157.0.8103.38 through the system-Chrome fallback, and OpenSCAD 2021.01.

- **CI and build.** Both workflows use the Node 24 releases of their actions (v7 of `checkout`, `setup-python`, `setup-node`, and `upload-artifact`), run on `ubuntu-26.04`, and run once per pull-request push instead of twice. The tests and smoke check use `httpx2`, which Starlette's test client now expects. The production build puts three.js (1,003 kB, 272 kB gzip) and the other libraries (289 kB) in their own chunks, apart from the application's 76 kB. The development server binds to loopback by default, as `dev.sh` already did.
- **Frontend (10 fixes).**
  - **Try again** repeats only the failed step, using the inputs on screen. Before, an error with no retry of its own replayed an earlier step and could silently restore old dimensions and design settings.
  - A failed retrace no longer marks the model outdated.
  - An AI answer no longer takes focus from a field being edited.
  - Focus returns to the control that started busy work.
  - Undoing a suggestion that was never built keeps the model current.
  - Unit switching converts out-of-range entries.
  - Restored project names are cleaned like typed ones.
  - The outline toggle is disabled without a photo.
  - Printer profiles that describe one bed are not reported as ambiguous.
  - Leaving or reloading the page releases its temporary model files.
- **Backend (12 fixes).**
  - Malformed EXIF no longer returns HTTP 500.
  - Camera MPO JPEGs and 16-bit grayscale PNGs trace.
  - A speck inside a hole is ignored like a tiny hole.
  - Outlines now follow pixel edges, not boundary-pixel centres. The old tracing made outer spans 1 px short and holes 1 px large; a 51 px hole in a 401 px part was 2.2 % oversize. The sample is now 34.05 mm tall at 80 mm wide (previously 34.01 mm).
  - Negated wording such as "don't change the thickness" no longer authorizes a size proposal.
  - Expiry deletes only directories holding this application's job files, and it survives a failed pass.
  - Null bytes in frontend paths return 404.
  - Job files use explicit UTF-8.
  - Each hole ring is bounded before parsing.
  - The traversal test now reaches the download route.
  - The benchmark's dimension hint judges the model's raw proposal.
- **Workbench results.** `make test-app` passed with **179 Python tests** (146 before), production typecheck/build, and **23 Chromium browser scenarios** (15 before). The backend tests produced no warnings. `make lint` passed. `scripts/smoke.py` passed against the running service.
- **Regression checks.** 27 new or changed backend tests and 9 browser scenarios failed on the previous code. The strengthened traversal test passes on both versions, because that route was already safe.
- **Reference library (8 fixes; see its [changelog](../reference-library/CHANGELOG.md)).** `make release` passed over `file://` with **157 Python tests**, **25 Node test groups**, **101 page assertions**, **49 Photos assertions**, and **16/16** plate checks. `make test-library` passed the same counts over loopback HTTP.

HawkScan was not run because no `HAWK_API_KEY` is configured. These are software and geometry checks of synthetic fixtures; no part was sliced or printed. The CI results for this change set belong to its pull request.

## Reference library Photos fix: blob-URL race

After Revision 4 merged, both library CI runs failed. The Photos check's final assertion found two "Not allowed to load local resource: blob:null/…" console errors. The same failure appeared locally in about 1 run in 4, and in 1 of 20 instrumented runs, always as a filtered gallery refreshed. The gallery revoked its previous thumbnails' object URLs while those images still referenced them, so a lazy load that started late requested a revoked URL. The fix creates URLs only for the gallery actually shown and detaches old thumbnails before revoking. A new deterministic assertion (49 in total) fails on the previous code and passes now. The library and workbench results for this fix are in its pull request and the library's [verification record](../reference-library/VERIFICATION.md).

## Reference library Revision 4: Photos workspace

This change set adds the library's offline Photos workspace (Revision 4). It shares the browser checks' loopback server so the Photos check runs over both transports, and it keeps `reference-library/.venv` out of the library archive. The workbench code is unchanged. The run below used the same workstation and tools as the section that follows.

- Root commands: `make setup-library` completed, then `make test-library` passed. It ran **129 Python tests** and **22 Node test groups**, then **99 page assertions** and **48 Photos assertions** over loopback HTTP.
- Library: `make release` passed with both browser checks over `file://` (99 and 48 assertions) and **16/16** plate checks after an OpenSCAD render. Two PDF, HTML, and archive builds were each byte-identical, and ReportLab 4.4.9 and 4.5.1 produced the same PDF.
- Workbench: **146 Python tests** and `make lint` passed. The Chromium scenarios were not rerun because no workbench code changed.

The Photos checks use generated images in fresh browser contexts. They do not establish that a particular browser keeps photos for a `file://` page, and they are not a reconstruction or accuracy benchmark.

## Mesh interoperability and library review fixes

This change set addresses the automated review findings on the reference library's STL checker and homography calculator. It also adds `tests/test_mesh_interop.py`, which runs the library's independent STL checker on workbench exports. The run below used the local Linux workstation: Python 3.12.3, Node.js 22.13.1, uv 0.11.16, Google Chrome 157.0.8103.38 through `PLAYWRIGHT_CHROMIUM_EXECUTABLE`, and OpenSCAD 2021.01.

- Workbench: `./scripts/test.sh` passed with **146 Python tests** (the previous 142 plus 4 interoperability tests), production typecheck/build, and **15 Chromium browser scenarios**. `make lint` passed.
- Interoperability: the combined STL, an STL built from a traced photograph with two round holes, and both pieces of a 2 × 1 split bundle are closed, manifold, consistently oriented, and outward-facing. Each has one component and one genus per hole. Their volumes are within 0.01 % of the CAD solid, and split pieces start at the origin. The documented `python3 -m cadkit meshcheck … --expect-mm 80` command exits 0 on a workbench export.
- Reference library: `make release` passed with **129 Python tests**, **12 Node test groups**, **98 browser assertions** over `file://`, and **16/16** plate checks after an OpenSCAD render. The same 98 assertions also passed over loopback HTTP. Regenerated HTML matched the committed file, and the PDF matched its recorded SHA-256.

These are software and geometry checks of synthetic fixtures. They do not establish dimensional accuracy for an arbitrary photograph, and no part was sliced or printed. The CI results for this change set belong to its pull request.

## Repository command integration

The root Makefile exposes setup, build, test, and lint commands for the workbench and reference library while preserving each component's existing entry points. The combined `make setup` completed successfully. `PICAD_TEST_URL=http://127.0.0.1:8001 make test` then passed against an isolated workbench instance:

- Workbench: **142 Python tests**, production typecheck/build, and **15 Chromium browser scenarios**.
- Reference library: **119 Python tests**, **11 Node tests**, and **98 browser assertions** over loopback HTTP.

There were no failed or skipped tests in that completed run. `make lint`, shell and JavaScript syntax checks, and documentation file-link checks also passed. The library HTTP server closed after both a successful check and a deliberately failed browser launch. Interpreter paths containing spaces were checked through the library Makefile. No generated library content or dependency versions changed.

Direct library browser checks retain the `file://` default. This managed browser blocks that transport; the local pass above establishes HTTP behavior. The library CI checks both transports. Remote results below apply only to their named commits.

## Current design, print and assistant changes

The complete `PICAD_TEST_URL=http://127.0.0.1:8001 ./scripts/test.sh` run passed against an isolated instance of the design, print, and assistant implementation: **142 Python tests**, production typecheck/build, and **15 Chromium browser scenarios**, with no failures or skips.

The Python checks comprise 34 original CAD/API tests, 26 real geometry/printing tests, 6 printer-catalog tests, 69 assistant tests, and 7 benchmark tests. The browser run includes the original six workflows, five assistant-control scenarios, and four design/print scenarios.

Additional verified behavior:

- XY/thickness design scales change real STEP/STL geometry while preserving measured source inputs. Split solids are distinct pieces, preserve total volume, and match their preview meshes and ZIP manifest.
- Nozzle-relative simplification changes the actual CAD/DXF outline and retains holes. Printer checks use the exact matching nozzle profile, mark ambiguous/shaped/excluded beds unverified, and check margins, height, and 90-degree rotation.
- Version 2 saves restore design and appearance; version 1 imports still work. Invalid oversized recipes preserve the current project, and backend-normalized printer dimensions reach the interface and resaved recipe.
- Apply is explicit. Undo after a completed AI-assisted build restores the prior actual preview and settings; exports stay stale until a correct rebuild. Manual edits invalidate old proposals; stopped waits ignore late answers.
- Actual split meshes support assembled/separated inspection without changing downloaded ZIP bytes. A real WebGL context loss recovers through Retry. A retired-canvas event regression was found and fixed before this passing run.
- The expanded controls pass the selected axe-core checks on a 390 px viewport. Printer search tolerates punctuation and spacing. These checks are not a claim of complete accessibility conformance.
- The catalog contains 429 model groups, 70 manufacturer/profile families, and 1,106 nozzle profiles. Two imports of the pinned source produced identical bytes; three familiar models were independently checked against their inheritance chains. Unknown hardware capabilities remain unknown.

Ruff, touched frontend/browser-source Prettier checks, shell syntax, and local documentation links pass. The new printer data is fetched only when the design panel opens. No model weights or Ollama binaries are committed or downloaded in CI.

## Original CAD release: local results

| Check | Observed result |
| --- | --- |
| `./scripts/setup.sh` | Passed. Reused the Python environment, performed a frozen uv sync and clean npm install, and built the frontend successfully. |
| `./scripts/test.sh` | Passed: 34 backend tests, production typecheck/build, and 6 Chromium browser tests. No failed or skipped tests in that completed run. |
| Mobile typography follow-up | The affected keyboard/accessibility/mobile scenario passed again after the final helper-text adjustment. |
| Python lint and shell syntax | Ruff and `bash -n` passed for the application, backend tests, smoke helper, and shell scripts. |
| Frontend formatting | Prettier check passed for TypeScript, TSX, CSS, HTML, and browser-test/configuration files. |
| Package advisory check | `npm audit` reported zero known advisories at the time of this check, including development dependencies. |
| Running development service | The smoke helper passed through the Vite proxy on port 4173: served interface, traced sample, built solid, and downloaded STEP. |
| Visual comparison | [Passed](../design-qa.md), with paired source/implementation evidence and desktop/mobile captures. |

## Optional local assistant

The assistant uses the deterministic tracing and CAD pipeline. Proposals require user review; measured width and thickness are never proposal fields. Explicit design percentages can resize the resulting geometry.

- The 69 assistant checks and 7 benchmark-report checks are included in the complete 142-test run above. They use a local test HTTP daemon or explicit fixtures and do not measure an LLM's quality.
- The assistant checks cover loopback-only connections, rejected remote URLs and cloud aliases, unavailable/empty model lists, no automatic pulls, bounded context, discarded invalid or dimensional proposals, malformed output, timeout recovery, and the cancellation/concurrency boundary.
- Ruff passed across `backend`, `scripts`, and `tests`; the Ollama shell helper passed syntax checks and a verified-install run. Frontend type checking/build and touched-source Prettier checks passed.
- The actual **Ollama 0.40.15** runtime downloaded from its official GitHub release, matched SHA-256 `628c018404a4206493efd38e46251c154ede5141b8b8dc85c659b3b027c47379`, and started on `127.0.0.1:11434` with `OLLAMA_NO_CLOUD=1`.
- Live API checks reported the runtime version and an empty model list. The CAD backend correctly reported Ollama running with no models and returned HTTP 409 for an uninstalled model without changing CAD state.
- The actual `qwen3:1.7b` pull failed at the model manifest because the managed proxy denied `registry.ollama.ai`. The [recorded comparison preflight](benchmarks/ollama-preflight.json) found all three shortlisted models missing and attempted **zero inferences**. Model weights, answer quality, memory use, and inference speed remain unverified.

The model shortlist is provisional. See [local AI setup](ollama.md) and [model research](ollama-models.md). Network draft changes must be applied before downloading and comparing the candidates; integration fixtures are not substitutes for that test.

## GitHub-hosted CI

Both workflows completed with **Success** for merge commit `5d6a446d6175e4ad1bd0c01c0166b05e0d1e393a`:

| Workflow | Recorded run | Scope |
| --- | --- | --- |
| Validate workbench | [42528803054](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42528803054) | Locked workbench setup/build, Chromium installation, Ruff, Python and browser workflow checks |
| Validate reference library | [42528803055](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42528803055) | Library regeneration and drift checks, Python/Node tests, required OpenSCAD plate pipeline, and browser checks |

These runs use `ubuntu-latest`, Python 3.12, and Node.js 24. They validate that exact merge commit. They do not validate later repository-command or browser-transport changes before those changes receive their own completed runs.

Earlier workbench evidence remains available: the [feature run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42528243229) passed for `f4b924517c6f58fe34686f380c478e55ba67d4ef`; the [original CAD run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42519068333) passed for `96d73c6ef1b6ee50759f1835e63717835772b4f1`.

The library has a separate [verification record](../reference-library/VERIFICATION.md) describing its 157 Python tests, 25 Node test groups, and browser assertions. Those checks are additional to the workbench's 179 Python tests and 23 browser scenarios; they do not evaluate real photograph reconstruction, physical printing, or LLM quality. Counts, skips, and browser transport belong to the particular recorded invocation rather than the mere presence of a test command.

## Geometry and API evidence

The synthetic reference profile is 100 × 60 units with two 10 × 10 square holes. Scaling to 80 mm width and extruding 4 mm produces an 80 × 48 × 4 mm solid with expected volume **14,848 mm³**.

The backend suite verifies:

- Correct dimensions, positive volume, expected hole count, and matching settings revision.
- STEP re-import as one valid solid with the expected dimensions and volume.
- Binary STL structure, expected bounds, and exactly two incident triangles at every welded mesh edge.
- Independent STL checks by the reference library's `cadkit` (see above): closure, vertex manifoldness, orientation, one component, and one genus per hole for combined, traced, and split exports.
- DXF millimeter units and three closed profile rings for the two-hole fixture.
- Reproducible project-recipe content.
- Trace hierarchy, foreground inversion, EXIF orientation, and removal of source metadata from the normalized display image.
- Invalid image data, empty/edge-clipped images, upload and decoded-pixel limits.
- Nonfinite/invalid dimensions, invalid or intersecting profiles, invalid download paths, expiry, and deletion.
- CAD timeout cleanup, storage-capacity preservation, one-at-a-time image tracing, repeated request cancellation, and cleanup protection during active CAD work.

These fixtures establish software behavior under their stated conditions. They do not establish a dimensional accuracy guarantee for arbitrary photographs or replace physical measurement.

## Browser evidence

The original six scenarios below also passed in the complete 15-scenario run against the current built application:

1. Trace the supplied sample, render the actual solid, and download STEP, STL, and DXF files with format checks.
2. Change thickness, invalidate old exports, rebuild, switch display units without altering physical size, save a recipe, and restore/rebuild it.
3. Upload a photo, require measured dimensions, build a part, and preserve the prior valid result after a malformed upload.
4. Check keyboard dialog opening/closing and focus restoration, run axe-core A/AA rules on the workbench, and operate the export dialog at a 390 px mobile width without horizontal overflow.
5. Remove the current server artifact, surface its failed download in the UI without downloading an error file, and rebuild successfully.
6. Clear temporary exports through the interface, retain editable dimensions and outline, and build again.

The sample scenario recorded no JavaScript page exceptions or browser console errors. Expected failed HTTP requests in negative scenarios were checked as recovery behavior. The workbench returned zero violations in the selected axe-core rules. Complete screen-reader, cross-browser, and device-lab testing remain outside this run.

The final mobile typography change was followed by a passing rerun of scenario 4 against the development server. The local HTML Playwright report reflects the most recent local invocation. The GitHub workflow retains its own browser reports and failure traces according to its seven-day artifact policy.

## Runtime and reproducibility

- Tested runtime: Python 3.12.14, Node.js 24.22.1, npm 11.9.0, uv 0.13.5.
- Dependencies are recorded in `uv.lock` and `package-lock.json`; setup preserves both locks.
- Python is restricted to 3.12 because the selected CAD binary stack includes VTK 9.3.1 wheels through CPython 3.12. The project does not claim Python 3.13 support.
- The local machine already provided uv. The setup script's uv-absent bootstrap branch was not separately exercised in the local validation run.
- The service uses one API process and bounded CAD subprocesses. No GPU or third-party reconstruction API was required.
- A development startup and shutdown were exercised; the final single-service startup serves the built interface and API together.
- The Sites preview relay was unavailable. Actual Chromium against the application provided browser evidence; there is no published site or user-facing hosted preview.

## Remaining notices and limits

The build and backend tests run without warnings. The 3D stack is still the largest download: three.js is a 1,003 kB chunk (272 kB gzip) that loads with the page because the preview is on the first screen. The build's chunk-size limit sits just above it, so unexpected growth still warns. In the browser console, React Three Fiber 9.8.2 logs a `THREE.Clock` deprecation warning. It comes from the library, not this application, and only its version 10 pre-releases change it. Renderer dependency warnings are distinct from application console errors.

This is a working single-user, constant-thickness profile workbench. It has no public-service authentication, collaborative project database, arbitrary-object reconstruction, manufacturing certification, or validated metrology. See [scope](roadmap.md), [capture guidance](capture-guide.md), and [data handling](privacy-security.md).
