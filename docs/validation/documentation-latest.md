# Documentation review through PR #64 — November 12, 2026

This documentation-only pass reviews published PR #64 at
`701aa91af7a0b1c62e5527eed35e0227bdf0e9f3`, tree
`23a72f23a055763d40d3a6753883a63809c998ea`, in the isolated
`codex/documentation-latest` checkout. The primary checkout remains at
`d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`. Use the
[task index](../README.md) for guides and [project status](../project-status.md)
for integrated versus open-review state.

## Changes

- Move setup and the sample workflow forward in the README, keeping detailed
  mathematics and experiments reachable from the documentation index.
- Extend the status snapshot through published PR #64 and record its exact-head
  hosted observations, preserving older observations under their original dates.
- Document the raw-source Python API, coordinate/intensity units, numerical
  budgets and result fields. Explain standardized residuals, candidate ambiguity
  and brightness-design rank separately from edge identifiability.
- Distinguish the processed observations consumed by `PixelNoise.fit_source`
  from source-projected observations in `fit_plane_edge_offset`. Clarify that
  known earlier-warp composition is implemented while camera/estimated-parameter
  calibration remains open.
- Link the current coverage record from the README, index, contribution guide,
  validation overview and status page. Keep dated scientific receipts intact.

The [raw-source experiment](raw-source-fit.md) retains its 1,273-test local
regression and complete positive/adverse numerical controls. Those results are
not rerun or relabelled as checks of this documentation branch. The companion
library remains at Revision 7; this pass creates no library release.

## Verification

All **86 Markdown documents** parse; **1,189 local links**, **73 fragments**
and **138 tables** pass with no errors. The existing companion-library
documentation suite passes **19 tests**:

```bash
.venv/bin/python -m unittest discover -s reference-library/tests/python -p test_docs.py -v
```

All **24 argparse-based commands** in `scripts/` and `studies/verification/`
return successfully with `--help`; their source hashes and outputs are retained.
The nearest-crossing oracle is deliberately excluded because `--help` executes
its checks and writes a sidecar rather than displaying help. `make help` succeeds.
The API example's **11 HTTP endpoints** exactly match the generated `/api/`
OpenAPI operations. Both documented raw-source signatures match the implementation's
argument order, keyword-only parameters and defaults. This is a schema/source
comparison; no HTTP server or synthetic model is started for it.

The Markdown audit uses the library's locked `marked` package to parse every
tracked guide, worksheet, generated catalog and historical record, plus this
new record. It checks local file targets, Markdown heading fragments, referenced
HTML anchors and table column counts. It does not request external catalog URLs
or refresh dated third-party metadata.

The source review compares setup and numerical commands with the root/library
Makefiles and their runners, the documented HTTP endpoint map with the generated
OpenAPI schema, and the raw-source signature/defaults/limits with its implementation.
Independent read-only reviews cover navigation, recovery, exports, privacy,
engineering equations and numerical interpretation. These are documentation
checks, not a fresh full product regression or physical-camera evaluation.

All **371 tracked non-Markdown files** match the baseline bytes, including
executable source, tests, workflows, dependencies, archived experiments and
library HTML/PDF/catalog outputs. The changed Markdown is not a generated-reader
or PDF input, so no library rebuild is needed. Historical validation receipts,
library source inputs, generated Markdown catalogs and templates are unchanged.
Source hashes and command/check receipts are retained in ignored
`.local/verification/`. No server, browser, native application, AI model or printer
is started, and no photograph is uploaded by this review.

## Coverage inventory

Every document below is included in the structural/link audit. The table records
its role; “historical” retains its original revision/counts, and “generated” means
its source and generation contract were reviewed without hand-editing the artifact.
Structural coverage does not assert fresh runtime, external-link or physical
verification of every claim in an older report.

| Document | Role in this review |
| --- | --- |
| [README.md](../../README.md) | Current workbench guide or navigation |
| [data/PRINTER_SOURCES.md](../../data/PRINTER_SOURCES.md) | Historical evidence or source record; retained |
| [design-qa.md](../../design-qa.md) | Historical evidence or source record; retained |
| [docs/README.md](../README.md) | Current workbench guide or navigation |
| [docs/api-examples.md](../api-examples.md) | Current workbench guide or navigation |
| [docs/architecture.md](../architecture.md) | Current workbench guide or navigation |
| [docs/capture-guide.md](../capture-guide.md) | Current workbench guide or navigation |
| [docs/changelog.md](../changelog.md) | Current workbench guide or navigation |
| [docs/contributing.md](../contributing.md) | Current workbench guide or navigation |
| [docs/corner-feasibility.md](../corner-feasibility.md) | Current workbench guide or navigation |
| [docs/developer-tools.md](../developer-tools.md) | Current workbench guide or navigation |
| [docs/development.md](../development.md) | Current workbench guide or navigation |
| [docs/edge-crossings.md](../edge-crossings.md) | Current workbench guide or navigation |
| [docs/engineering-model.md](../engineering-model.md) | Current workbench guide or navigation |
| [docs/exports.md](../exports.md) | Current workbench guide or navigation |
| [docs/material-gradients.md](../material-gradients.md) | Current workbench guide or navigation |
| [docs/ollama-models.md](../ollama-models.md) | Current workbench guide or navigation |
| [docs/ollama.md](../ollama.md) | Current workbench guide or navigation |
| [docs/photo-benchmark.md](../photo-benchmark.md) | Current workbench guide or navigation |
| [docs/pixel-apertures.md](../pixel-apertures.md) | Current workbench guide or navigation |
| [docs/print-planning.md](../print-planning.md) | Current workbench guide or navigation |
| [docs/printer-catalog.md](../printer-catalog.md) | Current workbench guide or navigation |
| [docs/privacy-security.md](../privacy-security.md) | Current workbench guide or navigation |
| [docs/profile-observations.md](../profile-observations.md) | Current workbench guide or navigation |
| [docs/project-status.md](../project-status.md) | Current workbench guide or navigation |
| [docs/raw-source-fit.md](../raw-source-fit.md) | Current workbench guide or navigation |
| [docs/reference-sensitivity.md](../reference-sensitivity.md) | Current workbench guide or navigation |
| [docs/reference-sheet.md](../reference-sheet.md) | Current workbench guide or navigation |
| [docs/research.md](../research.md) | Current workbench guide or navigation |
| [docs/roadmap.md](../roadmap.md) | Current workbench guide or navigation |
| [docs/signed-stencils.md](../signed-stencils.md) | Current workbench guide or navigation |
| [docs/slicers.md](../slicers.md) | Current workbench guide or navigation |
| [docs/troubleshooting.md](../troubleshooting.md) | Current workbench guide or navigation |
| [docs/validation.md](../validation.md) | Current workbench guide or navigation |
| [docs/validation/benchmark-correspondence.md](benchmark-correspondence.md) | Historical evidence or source record; retained |
| [docs/validation/ci-runtime-budget.md](ci-runtime-budget.md) | Historical evidence or source record; retained |
| [docs/validation/contrast-recovery.md](contrast-recovery.md) | Historical evidence or source record; retained |
| [docs/validation/corner-blur-domains.md](corner-blur-domains.md) | Historical evidence or source record; retained |
| [docs/validation/corner-feasibility.md](corner-feasibility.md) | Historical evidence or source record; retained |
| [docs/validation/curved-placement.md](curved-placement.md) | Historical evidence or source record; retained |
| [docs/validation/directional-spread-qualification.md](directional-spread-qualification.md) | Historical evidence or source record; retained |
| [docs/validation/documentation-alignment.md](documentation-alignment.md) | Historical evidence or source record; retained |
| [docs/validation/documentation-complete-2026-11-12.md](documentation-complete-2026-11-12.md) | Historical evidence or source record; retained |
| [docs/validation/documentation-current-state.md](documentation-current-state.md) | Historical evidence or source record; retained |
| [docs/validation/documentation-latest.md](documentation-latest.md) | Current coverage and verification record |
| [docs/validation/documentation-math-state.md](documentation-math-state.md) | Historical evidence or source record; retained |
| [docs/validation/documentation-refresh.md](documentation-refresh.md) | Historical evidence or source record; retained |
| [docs/validation/documentation-review-2026-11-12.md](documentation-review-2026-11-12.md) | Historical evidence or source record; retained |
| [docs/validation/edge-crossings.md](edge-crossings.md) | Historical evidence or source record; retained |
| [docs/validation/engineering-audit.md](engineering-audit.md) | Historical evidence or source record; retained |
| [docs/validation/fillet-sweep.md](fillet-sweep.md) | Historical evidence or source record; retained |
| [docs/validation/fit-support.md](fit-support.md) | Historical evidence or source record; retained |
| [docs/validation/guided-workbench.md](guided-workbench.md) | Historical evidence or source record; retained |
| [docs/validation/material-gradients.md](material-gradients.md) | Historical evidence or source record; retained |
| [docs/validation/pixel-apertures.md](pixel-apertures.md) | Historical evidence or source record; retained |
| [docs/validation/profile-observations.md](profile-observations.md) | Historical evidence or source record; retained |
| [docs/validation/project-import-recovery.md](project-import-recovery.md) | Historical evidence or source record; retained |
| [docs/validation/radial-inverse.md](radial-inverse.md) | Historical evidence or source record; retained |
| [docs/validation/raw-source-fit.md](raw-source-fit.md) | Historical evidence or source record; retained |
| [docs/validation/reference-sensitivity.md](reference-sensitivity.md) | Historical evidence or source record; retained |
| [docs/validation/scientific-model-review.md](scientific-model-review.md) | Historical evidence or source record; retained |
| [docs/validation/sharp-corner-resolution.md](sharp-corner-resolution.md) | Historical evidence or source record; retained |
| [docs/validation/signed-stencils.md](signed-stencils.md) | Historical evidence or source record; retained |
| [docs/validation/split-plans.md](split-plans.md) | Historical evidence or source record; retained |
| [docs/validation/wall-gradients.md](wall-gradients.md) | Historical evidence or source record; retained |
| [docs/validation/wall-localization.md](wall-localization.md) | Historical evidence or source record; retained |
| [docs/validation/warp-observations.md](warp-observations.md) | Historical evidence or source record; retained |
| [docs/wall-gradients.md](../wall-gradients.md) | Current workbench guide or navigation |
| [docs/wall-localization.md](../wall-localization.md) | Current workbench guide or navigation |
| [docs/warp-observations.md](../warp-observations.md) | Current workbench guide or navigation |
| [reference-library/BUILD.md](../../reference-library/BUILD.md) | Companion-library guide; separate revision and build contract retained |
| [reference-library/CHANGELOG.md](../../reference-library/CHANGELOG.md) | Historical evidence or source record; retained |
| [reference-library/CONTRIBUTING.md](../../reference-library/CONTRIBUTING.md) | Companion-library guide; separate revision and build contract retained |
| [reference-library/GITHUB.md](../../reference-library/GITHUB.md) | Generated dated catalog; retained |
| [reference-library/HANDBOOK.md](../../reference-library/HANDBOOK.md) | Companion-library guide; separate revision and build contract retained |
| [reference-library/OPENSCAD.md](../../reference-library/OPENSCAD.md) | Companion-library guide; separate revision and build contract retained |
| [reference-library/README.md](../../reference-library/README.md) | Companion-library guide; separate revision and build contract retained |
| [reference-library/REFERENCES.md](../../reference-library/REFERENCES.md) | Generated dated catalog; retained |
| [reference-library/RESEARCH-NOTES.md](../../reference-library/RESEARCH-NOTES.md) | Companion-library guide; separate revision and build contract retained |
| [reference-library/VERIFICATION.md](../../reference-library/VERIFICATION.md) | Historical evidence or source record; retained |
| [reference-library/cadkit/README.md](../../reference-library/cadkit/README.md) | Companion-library guide; separate revision and build contract retained |
| [reference-library/examples/README.md](../../reference-library/examples/README.md) | Companion-library guide; separate revision and build contract retained |
| [reference-library/templates/CAPTURE-CHECKLIST.md](../../reference-library/templates/CAPTURE-CHECKLIST.md) | Library worksheet and generated-reader input; retained |
| [reference-library/templates/INDEPENDENT-CHECKS.md](../../reference-library/templates/INDEPENDENT-CHECKS.md) | Library worksheet and generated-reader input; retained |
| [reference-library/templates/PRINT-ACCEPTANCE.md](../../reference-library/templates/PRINT-ACCEPTANCE.md) | Library worksheet and generated-reader input; retained |
| [reference-library/templates/PROJECT-BRIEF.md](../../reference-library/templates/PROJECT-BRIEF.md) | Library worksheet and generated-reader input; retained |
