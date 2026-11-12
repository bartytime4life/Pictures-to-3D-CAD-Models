# Complete documentation update — November 12, 2026

This review starts from published source
`7dfe0fe698c8831e9c02ae960f03bcdc533701dc`,
[draft PR #57](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/57),
in the isolated `codex/documentation-complete-20261112` worktree. The primary
checkout and unfinished `codex/wall-localization` experiment are preserved.
The latter's proposed behavior is outside this documentation baseline.

## Corrections

- The [status page](../project-status.md) identifies published PR #57, its full
  ancestor review chain, the integrated `main` and separately observed hosted CI.
  An open review branch is not described as installed or deployed.
- The [developer-tool catalog](../developer-tools.md) connects corner input
  versions 1–4, sampling studies, full-CSV audits, numerical oracles, optional
  figures, measured-photo comparisons, native imports and local AI evaluation.
  Each route identifies its inputs, outputs and interpretation limits.
- The [wall method](../reference-sheet.md#5-camera-pose-and-thickness-parallax)
  now describes heuristic selection rather than guaranteed tone identification.
  It discloses the published offset window and fixed supplied width. The rounded
  0.2 σ scenario estimate is not treated as a general physical error cap.
- Capture, engineering, troubleshooting and benchmark guidance carry those
  limits into the practical workflow. Benchmark coverage distinguishes compared,
  unmatched and unavailable dimensions; wall correction is model-dependent.
- Sharp-corner recovery and channel-mix invariance state their assumptions.
  Short unsupported features can retain a polyline rather than invariably
  becoming a large-radius arc. Implemented conditional radius sets are separated
  from future broader model-discrepancy and nuisance-domain work.
- Photo and Ollama benchmark reports can replace existing files, including a
  saved unavailable-service preflight. Their guides now recommend fresh paths.
  PDF timestamp invariance is distinguished from matching fonts, rendering
  dependencies and environment for byte-identical reproduction.

## Completed verification

All **75 Markdown documents** parse with the library's locked `marked` dependency.
The local audit checks **863 relative links**, **61 heading fragments** and
**127 tables**, with no errors. These checks include the coverage inventory below.
Its machine-readable receipt and each
document's SHA-256 are retained in `.local/verification/`.

The existing companion documentation suite passed **19 tests**. It checks
catalog/revision counts, worked calculations, figure references, CLI coverage,
local links and the dated PDF/verification record. Run it from the repository
root after preparing a root Python environment:

```bash
.venv/bin/python -m unittest discover -s reference-library/tests/python -p test_docs.py -v
```

The complete archived wall-study CSV audit also passed: **840 direct rows**,
**576 image rows**, unique complete Cartesian keys, **36 image-summary groups**
and **six witness-summary groups**, with no execution failures. This recomputes
accounting on the retained artifacts; it does not rerun the study or refresh its
recorded runtime/source state. The [wall validation record](wall-gradients.md)
retains the original hashes and scientific interpretation.

Ten argparse-based analysis/study/plot commands were checked with `--help`.
The nearest-crossing oracle has no argument parser; its invocation executed
**3,888 finite-data cases** successfully. Its generated sidecar is preserved in
ignored verification storage, and the guide's fresh-copy command was also checked.
This is a numerical predicate check,
not a camera or physical-feature evaluation. Setup, Makefile, API/error schemas,
UI labels, AI context and explicit Apply/Undo behavior were reviewed against
the exact baseline source. No live model inference or native application was
started for this documentation task.

Only Markdown changes are included. Executable source, dependencies, workflows,
archived study data and generated library outputs match the baseline. The
library build graph does not use the edited `BUILD.md` as generated-reader or
PDF text, so no generated release artifact needs regeneration for this change.
Historical regression counts are retained in their dated reports; they are not
new Python/browser/build runs on this documentation branch.

## Coverage inventory

Every document below is included in the structural checks. Current guides were
reviewed against the relevant source and cross-linked where needed. Dated
validation and release records retain their original claims, failures and counts.
Generated catalogs and wider library reference material retain their original
catalog metadata; this review does not claim a new literature search, source-URL
availability check or library release.

### Current workbench and developer guides

| Document | Treatment |
| --- | --- |
| [README.md](../../README.md) | Current guide/source contract reviewed |
| [data/PRINTER_SOURCES.md](../../data/PRINTER_SOURCES.md) | Dated evidence retained; links checked |
| [design-qa.md](../../design-qa.md) | Dated evidence retained; links checked |
| [docs/README.md](../README.md) | Current guide/source contract reviewed |
| [docs/api-examples.md](../api-examples.md) | Current guide/source contract reviewed |
| [docs/architecture.md](../architecture.md) | Current guide/source contract reviewed |
| [docs/capture-guide.md](../capture-guide.md) | Current guide/source contract reviewed |
| [docs/changelog.md](../changelog.md) | Current guide/source contract reviewed |
| [docs/contributing.md](../contributing.md) | Current guide/source contract reviewed |
| [docs/corner-feasibility.md](../corner-feasibility.md) | Current guide/source contract reviewed |
| [docs/developer-tools.md](../developer-tools.md) | Current guide/source contract reviewed |
| [docs/development.md](../development.md) | Current guide/source contract reviewed |
| [docs/edge-crossings.md](../edge-crossings.md) | Current guide/source contract reviewed |
| [docs/engineering-model.md](../engineering-model.md) | Current guide/source contract reviewed |
| [docs/exports.md](../exports.md) | Current guide/source contract reviewed |
| [docs/material-gradients.md](../material-gradients.md) | Current guide/source contract reviewed |
| [docs/ollama-models.md](../ollama-models.md) | Current guide/source contract reviewed |
| [docs/ollama.md](../ollama.md) | Current guide/source contract reviewed |
| [docs/photo-benchmark.md](../photo-benchmark.md) | Current guide/source contract reviewed |
| [docs/pixel-apertures.md](../pixel-apertures.md) | Current guide/source contract reviewed |
| [docs/print-planning.md](../print-planning.md) | Current guide/source contract reviewed |
| [docs/printer-catalog.md](../printer-catalog.md) | Current guide/source contract reviewed |
| [docs/privacy-security.md](../privacy-security.md) | Current guide/source contract reviewed |
| [docs/project-status.md](../project-status.md) | Current guide/source contract reviewed |
| [docs/reference-sensitivity.md](../reference-sensitivity.md) | Current guide/source contract reviewed |
| [docs/reference-sheet.md](../reference-sheet.md) | Current guide/source contract reviewed |
| [docs/research.md](../research.md) | Current guide/source contract reviewed |
| [docs/roadmap.md](../roadmap.md) | Current guide/source contract reviewed |
| [docs/signed-stencils.md](../signed-stencils.md) | Current guide/source contract reviewed |
| [docs/slicers.md](../slicers.md) | Current guide/source contract reviewed |
| [docs/troubleshooting.md](../troubleshooting.md) | Current guide/source contract reviewed |
| [docs/validation.md](../validation.md) | Current guide/source contract reviewed |
| [docs/wall-gradients.md](../wall-gradients.md) | Current guide/source contract reviewed |

### Source-bound validation records

| Document | Treatment |
| --- | --- |
| [docs/validation/benchmark-correspondence.md](benchmark-correspondence.md) | Dated evidence retained; links checked |
| [docs/validation/contrast-recovery.md](contrast-recovery.md) | Dated evidence retained; links checked |
| [docs/validation/corner-blur-domains.md](corner-blur-domains.md) | Dated evidence retained; links checked |
| [docs/validation/corner-feasibility.md](corner-feasibility.md) | Dated evidence retained; links checked |
| [docs/validation/curved-placement.md](curved-placement.md) | Dated evidence retained; links checked |
| [docs/validation/directional-spread-qualification.md](directional-spread-qualification.md) | Dated evidence retained; links checked |
| [docs/validation/documentation-complete-2026-11-12.md](documentation-complete-2026-11-12.md) | Current review and complete inventory |
| [docs/validation/documentation-current-state.md](documentation-current-state.md) | Dated evidence retained; links checked |
| [docs/validation/documentation-math-state.md](documentation-math-state.md) | Dated evidence retained; links checked |
| [docs/validation/documentation-refresh.md](documentation-refresh.md) | Dated evidence retained; links checked |
| [docs/validation/documentation-review-2026-11-12.md](documentation-review-2026-11-12.md) | Dated evidence retained; links checked |
| [docs/validation/edge-crossings.md](edge-crossings.md) | Dated evidence retained; links checked |
| [docs/validation/engineering-audit.md](engineering-audit.md) | Dated evidence retained; links checked |
| [docs/validation/fillet-sweep.md](fillet-sweep.md) | Dated evidence retained; links checked |
| [docs/validation/fit-support.md](fit-support.md) | Dated evidence retained; links checked |
| [docs/validation/guided-workbench.md](guided-workbench.md) | Dated evidence retained; links checked |
| [docs/validation/material-gradients.md](material-gradients.md) | Dated evidence retained; links checked |
| [docs/validation/pixel-apertures.md](pixel-apertures.md) | Dated evidence retained; links checked |
| [docs/validation/project-import-recovery.md](project-import-recovery.md) | Dated evidence retained; links checked |
| [docs/validation/radial-inverse.md](radial-inverse.md) | Dated evidence retained; links checked |
| [docs/validation/reference-sensitivity.md](reference-sensitivity.md) | Dated evidence retained; links checked |
| [docs/validation/scientific-model-review.md](scientific-model-review.md) | Dated evidence retained; links checked |
| [docs/validation/sharp-corner-resolution.md](sharp-corner-resolution.md) | Dated evidence retained; links checked |
| [docs/validation/signed-stencils.md](signed-stencils.md) | Dated evidence retained; links checked |
| [docs/validation/split-plans.md](split-plans.md) | Dated evidence retained; links checked |
| [docs/validation/wall-gradients.md](wall-gradients.md) | Dated evidence retained; links checked |

### Companion library guides and worksheets

| Document | Treatment |
| --- | --- |
| [reference-library/BUILD.md](../../reference-library/BUILD.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/CHANGELOG.md](../../reference-library/CHANGELOG.md) | Dated evidence retained; links checked |
| [reference-library/CONTRIBUTING.md](../../reference-library/CONTRIBUTING.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/HANDBOOK.md](../../reference-library/HANDBOOK.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/OPENSCAD.md](../../reference-library/OPENSCAD.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/README.md](../../reference-library/README.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/RESEARCH-NOTES.md](../../reference-library/RESEARCH-NOTES.md) | Dated evidence retained; links checked |
| [reference-library/VERIFICATION.md](../../reference-library/VERIFICATION.md) | Dated evidence retained; links checked |
| [reference-library/cadkit/README.md](../../reference-library/cadkit/README.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/examples/README.md](../../reference-library/examples/README.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/templates/CAPTURE-CHECKLIST.md](../../reference-library/templates/CAPTURE-CHECKLIST.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/templates/INDEPENDENT-CHECKS.md](../../reference-library/templates/INDEPENDENT-CHECKS.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/templates/PRINT-ACCEPTANCE.md](../../reference-library/templates/PRINT-ACCEPTANCE.md) | Guide or worksheet reviewed; library release remains separate |
| [reference-library/templates/PROJECT-BRIEF.md](../../reference-library/templates/PROJECT-BRIEF.md) | Guide or worksheet reviewed; library release remains separate |

### Generated library catalogs

| Document | Treatment |
| --- | --- |
| [reference-library/GITHUB.md](../../reference-library/GITHUB.md) | Generated snapshot retained; links checked |
| [reference-library/REFERENCES.md](../../reference-library/REFERENCES.md) | Generated snapshot retained; links checked |

## Interpretation and remaining work

Documentation checks do not establish a new installed version, production
deployment, native slicer acceptance, real-photo accuracy, physical fit,
structural performance or live-model answer quality. The [roadmap](../roadmap.md)
retains those engineering tasks. Continue with [reserved measurements](../engineering-model.md)
and the appropriate source-bound validation before relying on a manufactured part.
