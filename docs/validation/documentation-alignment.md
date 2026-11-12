# Documentation alignment — November 12, 2026

This documentation-only review starts from published PR #62 at
`ca321442bd276c177c31f00bcd62fb0ea27b2e0e` in the isolated
`codex/documentation-alignment` worktree. It includes the wall-localization code,
fixed-observation/covariance tools, known warp-chain extension and 45-minute
hosted job budget. The primary checkout and earlier research are preserved.

Use [project status](../project-status.md) for integrated versus review-branch
state, [the task index](../README.md) for usage, and
[the developer catalog](../developer-tools.md) for numerical commands. Earlier
documentation reports remain dated evidence rather than current status pages.

## Corrections and scope

- Extend the source/review chain through PRs #61 and #62 and record terminal
  PR #60 CI separately from still-running heads. The health version cannot
  identify a checkout; record its Git revision before testing a service.
- Complete the development command table for profile noise, finite postblur
  and raw-image warp composition. Preserve fresh-output requirements, source
  pins, runtime assumptions and developer-only scope.
- Correct benchmark wording: errors are conditional on compared dimensions;
  unmatched and unavailable dimensions remain in coverage totals.
- Describe the current wall notes and unchanged unresolved points. Preserve
  the older 0.2 × blur scenario estimate as historical, not an error guarantee.
- Restore the measurement path's Gaussian smoothing and explain that the
  saved-value rectification affects segmentation and channel selection. Fitted
  illumination surfaces reduce lighting effects under their assumptions;
  arbitrary gradients and shadows are not guaranteed harmless.
- Specify the unit normal in the affine optical-spread equation. Explain why
  small retained covariance modes can amplify deterministic rounding and model
  discrepancy even when a residual passes the retained-range check.
- Direct earlier documentation reviews to this current inventory while keeping
  their original revisions, counts, failures and environments intact.

The [warp-chain record](warp-observations.md) retains the source-bound 1,249-test
local regression, 324 readouts from six reused arrays and separate optical
controls. The [fixed-observation record](profile-observations.md) retains its
1,225-test local regression and supplied-noise controls. These are prior results,
not new regression runs on this documentation branch. Unpublished raw-source
fitting prototypes remain outside this baseline and are not product features.

## Verification

All **83 Markdown documents** parse with the library's locked `marked`
dependency. The audit checks **1,071 local links**, **65 heading fragments** and
**133 tables**, with no errors. The inventory includes this record.

The existing companion-library documentation suite passed **19 tests**:

```bash
.venv/bin/python -m unittest discover -s reference-library/tests/python -p test_docs.py -v
```

Fifteen argparse-based numerical, benchmark, audit and figure commands returned
successfully with `--help`. The nearest-contact oracle was not invoked with that
flag because it executes its numerical checks instead of displaying help.
`make help` and the documented root targets agree. API/UI recovery, export,
slicer, assistant and privacy wording were compared with their implementations;
no live service, browser, native application or AI model was started.

A byte comparison against PR #62 confirms **363 tracked non-Markdown files**
are unchanged. This includes the complete executable/test sources, workflows,
archived study data and generated library artifacts. Documentation and command
receipts, source hashes and independent review notes are retained in ignored
`.local/verification/`. `git diff --check` passed.

These checks do not rerun the full Python/browser/build suites. The review does
not refresh external catalog metadata or claim external-URL availability, a new
literature search, a generated library release, native-tool acceptance or physical qualification.

Only Markdown is changed. Generated HTML, PDF, catalogs, figures, worksheets in
CSV, study data, executable source, tests, dependencies and workflows retain
their baseline bytes. None of the edited Markdown is a generated-reader/PDF
input, so a library rebuild is unnecessary. No model or photograph is uploaded.

## Coverage inventory

Every Markdown document below is included in the structural/link audit. Current
contracts were checked against their relevant setup scripts, Makefiles, CLI
parsers, API/backend and interface source. Dated validation reports retain their
original meaning. The library handbook and templates remain their own revision-7
reference material; source catalogs and generated artifacts retain their dated
snapshot. Inclusion here does not imply a new scientific experiment per guide.

### Current workbench and developer guides

| Document | Treatment |
| --- | --- |
| [README.md](../../README.md) | Current guide; relevant source contract and links reviewed |
| [docs/README.md](../README.md) | Current guide; relevant source contract and links reviewed |
| [docs/api-examples.md](../api-examples.md) | Current guide; relevant source contract and links reviewed |
| [docs/architecture.md](../architecture.md) | Current guide; relevant source contract and links reviewed |
| [docs/capture-guide.md](../capture-guide.md) | Current guide; relevant source contract and links reviewed |
| [docs/changelog.md](../changelog.md) | Current guide; relevant source contract and links reviewed |
| [docs/contributing.md](../contributing.md) | Current guide; relevant source contract and links reviewed |
| [docs/corner-feasibility.md](../corner-feasibility.md) | Current guide; relevant source contract and links reviewed |
| [docs/developer-tools.md](../developer-tools.md) | Current guide; relevant source contract and links reviewed |
| [docs/development.md](../development.md) | Current guide; relevant source contract and links reviewed |
| [docs/edge-crossings.md](../edge-crossings.md) | Current guide; relevant source contract and links reviewed |
| [docs/engineering-model.md](../engineering-model.md) | Current guide; relevant source contract and links reviewed |
| [docs/exports.md](../exports.md) | Current guide; relevant source contract and links reviewed |
| [docs/material-gradients.md](../material-gradients.md) | Current guide; relevant source contract and links reviewed |
| [docs/ollama-models.md](../ollama-models.md) | Current guide; relevant source contract and links reviewed |
| [docs/ollama.md](../ollama.md) | Current guide; relevant source contract and links reviewed |
| [docs/photo-benchmark.md](../photo-benchmark.md) | Current guide; relevant source contract and links reviewed |
| [docs/pixel-apertures.md](../pixel-apertures.md) | Current guide; relevant source contract and links reviewed |
| [docs/print-planning.md](../print-planning.md) | Current guide; relevant source contract and links reviewed |
| [docs/printer-catalog.md](../printer-catalog.md) | Current guide; relevant source contract and links reviewed |
| [docs/privacy-security.md](../privacy-security.md) | Current guide; relevant source contract and links reviewed |
| [docs/profile-observations.md](../profile-observations.md) | Current guide; relevant source contract and links reviewed |
| [docs/project-status.md](../project-status.md) | Current guide; relevant source contract and links reviewed |
| [docs/reference-sensitivity.md](../reference-sensitivity.md) | Current guide; relevant source contract and links reviewed |
| [docs/reference-sheet.md](../reference-sheet.md) | Current guide; relevant source contract and links reviewed |
| [docs/research.md](../research.md) | Current guide; relevant source contract and links reviewed |
| [docs/roadmap.md](../roadmap.md) | Current guide; relevant source contract and links reviewed |
| [docs/signed-stencils.md](../signed-stencils.md) | Current guide; relevant source contract and links reviewed |
| [docs/slicers.md](../slicers.md) | Current guide; relevant source contract and links reviewed |
| [docs/troubleshooting.md](../troubleshooting.md) | Current guide; relevant source contract and links reviewed |
| [docs/validation.md](../validation.md) | Current guide; relevant source contract and links reviewed |
| [docs/wall-gradients.md](../wall-gradients.md) | Current guide; relevant source contract and links reviewed |
| [docs/wall-localization.md](../wall-localization.md) | Current guide; relevant source contract and links reviewed |
| [docs/warp-observations.md](../warp-observations.md) | Current guide; relevant source contract and links reviewed |

### Dated validation and source records

| Document | Treatment |
| --- | --- |
| [data/PRINTER_SOURCES.md](../../data/PRINTER_SOURCES.md) | Dated evidence retained; structure and links checked |
| [design-qa.md](../../design-qa.md) | Dated evidence retained; structure and links checked |
| [docs/validation/benchmark-correspondence.md](benchmark-correspondence.md) | Dated evidence retained; structure and links checked |
| [docs/validation/ci-runtime-budget.md](ci-runtime-budget.md) | Dated evidence retained; structure and links checked |
| [docs/validation/contrast-recovery.md](contrast-recovery.md) | Dated evidence retained; structure and links checked |
| [docs/validation/corner-blur-domains.md](corner-blur-domains.md) | Dated evidence retained; structure and links checked |
| [docs/validation/corner-feasibility.md](corner-feasibility.md) | Dated evidence retained; structure and links checked |
| [docs/validation/curved-placement.md](curved-placement.md) | Dated evidence retained; structure and links checked |
| [docs/validation/directional-spread-qualification.md](directional-spread-qualification.md) | Dated evidence retained; structure and links checked |
| [docs/validation/documentation-alignment.md](documentation-alignment.md) | Current coverage and verification record |
| [docs/validation/documentation-complete-2026-11-12.md](documentation-complete-2026-11-12.md) | Dated evidence retained; structure and links checked |
| [docs/validation/documentation-current-state.md](documentation-current-state.md) | Dated evidence retained; structure and links checked |
| [docs/validation/documentation-math-state.md](documentation-math-state.md) | Dated evidence retained; structure and links checked |
| [docs/validation/documentation-refresh.md](documentation-refresh.md) | Dated evidence retained; structure and links checked |
| [docs/validation/documentation-review-2026-11-12.md](documentation-review-2026-11-12.md) | Dated evidence retained; structure and links checked |
| [docs/validation/edge-crossings.md](edge-crossings.md) | Dated evidence retained; structure and links checked |
| [docs/validation/engineering-audit.md](engineering-audit.md) | Dated evidence retained; structure and links checked |
| [docs/validation/fillet-sweep.md](fillet-sweep.md) | Dated evidence retained; structure and links checked |
| [docs/validation/fit-support.md](fit-support.md) | Dated evidence retained; structure and links checked |
| [docs/validation/guided-workbench.md](guided-workbench.md) | Dated evidence retained; structure and links checked |
| [docs/validation/material-gradients.md](material-gradients.md) | Dated evidence retained; structure and links checked |
| [docs/validation/pixel-apertures.md](pixel-apertures.md) | Dated evidence retained; structure and links checked |
| [docs/validation/profile-observations.md](profile-observations.md) | Dated evidence retained; structure and links checked |
| [docs/validation/project-import-recovery.md](project-import-recovery.md) | Dated evidence retained; structure and links checked |
| [docs/validation/radial-inverse.md](radial-inverse.md) | Dated evidence retained; structure and links checked |
| [docs/validation/reference-sensitivity.md](reference-sensitivity.md) | Dated evidence retained; structure and links checked |
| [docs/validation/scientific-model-review.md](scientific-model-review.md) | Dated evidence retained; structure and links checked |
| [docs/validation/sharp-corner-resolution.md](sharp-corner-resolution.md) | Dated evidence retained; structure and links checked |
| [docs/validation/signed-stencils.md](signed-stencils.md) | Dated evidence retained; structure and links checked |
| [docs/validation/split-plans.md](split-plans.md) | Dated evidence retained; structure and links checked |
| [docs/validation/wall-gradients.md](wall-gradients.md) | Dated evidence retained; structure and links checked |
| [docs/validation/wall-localization.md](wall-localization.md) | Dated evidence retained; structure and links checked |
| [docs/validation/warp-observations.md](warp-observations.md) | Dated evidence retained; structure and links checked |

### Companion library and worksheets

| Document | Treatment |
| --- | --- |
| [reference-library/BUILD.md](../../reference-library/BUILD.md) | Separate library contract/revision retained; documentation suite checked |
| [reference-library/CHANGELOG.md](../../reference-library/CHANGELOG.md) | Dated evidence retained; structure and links checked |
| [reference-library/CONTRIBUTING.md](../../reference-library/CONTRIBUTING.md) | Separate library contract/revision retained; documentation suite checked |
| [reference-library/GITHUB.md](../../reference-library/GITHUB.md) | Generated dated catalog; structure and links checked |
| [reference-library/HANDBOOK.md](../../reference-library/HANDBOOK.md) | Separate library contract/revision retained; documentation suite checked |
| [reference-library/OPENSCAD.md](../../reference-library/OPENSCAD.md) | Separate library contract/revision retained; documentation suite checked |
| [reference-library/README.md](../../reference-library/README.md) | Separate library contract/revision retained; documentation suite checked |
| [reference-library/REFERENCES.md](../../reference-library/REFERENCES.md) | Generated dated catalog; structure and links checked |
| [reference-library/RESEARCH-NOTES.md](../../reference-library/RESEARCH-NOTES.md) | Separate library contract/revision retained; documentation suite checked |
| [reference-library/VERIFICATION.md](../../reference-library/VERIFICATION.md) | Dated evidence retained; structure and links checked |
| [reference-library/cadkit/README.md](../../reference-library/cadkit/README.md) | Separate library contract/revision retained; documentation suite checked |
| [reference-library/examples/README.md](../../reference-library/examples/README.md) | Separate library contract/revision retained; documentation suite checked |
| [reference-library/templates/CAPTURE-CHECKLIST.md](../../reference-library/templates/CAPTURE-CHECKLIST.md) | Reference worksheet; structure and links checked |
| [reference-library/templates/INDEPENDENT-CHECKS.md](../../reference-library/templates/INDEPENDENT-CHECKS.md) | Reference worksheet; structure and links checked |
| [reference-library/templates/PRINT-ACCEPTANCE.md](../../reference-library/templates/PRINT-ACCEPTANCE.md) | Reference worksheet; structure and links checked |
| [reference-library/templates/PROJECT-BRIEF.md](../../reference-library/templates/PROJECT-BRIEF.md) | Reference worksheet; structure and links checked |

