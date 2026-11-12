# Documentation review through PR #72 — November 12, 2026

This documentation update reviews published
[PR #72](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/72)
at `25ff63a2452d6d47ac382f2cf15bfb403d6a6203`, tree
`f99a1738ebf34268194bc75cb2c0a73a2b336054`. During the audit, PR #72 was
merged into `codex/tapered-cap-geometry` at
`c3bd7bfd43c92904959a970825f61544c7c5a206`; the merged tree is identical.
This documentation update uses that merged base. Work is isolated on
`codex/documentation-arc-state`. The primary checkout remains at
`d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`; unfinished finite-shape
source and tests remain in their separate local worktree. Use the
[task index](../README.md) for guides and [project status](../project-status.md)
for integrated, review and exact-head hosted observations.

## Corrections and scope

- Identify the published arc-join repair by commit, tree and review-branch merge
  rather than describe it as an unpublished proposal. Refresh its exact-head
  hosted result from in progress to success, preserving both observations and
  keeping its local regressions separate from integration into `main`.
- Describe mixed STEP output accurately: accepted circles/arcs are analytic;
  retained traced boundaries remain polygonal. Design-intent recovery may
  deliberately change a model-derived radius.
- State the request middleware's additional 64 KiB allowance separately from
  the 32 MiB photo-file limit.
- Explain that projected source fitting and all-pixel standardized least squares
  coincide when every source mode is retained; omitted modes change the objective.
- Correct the handbook's rejection of diagonal placement. A supported footprint
  can fit diagonally; required supports and clearance must fit as well.
- Clarify the current treatment of collapsed and sliver STL triangles without
  rewriting the dated implementation history.
- Review current guides, historical records, worksheets and generated documents;
  connect the complete coverage record to current navigation.

The finite-shape prototype is outside the reviewed source and this PR. Its local
working guide is explicitly marked unfinished; no inverse-recovery result,
serialization contract or production integration is promoted into these guides.
Existing mathematical model assumptions, uncertain inputs, retained unknowns and
physical qualification limits remain visible.

## Verification

All **97 Markdown documents**, **1,729 local Markdown references**, **119 heading
fragments** and **161 tables** pass structural/navigation checks with zero errors.
The additional local HTML image also resolves. The complete inventory follows. Source inspections cover current API/configuration defaults,
commands, mathematical contracts, visible controls, storage and export behavior.
Unchanged historical records retain their original dates, counts and limitations;
external source catalogs are not a fresh upstream metadata or URL audit.

All 41 argparse help paths and root `make help` succeed. All 26 existing
command/API/example checks pass, including both endpoint maps against the 11
OpenAPI operations, raw-source signatures, response/rectangle/Gaussian JSON and
Python examples, source/input hashes, invalid-input handling and original-report
preservation on overwrite refusal. Those checks complete before library
regeneration, with all 431 tracked non-Markdown files matching the baseline.
They require no server, personal images, model inference or native applications.

The existing library documentation-accuracy suite passes **all 19 tests** after
the changes:

```bash
.venv/bin/python -m unittest discover -s reference-library/tests/python -p test_docs.py -v
```

An intermediate run found a link to this not-yet-created review record. The
library note now names the repository audit without introducing that parent-path
navigation dependency into the standalone library. The failed receipt is retained
separately; final checks use the complete documentation tree.

The regenerated reader passes its existing **112 browser assertions with each
transport**, first offline `file://`, then a private loopback HTTP server. These
checks cover tabs/deep links, local files/anchors, figures, catalog filters,
calculators, route finder, theme and desktop/mobile overflow, with no browser
errors. The HTTP server is test-owned and closed by the runner. Separate
receipts retain each transport; these are reader checks, not workbench browser,
Photos/OpenSCAD handoff or native-application qualification.

```bash
CAD_REFERENCE_BROWSER_TRANSPORT=file node reference-library/scripts/check-library.mjs
CAD_REFERENCE_BROWSER_TRANSPORT=http node reference-library/scripts/check-library.mjs
```

The runner writes the same QA path, so preserve `tmp/qa/browser-check.json` and
screenshots before running another transport when both receipts are needed.
This review retains each JSON receipt under ignored `.local/verification/`.

### Generated handbook

The handbook source change is regenerated through the existing library targets:

```bash
make -C reference-library pdf PDF_PYTHON=/path/to/python-with-reportlab-and-lxml
```

This uses `figures`, `html` and `pdf` in dependency order. The recorded environment
uses Node.js 22.13.1, ReportLab 4.4.9 and lxml 6.1.1. The default PDF interpreter
fallback is described in [library build instructions](../../reference-library/BUILD.md).
No catalog metadata refresh, library release or archive build is performed.

The PDF remains 59 pages. Extracted-text comparison identifies pages 21 and 22
only: the corrected placement paragraph adds one line and moves the following
clearance paragraph to page 22. Both complete pages are rendered and visually
reviewed for clipping, headings, diagrams and pagination. The generated HTML
contains the same corrected paragraph. No interaction source changes.

| Regenerated documentation artifact | SHA-256 |
| --- | --- |
| [HTML reader](../../reference-library/index.html) | `ef12656e65b268c27c6166e9d2d3a89f0be8944826be2d7f54e4d51bb080ed6e` |
| [PDF handbook](../../reference-library/output/pdf/pictures-to-printable-cad.pdf) | `0e054ab176971f8667b94ae93e0580b94aa99b681a93f67f5942ebff4f7c61b9` |

The other 429 tracked non-Markdown files match the reviewed baseline. Runtime
source, tests, lockfiles, workflows, study plans/results, figures, catalogs,
`library.json` and `verification.json` are unchanged. Revision 7's November 9
release verification remains historical and does not qualify these revised
artifacts. The library's [verification note](../../reference-library/VERIFICATION.md)
keeps that distinction explicit.

This documentation pass does not rerun the complete workbench Python/browser
suite, native slicers or physical measurements. PR #72's 1,609 Python tests,
74 isolated browser scenarios and independent geometry controls retain their
[source-bound record](canonical-arcs.md), including the earlier failures.
Documentation checks are not a new engineering or physical acceptance result.

## Coverage inventory

**12 existing Markdown documents** are updated, **84 remain unchanged** and this
new record brings the total to **97**. All source Markdown is included below. Current guides are compared with relevant
source contracts; historical and generated records are checked for navigation
and consistency while preserving their evidence. A review need not change a
file that remains accurate. HTML/PDF rebuild checks are listed separately above.

| Document | Review role |
| --- | --- |
| [README.md](../../README.md) | Current workbench guide or navigation; source contract reviewed |
| [data/PRINTER_SOURCES.md](../../data/PRINTER_SOURCES.md) | Dated evidence retained; current audit separately scoped |
| [design-qa.md](../../design-qa.md) | Dated evidence retained; current audit separately scoped |
| [docs/README.md](../README.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/api-examples.md](../api-examples.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/architecture.md](../architecture.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/capture-guide.md](../capture-guide.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/changelog.md](../changelog.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/contributing.md](../contributing.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/corner-feasibility.md](../corner-feasibility.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/developer-tools.md](../developer-tools.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/development.md](../development.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/edge-crossings.md](../edge-crossings.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/engineering-model.md](../engineering-model.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/exports.md](../exports.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/gaussian-response-domains.md](../gaussian-response-domains.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/material-gradients.md](../material-gradients.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/ollama-models.md](../ollama-models.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/ollama.md](../ollama.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/photo-benchmark.md](../photo-benchmark.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/pixel-apertures.md](../pixel-apertures.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/print-planning.md](../print-planning.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/printer-catalog.md](../printer-catalog.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/privacy-security.md](../privacy-security.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/profile-observations.md](../profile-observations.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/project-status.md](../project-status.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/raw-source-fit.md](../raw-source-fit.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/reference-sensitivity.md](../reference-sensitivity.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/reference-sheet.md](../reference-sheet.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/research.md](../research.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/response-calibration.md](../response-calibration.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/response-rectangles.md](../response-rectangles.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/roadmap.md](../roadmap.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/signed-stencils.md](../signed-stencils.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/slicers.md](../slicers.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/troubleshooting.md](../troubleshooting.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/validation.md](../validation.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/validation/benchmark-correspondence.md](benchmark-correspondence.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/canonical-arcs.md](canonical-arcs.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/ci-runtime-budget.md](ci-runtime-budget.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/contrast-recovery.md](contrast-recovery.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/corner-blur-domains.md](corner-blur-domains.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/corner-feasibility.md](corner-feasibility.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/curved-placement.md](curved-placement.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/directional-spread-qualification.md](directional-spread-qualification.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/documentation-alignment.md](documentation-alignment.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/documentation-complete-2026-11-12.md](documentation-complete-2026-11-12.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/documentation-current-state.md](documentation-current-state.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/documentation-latest.md](documentation-latest.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/documentation-math-state.md](documentation-math-state.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/documentation-pr70.md](documentation-pr70.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/documentation-pr72.md](documentation-pr72.md) | Current documentation coverage and verification |
| [docs/validation/documentation-refresh.md](documentation-refresh.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/documentation-response-state.md](documentation-response-state.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/documentation-review-2026-11-12.md](documentation-review-2026-11-12.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/edge-crossings.md](edge-crossings.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/engineering-audit.md](engineering-audit.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/fillet-sweep.md](fillet-sweep.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/fit-support.md](fit-support.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/gaussian-response-domains.md](gaussian-response-domains.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/guided-workbench.md](guided-workbench.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/material-gradients.md](material-gradients.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/pixel-apertures.md](pixel-apertures.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/profile-observations.md](profile-observations.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/project-import-recovery.md](project-import-recovery.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/radial-inverse.md](radial-inverse.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/raw-source-fit.md](raw-source-fit.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/reference-sensitivity.md](reference-sensitivity.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/response-calibration.md](response-calibration.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/response-rectangles.md](response-rectangles.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/scientific-model-review.md](scientific-model-review.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/sharp-corner-resolution.md](sharp-corner-resolution.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/signed-stencils.md](signed-stencils.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/split-plans.md](split-plans.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/tapered-caps.md](tapered-caps.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/wall-gradients.md](wall-gradients.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/wall-localization.md](wall-localization.md) | Dated evidence retained; current audit separately scoped |
| [docs/validation/warp-observations.md](warp-observations.md) | Dated evidence retained; current audit separately scoped |
| [docs/wall-gradients.md](../wall-gradients.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/wall-localization.md](../wall-localization.md) | Current workbench guide or navigation; source contract reviewed |
| [docs/warp-observations.md](../warp-observations.md) | Current workbench guide or navigation; source contract reviewed |
| [reference-library/BUILD.md](../../reference-library/BUILD.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/CHANGELOG.md](../../reference-library/CHANGELOG.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/CONTRIBUTING.md](../../reference-library/CONTRIBUTING.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/GITHUB.md](../../reference-library/GITHUB.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/HANDBOOK.md](../../reference-library/HANDBOOK.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/OPENSCAD.md](../../reference-library/OPENSCAD.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/README.md](../../reference-library/README.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/REFERENCES.md](../../reference-library/REFERENCES.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/RESEARCH-NOTES.md](../../reference-library/RESEARCH-NOTES.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/VERIFICATION.md](../../reference-library/VERIFICATION.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/cadkit/README.md](../../reference-library/cadkit/README.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/examples/README.md](../../reference-library/examples/README.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/templates/CAPTURE-CHECKLIST.md](../../reference-library/templates/CAPTURE-CHECKLIST.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/templates/INDEPENDENT-CHECKS.md](../../reference-library/templates/INDEPENDENT-CHECKS.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/templates/PRINT-ACCEPTANCE.md](../../reference-library/templates/PRINT-ACCEPTANCE.md) | Companion guide, worksheet or generated directory; source/record checked |
| [reference-library/templates/PROJECT-BRIEF.md](../../reference-library/templates/PROJECT-BRIEF.md) | Companion guide, worksheet or generated directory; source/record checked |
