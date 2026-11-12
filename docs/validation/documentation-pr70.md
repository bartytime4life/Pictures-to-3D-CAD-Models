# Documentation review through PR #70 — November 12, 2026

This documentation-only update reviews published
[draft PR #70](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/70)
at `df53bc495a83ebf72c38f0f14a778e153d35b8db`, tree
`cabe975b6f2eb229072182e9a53ba45f6e7dc1cc`. Changes are isolated in
`codex/documentation-pr70-review`; the primary checkout remains at
`d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`. Use the [task index](../README.md)
for guides and [project status](../project-status.md) for the separate integrated,
review and hosted states.

## Changes and scope

- Update the source snapshot through PR #70, including its tapered-cap repair
  and the latest observed exact-head CI results.
- Explain the remaining free-arc representation limitation in capture, export,
  API, engineering and troubleshooting guides. Turning off **Recover design
  intent** still permits fitting and blur correction. Critical radii and joins
  require independent CAD and physical checks; a valid solid is insufficient.
- Distinguish a supported in-plane taper from a cross-section that changes
  through the part's depth. Clarify preview updates and downstream CAD revisions.
- Make build-before-test guidance explicit and align developer/API descriptions
  with the actual sampling and correction stages.
- Review current user and numerical-tool guides, historical records, library
  orientation, worksheets and generated documents. Route current coverage here;
  retain historical dates, counts, source pins and adverse results.

The [critical-arc guide](../exports.md#verify-critical-arc-geometry) gives the
manual verification and recovery path. The [PR #70 validation](tapered-caps.md)
already records the remaining free-arc issue. This update documents that boundary;
it adds no join solver, automatic consistency gate or new experiment result.
The separate developer Gaussian/response models still do not enter production
tracing. No unfinished investigation is promoted into a verified product feature.

## Verification

The checks below are recorded for this documentation tree. The complete
per-file hashes, command outputs and check receipts are retained locally in
ignored `.local/verification/`; they contain no personal photos.

All **95 Markdown documents**, **1,586 local Markdown links**, **119 fragments**
and **156 tables** pass parsing and structural checks with zero errors. The
additional local HTML image link also resolves. The complete inventory follows.
The library's existing documentation-accuracy suite passes **19 tests**.

All **39 argparse-based commands** in `scripts/` and `studies/verification/`
return successfully with `--help`; root `make help` also succeeds. The
**26 documentation-contract checks** pass, including both API tables against
all **11 generated HTTP operations**, raw-source and response signatures,
response-calibration JSON/Python examples, rectangle `some`/`all` and finite-slope
examples, the bounded-CDF Python example and the shared-Gaussian-domain example.
They also check source/input hashes, incompatible/unavailable queries, invalid
numeric inputs and original-output preservation on overwrite refusal.

```bash
.venv/bin/python -m unittest discover -s reference-library/tests/python -p test_docs.py -v
make help
```

The structure/contract harnesses are local verification tools, not new committed
product commands. The individual executable examples remain in their linked
[response](../response-calibration.md#run-an-exact-example),
[rectangle](../response-rectangles.md#run-a-small-exact-example) and
[Gaussian-domain](../gaussian-response-domains.md#run-a-declared-example) guides.

Existing command help is checked without a server or model inference. The
nearest-crossing oracle is excluded from the help census because its `--help`
argument runs checks and writes a sidecar. API tables are compared with generated
OpenAPI without starting an HTTP listener. Declared response examples execute
to fresh local paths, including their refusal to overwrite an existing report.
These checks do not run a full image-processing study or native slicer session.

All **422 tracked non-Markdown files** match PR #70 before and after these
checks. Executable source, tests, dependencies, workflows, archived studies,
images and generated library HTML/PDF/catalog files are unchanged. Library
guides and templates remain accurate at Revision 7; their dated release record
is preserved. No generated-reader inputs changed, so this update creates no
library rebuild or release.

The earlier **1,556 Python tests and 74 browser scenarios** remain PR #70's
source-bound regression result. This documentation pass does not claim a fresh
full software/browser run, new visual/accessibility acceptance, installed-tool
qualification, real-photo calibration or physical fit. Hosted CI is reported
separately in [project status](../project-status.md#evidence-by-scope).

## Coverage inventory

Every document below is included in the structural and local-navigation check.
Current guides are reviewed against relevant source contracts; historical and
generated records retain their original scope. Unchanged documentation remains
in the inventory because review does not require a cosmetic edit. External
catalog URLs, upstream product metadata and historical software/physical claims
are not represented as freshly revalidated by this pass.

| Document | Review role |
| --- | --- |
| [README.md](../../README.md) | Current workbench guide or navigation; source reviewed |
| [data/PRINTER_SOURCES.md](../../data/PRINTER_SOURCES.md) | Historical evidence or dated source record; retained |
| [design-qa.md](../../design-qa.md) | Historical evidence or dated source record; retained |
| [docs/README.md](../README.md) | Current workbench guide or navigation; source reviewed |
| [docs/api-examples.md](../api-examples.md) | Current workbench guide or navigation; source reviewed |
| [docs/architecture.md](../architecture.md) | Current workbench guide or navigation; source reviewed |
| [docs/capture-guide.md](../capture-guide.md) | Current workbench guide or navigation; source reviewed |
| [docs/changelog.md](../changelog.md) | Current workbench guide or navigation; source reviewed |
| [docs/contributing.md](../contributing.md) | Current workbench guide or navigation; source reviewed |
| [docs/corner-feasibility.md](../corner-feasibility.md) | Current workbench guide or navigation; source reviewed |
| [docs/developer-tools.md](../developer-tools.md) | Current workbench guide or navigation; source reviewed |
| [docs/development.md](../development.md) | Current workbench guide or navigation; source reviewed |
| [docs/edge-crossings.md](../edge-crossings.md) | Current workbench guide or navigation; source reviewed |
| [docs/engineering-model.md](../engineering-model.md) | Current workbench guide or navigation; source reviewed |
| [docs/exports.md](../exports.md) | Current workbench guide or navigation; source reviewed |
| [docs/gaussian-response-domains.md](../gaussian-response-domains.md) | Current workbench guide or navigation; source reviewed |
| [docs/material-gradients.md](../material-gradients.md) | Current workbench guide or navigation; source reviewed |
| [docs/ollama-models.md](../ollama-models.md) | Current workbench guide or navigation; source reviewed |
| [docs/ollama.md](../ollama.md) | Current workbench guide or navigation; source reviewed |
| [docs/photo-benchmark.md](../photo-benchmark.md) | Current workbench guide or navigation; source reviewed |
| [docs/pixel-apertures.md](../pixel-apertures.md) | Current workbench guide or navigation; source reviewed |
| [docs/print-planning.md](../print-planning.md) | Current workbench guide or navigation; source reviewed |
| [docs/printer-catalog.md](../printer-catalog.md) | Current workbench guide or navigation; source reviewed |
| [docs/privacy-security.md](../privacy-security.md) | Current workbench guide or navigation; source reviewed |
| [docs/profile-observations.md](../profile-observations.md) | Current workbench guide or navigation; source reviewed |
| [docs/project-status.md](../project-status.md) | Current workbench guide or navigation; source reviewed |
| [docs/raw-source-fit.md](../raw-source-fit.md) | Current workbench guide or navigation; source reviewed |
| [docs/reference-sensitivity.md](../reference-sensitivity.md) | Current workbench guide or navigation; source reviewed |
| [docs/reference-sheet.md](../reference-sheet.md) | Current workbench guide or navigation; source reviewed |
| [docs/research.md](../research.md) | Current workbench guide or navigation; source reviewed |
| [docs/response-calibration.md](../response-calibration.md) | Current workbench guide or navigation; source reviewed |
| [docs/response-rectangles.md](../response-rectangles.md) | Current workbench guide or navigation; source reviewed |
| [docs/roadmap.md](../roadmap.md) | Current workbench guide or navigation; source reviewed |
| [docs/signed-stencils.md](../signed-stencils.md) | Current workbench guide or navigation; source reviewed |
| [docs/slicers.md](../slicers.md) | Current workbench guide or navigation; source reviewed |
| [docs/troubleshooting.md](../troubleshooting.md) | Current workbench guide or navigation; source reviewed |
| [docs/validation.md](../validation.md) | Current workbench guide or navigation; source reviewed |
| [docs/validation/benchmark-correspondence.md](benchmark-correspondence.md) | Historical evidence or dated source record; retained |
| [docs/validation/ci-runtime-budget.md](ci-runtime-budget.md) | Historical evidence or dated source record; retained |
| [docs/validation/contrast-recovery.md](contrast-recovery.md) | Historical evidence or dated source record; retained |
| [docs/validation/corner-blur-domains.md](corner-blur-domains.md) | Historical evidence or dated source record; retained |
| [docs/validation/corner-feasibility.md](corner-feasibility.md) | Historical evidence or dated source record; retained |
| [docs/validation/curved-placement.md](curved-placement.md) | Historical evidence or dated source record; retained |
| [docs/validation/directional-spread-qualification.md](directional-spread-qualification.md) | Historical evidence or dated source record; retained |
| [docs/validation/documentation-alignment.md](documentation-alignment.md) | Historical evidence or dated source record; retained |
| [docs/validation/documentation-complete-2026-11-12.md](documentation-complete-2026-11-12.md) | Historical evidence or dated source record; retained |
| [docs/validation/documentation-current-state.md](documentation-current-state.md) | Historical evidence or dated source record; retained |
| [docs/validation/documentation-latest.md](documentation-latest.md) | Historical evidence or dated source record; retained |
| [docs/validation/documentation-math-state.md](documentation-math-state.md) | Historical evidence or dated source record; retained |
| [docs/validation/documentation-pr70.md](documentation-pr70.md) | Current documentation coverage and verification |
| [docs/validation/documentation-refresh.md](documentation-refresh.md) | Historical evidence or dated source record; retained |
| [docs/validation/documentation-response-state.md](documentation-response-state.md) | Historical evidence or dated source record; retained |
| [docs/validation/documentation-review-2026-11-12.md](documentation-review-2026-11-12.md) | Historical evidence or dated source record; retained |
| [docs/validation/edge-crossings.md](edge-crossings.md) | Historical evidence or dated source record; retained |
| [docs/validation/engineering-audit.md](engineering-audit.md) | Historical evidence or dated source record; retained |
| [docs/validation/fillet-sweep.md](fillet-sweep.md) | Historical evidence or dated source record; retained |
| [docs/validation/fit-support.md](fit-support.md) | Historical evidence or dated source record; retained |
| [docs/validation/gaussian-response-domains.md](gaussian-response-domains.md) | Historical evidence or dated source record; retained |
| [docs/validation/guided-workbench.md](guided-workbench.md) | Historical evidence or dated source record; retained |
| [docs/validation/material-gradients.md](material-gradients.md) | Historical evidence or dated source record; retained |
| [docs/validation/pixel-apertures.md](pixel-apertures.md) | Historical evidence or dated source record; retained |
| [docs/validation/profile-observations.md](profile-observations.md) | Historical evidence or dated source record; retained |
| [docs/validation/project-import-recovery.md](project-import-recovery.md) | Historical evidence or dated source record; retained |
| [docs/validation/radial-inverse.md](radial-inverse.md) | Historical evidence or dated source record; retained |
| [docs/validation/raw-source-fit.md](raw-source-fit.md) | Historical evidence or dated source record; retained |
| [docs/validation/reference-sensitivity.md](reference-sensitivity.md) | Historical evidence or dated source record; retained |
| [docs/validation/response-calibration.md](response-calibration.md) | Historical evidence or dated source record; retained |
| [docs/validation/response-rectangles.md](response-rectangles.md) | Historical evidence or dated source record; retained |
| [docs/validation/scientific-model-review.md](scientific-model-review.md) | Historical evidence or dated source record; retained |
| [docs/validation/sharp-corner-resolution.md](sharp-corner-resolution.md) | Historical evidence or dated source record; retained |
| [docs/validation/signed-stencils.md](signed-stencils.md) | Historical evidence or dated source record; retained |
| [docs/validation/split-plans.md](split-plans.md) | Historical evidence or dated source record; retained |
| [docs/validation/tapered-caps.md](tapered-caps.md) | Historical evidence or dated source record; retained |
| [docs/validation/wall-gradients.md](wall-gradients.md) | Historical evidence or dated source record; retained |
| [docs/validation/wall-localization.md](wall-localization.md) | Historical evidence or dated source record; retained |
| [docs/validation/warp-observations.md](warp-observations.md) | Historical evidence or dated source record; retained |
| [docs/wall-gradients.md](../wall-gradients.md) | Current workbench guide or navigation; source reviewed |
| [docs/wall-localization.md](../wall-localization.md) | Current workbench guide or navigation; source reviewed |
| [docs/warp-observations.md](../warp-observations.md) | Current workbench guide or navigation; source reviewed |
| [reference-library/BUILD.md](../../reference-library/BUILD.md) | Companion-library guide or release record; reviewed |
| [reference-library/CHANGELOG.md](../../reference-library/CHANGELOG.md) | Companion-library guide or release record; reviewed |
| [reference-library/CONTRIBUTING.md](../../reference-library/CONTRIBUTING.md) | Companion-library guide or release record; reviewed |
| [reference-library/GITHUB.md](../../reference-library/GITHUB.md) | Generated source directory; retained |
| [reference-library/HANDBOOK.md](../../reference-library/HANDBOOK.md) | Companion-library guide or release record; reviewed |
| [reference-library/OPENSCAD.md](../../reference-library/OPENSCAD.md) | Companion-library guide or release record; reviewed |
| [reference-library/README.md](../../reference-library/README.md) | Companion-library guide or release record; reviewed |
| [reference-library/REFERENCES.md](../../reference-library/REFERENCES.md) | Generated source directory; retained |
| [reference-library/RESEARCH-NOTES.md](../../reference-library/RESEARCH-NOTES.md) | Companion-library guide or release record; reviewed |
| [reference-library/VERIFICATION.md](../../reference-library/VERIFICATION.md) | Companion-library guide or release record; reviewed |
| [reference-library/cadkit/README.md](../../reference-library/cadkit/README.md) | Companion-library guide or release record; reviewed |
| [reference-library/examples/README.md](../../reference-library/examples/README.md) | Companion-library guide or release record; reviewed |
| [reference-library/templates/CAPTURE-CHECKLIST.md](../../reference-library/templates/CAPTURE-CHECKLIST.md) | Independent measurement or acceptance worksheet; reviewed |
| [reference-library/templates/INDEPENDENT-CHECKS.md](../../reference-library/templates/INDEPENDENT-CHECKS.md) | Independent measurement or acceptance worksheet; reviewed |
| [reference-library/templates/PRINT-ACCEPTANCE.md](../../reference-library/templates/PRINT-ACCEPTANCE.md) | Independent measurement or acceptance worksheet; reviewed |
| [reference-library/templates/PROJECT-BRIEF.md](../../reference-library/templates/PROJECT-BRIEF.md) | Independent measurement or acceptance worksheet; reviewed |
