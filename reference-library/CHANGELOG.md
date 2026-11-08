# Changelog

All dates are 2026. Revisions are numbered in `library.json`, which feeds the HTML, the PDF, and the archive name. Revision 3 is the first revision kept in this repository; Revisions 1 and 2 were distributed as ZIP archives.

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
