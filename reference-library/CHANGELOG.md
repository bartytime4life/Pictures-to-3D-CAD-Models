# Changelog

All dates are 2026. Revisions are numbered in `library.json`, which feeds the HTML, the PDF, and the archive name. Revision 3 is the first revision kept in this repository; Revisions 1 and 2 were distributed as ZIP archives.

## Revision 4 (November 8, 2026)

### Added

- An offline **Photos** workspace with repeated multi-select and drag-and-drop intake, no fixed photo-count cap, sequential decoding, local original storage, and a paged thumbnail gallery.
- Byte-fingerprint duplicate detection, content and dimension validation, cancellation, readable storage failures, and atomic per-photo writes.
- Manual viewpoint coverage, searchable notes, saved reference and target endpoints, and known-length dimension estimates with explicit planar and perspective limitations.
- Original download, per-photo removal, and a metadata-only photo manifest export. Photos are never sent to a server, and the manifest is not an image backup.
- Automated photo validation tests (`tests/node/photos.test.mjs`) and isolated browser checks with synthetic images (`scripts/check-photos.mjs`). They cover persistence, multi-batch additions, measurement arithmetic, duplicate races, storage failure, and mobile layout. This is an intake and reference workflow; no 3D reconstruction or physical accuracy qualification is claimed.

### Changed

- **One loopback server for both browser checks.** The private HTTP server from `check-library.mjs` moved to `scripts/lib/serve.mjs`. The photo check now honours `CAD_REFERENCE_BROWSER_TRANSPORT` too, so the repository's root `make test-library` and CI test the Photos tab over the same transport as the rest of the page. Each record notes its transport.
- **`make check`** runs both browser checks, and `make verify` requires a passing, current photo check.

### Fixed

- **The archive no longer packages local environments.** `make-dist.py` now skips `.venv`, `.cache`, and `.ruff_cache`. `make setup-library` at the repository root creates `reference-library/.venv`, which a later `make dist` would otherwise have added to the ZIP.

## Revision 3 maintenance (November 8, 2026)

Fixes from the automated Codex review of pull request #2, plus a cross-check with the workbench. The revision number, archive name, and content are unchanged apart from the items below.

### Fixed

- **STL welding no longer depends on grid alignment.** `cadkit meshcheck` used to round coordinates to a `--weld-tol` grid, so two points 10⁻⁹ apart that straddled a cell boundary stayed separate. A cube shifted by half a cell reported 10 boundary edges and two components. Vertices are now merged by distance, using a spatial hash that searches neighbouring cells.
- **Pinched vertices fail the mesh check.** Two closed shells touching at one corner have two faces on every edge, so the check used to pass them. `meshcheck` now reports `nonmanifold_vertices` and `manifold`, requires a manifold mesh for `status: pass`, and reports genus only for closed 2-manifolds. The plate pipeline gained a matching check (16 instead of 15).
- **Non-finite STL coordinates are invalid input.** A NaN or infinite vertex now gives a clear error and exit code 2. An infinite vertex used to end in a traceback with exit code 1, which reads as a mesh that failed its checks.
- **Large homography inputs stay fast.** The near-collinear warning applies only to 4–6 points, but both implementations scanned every point triple first, which is cubic in the number of points. In Python, 400 points took about 5 seconds. Both now check the count first, and the browser calculator no longer stalls on long point lists.

### Added

- **Workbench interoperability tests** (`../tests/test_mesh_interop.py`). The workbench's test suite runs this library's STL checker on combined STL exports, a traced photograph with round holes, and each split part. It also runs the documented `meshcheck` command on a workbench export.
- **Record tests.** `test_docs` now checks the test, assertion, and plate-check counts in `VERIFICATION.md` against `verification.json`, and the record notes the browser transport that was checked.

## Revision 3 (November 8, 2026)

### Added

- **Figures.** Ten explanatory figures plus a banner, defined once in `scripts/figures.py` and rendered as SVG for the HTML and Markdown and drawn natively in the PDF. The figures are a route map, the evidence-class ladder, homography rectification, off-plane depth, chord error with a computed error curve, clearance, three fidelities, three tiers of checks, catalog composition from `sources.json`, and the process flow.
- **Toolkit tab** in `index.html`. A route finder covers 7 inputs × 5 goals. The 14 calculators include a homography fit with residuals, local scale, and anisotropy, and an import-unit detective. Calculators flag the handbook's warning conditions, link to their sections, and can be reached by deep link (`#calc-depth`).
- **`cadkit` Python package**, standard library only: `python3 -m cadkit` with 19 commands. These cover handbook formulas, a normalised-DLT homography, an ASCII/binary STL checker (extents, volume, closure, orientation, components, genus, unit hints), a design-parameter register loader, OpenSCAD rendering, a project scaffolder, and the route finder.
- **Example pipeline.** `examples/plate-parameters.csv` drives `two-hole-plate.scad` through `build_plate.py`, and the resulting STL is checked against design rules. `examples/clearance-coupon.scad` is a parameterised hole-clearance coupon with optional labels.
- **Tests.**
  - Python `unittest` covers formulas, homography, STL, parameters, OpenSCAD, the CLI, routes, catalog schema, and documentation accuracy. Counts, links, and worked numbers are asserted against the data.
  - `node --test` compares the browser calculators and the route finder with the Python implementation.
  - A Playwright browser check exercises every tab, filter, calculator, deep link, theme, and layout.
- **Library interface.**
  - Light and dark themes.
  - Catalog filters for review depth and level, sorting, topic chips, and filter state kept in the URL.
  - Handbook scroll-spy, a reading-progress bar, and section anchors.
  - Keyboard tab navigation (arrows, Home, End) and `/` to search.
- **Maintenance scripts.** `scripts/check-links.mjs` checks links over the network, `scripts/refresh-github.mjs` refreshes repository metadata, `scripts/record-verification.py` writes `verification.json`, and `scripts/make-dist.py` writes the manifest and a deterministic ZIP to `dist/`.
- **Project files.** A GitHub Actions workflow (`.github/workflows/reference-library.yml`), `Makefile` targets, `package.json` with `package-lock.json` and `requirements.txt` for portable, pinned dependencies, `.gitignore`, `CONTRIBUTING.md`, and this changelog.
- **Handbook section 23**, "Companion toolkit", and a Revision 3 note in section 22.

### Changed

- **Portable build.** The build scripts resolve dependencies from a local `npm install`, `CAD_REFERENCE_NODE_MODULES`, or the original Codex runtime. They no longer require one machine-specific path. The PDF builder finds DejaVu fonts itself or reads `CAD_REFERENCE_FONT_DIR`.
- **Reproducible PDF.** ReportLab invariant mode makes rebuilding unchanged sources byte-identical, so `SHA256SUMS` stays valid. The PDF now has the figures, a banner cover, and counts read from the data rather than typed in.
- **Generated counts.** Counts in the browser check and PDF come from `sources.json`, `library.json`, and the calculator list instead of being hard-coded.
- **Stable anchors.** Handbook headings have readable, stable anchors such as `#book-6-workflow-a-...` instead of positional `#book-12`.
- **Catalog sources.** The GitHub metadata snapshot was refreshed with four newer pushes, and the `utm_` tracking parameters were removed from eight SciSpace URLs.
- **Handbook accuracy.** The sweep self-intersection statement now names the profile's extent toward the centre of curvature. Section 22 states precisely which software was run.
- **Examples.** The README and PDF page now report the actual OpenSCAD render and STL checks instead of saying the renderer was not executed.

### Fixed

- Long repository names in GitHub headings overflowed the page on phones.
- The PDF worksheets had printed their checklists without checkboxes since Revision 1, and the nested list under "Design-rule checks" had collapsed into one paragraph. Both now render, with ☐ boxes in the DejaVu font.
- Issues found by an independent review of the new code, each covered by a regression test:
  - URL-encoded catalog state lost topics containing "&" after a reload.
  - Empty calculator fields were treated as zero.
  - `record-verification.py` could accept a stale browser record.
  - The JavaScript rounding and eigen-solver stopping rules differed slightly from Python's.
  - `cadkit label --decimals 400` and `cadkit chord --error 1e-17` crashed instead of reporting invalid input.
  - `cadkit homography --points` failed on long inline JSON.
  - `route --all` hid its warnings in text mode.
- `cadkit` homography results depended on the Python version: Python 3.12 made `sum()` of floats compensated, which moved ill-conditioned fits away from the browser twin. `cadkit/homography.py` now adds in one explicit order, and the parity tests pass on Python 3.10 and 3.14.

## Revision 2 (November 8, 2026)

Added governing decisions, unit and axis conventions, image provenance, and label rounding. Added single-view calibration checks, depth correction, and camera distance. Added Workflow E for organic subjects with mechanical interfaces, and held-object design. Added process selection, scripted-pipeline structure, and three tiers of checks. Also new: troubleshooting rows, exercises 7–8, a design-parameter register, and seven sources.

## Revision 1 (November 8, 2026)

The initial library: a handbook, 79 annotated resources, research notes, worksheets, and synthetic examples.
