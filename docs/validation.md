# Validation results

Validated November 8, 2026, in the managed Linux environment, followed by the successful GitHub-hosted CI run recorded below. A freshly published cloud task has not been validated.

## Local results

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

## GitHub-hosted CI

The **Validate workbench** workflow completed with **Success** for commit `96d73c6ef1b6ee50759f1835e63717835772b4f1`. The [workflow run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42519068333) and its [test job](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42519068333/job/128848357811) provide the remote evidence.

The workflow runs locked dependency setup and build, browser installation, Python lint, and the backend/build/browser test sequence on `ubuntu-latest` with Python 3.12 and Node.js 24. This result applies to the exact commit above. Later changes, including this documentation update, are not covered by that run until a subsequent run verifies them. The detailed counts below are the recorded local test results.

## Geometry and API evidence

The synthetic reference profile is 100 × 60 units with two 10 × 10 square holes. Scaling to 80 mm width and extruding 4 mm produces an 80 × 48 × 4 mm solid with expected volume **14,848 mm³**.

The backend suite verifies:

- Correct dimensions, positive volume, expected hole count, and matching settings revision.
- STEP re-import as one valid solid with the expected dimensions and volume.
- Binary STL structure, expected bounds, and exactly two incident triangles at every welded mesh edge.
- DXF millimeter units and three closed profile rings for the two-hole fixture.
- Reproducible project-recipe content.
- Trace hierarchy, foreground inversion, EXIF orientation, and removal of source metadata from the normalized display image.
- Invalid image data, empty/edge-clipped images, upload and decoded-pixel limits.
- Nonfinite/invalid dimensions, invalid or intersecting profiles, invalid download paths, expiry, and deletion.
- CAD timeout cleanup, storage-capacity preservation, one-at-a-time image tracing, repeated request cancellation, and cleanup protection during active CAD work.

These fixtures establish software behavior under their stated conditions. They do not establish a dimensional accuracy guarantee for arbitrary photographs or replace physical measurement.

## Browser evidence

Six complete scenarios ran against the built application in Chromium:

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

The build reports a large JavaScript chunk associated with the 3D stack (approximately 364 kB gzip). A Starlette TestClient/httpx deprecation warning appears in the backend test runner. Neither prevented the verified workflow. Renderer dependency warnings are distinct from application console errors.

This is a working single-user, constant-thickness profile workbench. It has no public-service authentication, collaborative project database, arbitrary-object reconstruction, manufacturing certification, or validated metrology. See [scope](roadmap.md), [capture guidance](capture-guide.md), and [data handling](privacy-security.md).
