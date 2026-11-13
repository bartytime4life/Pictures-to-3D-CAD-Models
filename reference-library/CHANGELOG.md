# Changelog

All dates are 2026. Revisions are numbered in `library.json`, which feeds the HTML, the PDF, and the archive name. Revision 3 is the first revision kept in this repository; Revisions 1 and 2 were distributed as ZIP archives.

## Revision 7 — November 9, 2026

- Connect the photo-to-CAD workflow to OpenSCAD with an offline mounting-plate and clearance-coupon workspace, dimensioned sketches, evidence fields, and SCAD/CSV/SVG downloads.
- Add `cadkit openscad doctor` and checked native builds, bringing the current CLI to a toolkit with 20 commands. Share model parameters and bounds with the browser.
- Preserve earlier exports on invalid input, failed renders and timeouts; commit complete new builds only after geometry checks pass.
- Record complete source, parameter, schema and output hashes, OpenSCAD versions, logs and actual-mesh checks. Include real default-model renders and editable starter files.
- Exercise browser downloads through actual OpenSCAD renders, with isolated desktop/mobile checks and preservation regression tests. Rebuild the handbook, verification record and portable archive. No slicing or physical print qualification.

### Workbench active-face result navigation — November 13, 2026

Link the [completed active-face study and saved-only physical census](../docs/validation/finite-acquisition-physical-rounding.md):
corrected selected 821 tests/33 subtests pass, full recovery remains 11/12 and
exit 1, and none of 128 adjacent physical candidates pass the unchanged gates.
The 49 diagnostic controls pass. Preserve all prior first outcomes and release
records; these documentation links add no library tool or qualification.

### Documentation maintenance — November 13, 2026

Correct chapter 15's build-volume guidance: a diagonal placement can fit when
its complete footprint and height, required supports and clearances fit within
the usable volume at that orientation. Rebuild the reader and PDF from the
handbook source. This correction does not change the revision label or refresh
the dated release-verification record, catalog snapshot or archive.

### Workbench research navigation — November 13, 2026

Link the [local acquisition-recovery snapshot](../docs/finite-acquisition-recovery.md)
and [documentation review](../docs/validation/documentation-recovery-state.md)
from the repository-facing library guides. The snapshot retains both failed
full protocols, their partial target passes, candidate-only tests and the
unresolved saved-audit comparisons. This is a documentation update, not a library
release or an addition to main's runtime or the Photos tab. The handbook text,
generated HTML/PDF, catalog, release counts and dated verification stay unchanged.

### Exact active-face research navigation — November 13, 2026

Link the [exact active-face method](../docs/finite-acquisition-protected-active.md)
and its [first selected software outcome](../docs/validation/finite-acquisition-protected-active.md):
820 passes, one failed test expectation and 33 passing subtests, exit 1.
No full recovery study or corrected control run has occurred. Library code,
generated reader/PDF and dated release verification remain unchanged.

### Protected-projection research navigation — November 13, 2026

Link the [protected-source-bin design](../docs/finite-acquisition-protected.md)
and its [eight failed first software controls](../docs/validation/finite-acquisition-protected.md).
The full recovery study has not run. This documentation does not change the
library release, generated reader/PDF or dated verification.

### Executed research navigation — November 13, 2026

Link the [coupled and source-event results](../docs/validation/finite-acquisition-continuations.md)
and [completed saved-only audits](../docs/finite-acquisition-saved-audit.md).
All four complete recovery protocols remain failed; these research records do
not change the library release, generated reader/PDF or physical acceptance.

### Unexecuted research navigation — November 13, 2026

Link the [coupled proposal](../docs/finite-acquisition-coupled.md) and
[archive/audit guide](../docs/finite-acquisition-saved-audit.md). These authoring
snapshots add no library runtime, release or verification result. Generated
HTML/PDF and dated release records remain unchanged.

## Revision 6 — November 9, 2026

- Keep catalog search and filters in easy reach, with an expandable coverage chart, a clear empty-state reset, and larger touch targets. Preserve filter links when moving between tabs.
- Show unsaved photo edits and protect notes, viewpoints, and measurement points on Close, Escape, and supported browser navigation. Explicit discard retains the last saved details.
- Release image sources before revoking preview URLs, including abandoned gallery refreshes, to avoid intermittent preview-load errors.
- Detect mesh vertices where disconnected surfaces meet at a single point; fail those mesh checks and withhold genus. Exclude degenerate faces from topology, and report invalid numeric geometry cleanly.
- Add independent-check worksheets to the browser, PDF, and new-project folders. Separate calibration evidence, held-out dimensions, uncertainty, and physical print acceptance.
- Add two primary sources on uncertainty-aware acceptance and independently checked photogrammetry, taking the catalog to 88 records.
- Rebuild the offline library, PDF, validation record, checksum manifest, and portable archive. Physical reconstruction and printing remain unperformed.

## Revision 5 (November 8, 2026)

- Added portable folder backup of unchanged originals, viewpoint labels, notes, and measurement points. Files are written sequentially to a new folder; the manifest is committed last.
- Added folder restore with manifest validation, image fingerprint and geometry checks, current-annotation preservation for existing photos, cancellation, and truthful partial-failure reporting.
- Added a measurement CSV matching the project worksheet. Estimates remain image-derived, unknown fields stay blank, and source points and fingerprints travel with each row.
- Added transfer and CSV tests plus isolated browser backup/restore acceptance. Native folder-picker interaction remains a manual browser boundary; no physical-object accuracy benchmark was performed.

## Revision 4 maintenance (November 8, 2026)

Fixes from a review of the toolkit after Revision 4 merged. The revision number, archive name, and content are unchanged apart from the items below. The handbook and PDF are unchanged; `index.html` changes only because it inlines `cadcalc.js`.

### Fixed

- **A malformed ASCII STL facet is invalid input.** The reader matched only plain decimals, so it skipped `vertex nan nan nan`, `inf`, `1,5`, and `1D+01`, and the following vertices regrouped across facets. A box plus such a facet reported `status: pass` with exit code 0. Each `vertex` line must now hold three numbers and each facet exactly three vertices; otherwise `meshcheck` exits 2 and names the line. NaN and infinite coordinates are rejected as they are in binary files.
- **Invalid input no longer exits 1.** Exit code 1 means a check failed, yet malformed `--points` JSON, a directory or unreadable file, an unusable `new-project` path, and arithmetic overflow ended in a traceback with exit code 1. `--points` is now validated against its two documented shapes. The CLI reports type, index, file-system, and overflow errors as one `error: …` line with exit code 2. `uncertainty` and `wind` results too large to represent raise `ValueError` in Python and an error in the browser, instead of a traceback or infinity.
- **The homography query point is checked.** `homography --at nan nan --json` printed bare `NaN`, which is not valid JSON. A pixel beyond the plane's vanishing line got a confident mapping: in the review's example, pixel (500, 50) mapped to y = −3000 mm with a local scale of 56 mm/px and no warning, although it does not image the plane at all. Python and the browser now require a finite point on the control points' side of the vanishing line (the same sign of `w`) and refuse any other with the same message.
- **Coupon rounding matches Python at exact ties.** The browser rounded exact binary ties such as 0.0078125 away from zero, while Python rounds them to even, so `coupon --start 0.0078125` gave 0.007813 in the browser and 0.007812 in Python. A double is such a tie only when it is an odd multiple of 1/128, and those values now take the even digit in both.
- **Range checks.**
  - `wind --diameter -2` returned a power estimate, because squaring the diameter drops its sign. The CLI now requires a positive diameter, as the browser does.
  - The gear pressure angle must lie strictly between 0° and 90° in both languages. Previously 95° was accepted, and 180° gave an undercut limit of 1.3 × 10³² teeth.
  - `depth` silently ignored `--z-range` without `--delta-range`, or the reverse; it now exits 2.
  - `--weld-tol` must be positive, finite, at most 1e100, and large enough for the coordinates. `inf` welded every vertex together, `nan` gave a confusing message, and `1e-320` overflowed the welding grid.
  - `chord_report(10, segments=3.5)` truncated to 3 segments; it now raises `ValueError`, like `chord_error`.
- **Byte-order marks.** A register saved as "CSV UTF-8" by a spreadsheet starts with a byte-order mark and failed with "missing columns parameter_id". Registers and `--points` files are now read with `utf-8-sig`.
- **The verification record keeps the last link check.** `make verify` wrote `"external_links": null` whenever the network link check had not been run on that machine, erasing the most recent result that `VERIFICATION.md` describes. It now keeps the previously recorded result until `make links` produces a new one.
- **Degenerate-face wording.** `cadkit/README.md` said degenerate faces are excluded from the topology checks. Only collapsed faces, with fewer than three distinct welded vertices, are excluded. Zero-area slivers are counted as degenerate, which fails `meshcheck`, but their edges still count. The code is unchanged; the README now says this, and a test locks it in.

### Added

- Regression tests for each item: 28 Python tests, 3 Node test groups that compare both languages, and 2 browser assertions (the homography refusal and the wind calculator's diameter check). Each code fix's test failed before the fix.
- `cadkit/README.md` describes what exit code 2 covers, the homography `at` rule, ASCII STL parsing, the weld-tolerance bounds, and the new shared conventions.

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

- **Thumbnails no longer request revoked blob URLs.** When the gallery refreshed while the previous thumbnails were still lazily loading, their object URLs were revoked while the images still pointed at them. A fetch that started late then failed: Chrome logs "Not allowed to load local resource" on `file://` pages, and the thumbnail is missing. This intermittently failed the photo check, about 1 run in 4 to 1 in 20 locally, and on both CI runs after Revision 4 merged. URLs are now created only after the last await, for the gallery that is actually shown. Old thumbnails drop their source before it is revoked, and the detail view revokes its previous URL only after switching. A new deterministic browser assertion fails if any image keeps or receives a revoked URL.
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
