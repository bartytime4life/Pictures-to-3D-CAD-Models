# Complete documentation review through PR #79

Reviewed **November 12, 2026** against published draft
[PR #79](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/79),
head `32d29f4b4884e6bdc3caf9d4415e48ec00d57562`, tree
`1f65bf8e7b49733906cabd484e6cc94521d2e70a`. This documentation-only branch
builds directly on that source. It does not change runtime code, tests,
configuration, generated reader artifacts or study results.

The primary checkout remains on `codex/slicer-integration` at
`d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`. The independently evolving
`main` remains at `f1679bb50ca39e1764897e00124eccdf41b21f59` at the source check.
Draft [PR #78](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/78)
at `185d682197437581083a8ecd46de6357d7adb846` repairs that main line; it does
not add the conditional PSF research modules. The
[project-status snapshot](../project-status.md) identifies both review chains
and their separate exact-head CI observations. Neither draft was merged at
this review's source check.

## What changed

- Connect setup and navigation to the actual source line. Document a new-copy,
  exact-revision research setup without replacing an existing checkout.
- Distinguish HTTP operations, caller-owned source contexts, explicit conditional
  fits and independent generated studies. Describe data lifetime and guard
  failures in the privacy and troubleshooting guides.
- Add a complete executable synthetic edge-fit example and connect the new
  fitter to the older fixed-PSF, finite-shape and observation guides.
- Keep working-photo pixels, squared-pixel variance summaries, sheet units,
  display coordinates and rectified blur diagnostics distinct.
- Make the half-plane homography equation explicitly preserve material-side
  orientation under a negative homogeneous scale. Check it against the callable
  model and a negatively scaled homography.
- Correct stale future-work and current-review references. Clarify that the ideal
  direction design assumes equal variance-summary weights, rather than deriving
  them from equal raw pixel noise.

Historical validation records keep their original revisions, dates, failures and
counts. The offline library remains Revision 7 with its separate release record;
its catalogs are retained snapshots, not a fresh network or metadata audit.
Accurate documents need no cosmetic change to count as reviewed.

## Checks performed

All **104 Markdown documents**, **1,975 local references**, **131 heading
fragments** and **173 tables** pass structural/navigation checks with zero errors.
The additional local HTML image resolves. The complete inventory follows.

The command/example check passes **32 checks**, including **45 argparse help
paths**, root `make help`, both endpoint maps against all **11 OpenAPI
operations**, raw-source signatures, the response/rectangle/domain examples and
their provenance and overwrite refusals, the new edge-fit example with strict
JSON, the PSF covariance/rank/planner arithmetic, and oriented-homography
agreement including negative scale. The generated example recovers the declared
`0.237` pixel offset and `1.37` pixel width within `1e-6` pixels; this is an exact
synthetic example check, not a physical accuracy specification.

The existing library documentation-accuracy suite passes **19 tests**:

```bash
.venv/bin/python -m unittest discover -s reference-library/tests/python -p test_docs.py -v
```

All **453 tracked non-Markdown files** match the PR #79 baseline before and after
these checks, including product source, tests, lockfiles, workflows, generated
HTML/PDF and saved study evidence. The local freeze manifest's SHA-256 is
`4dcea86d801fb4059d679f9801bac051d3b428dc1c0212c56ee3c75a426b2b3e`.

This documentation review does not rerun the full Python or browser suites,
independent science studies, native CAD/slicer applications or physical captures.
PR #79's 1,844-test and 13-case/225-check results keep their
[original source-bound record](psf-calibration.md). PR #78's 633 tests belong to
its separate main-based source. Passing documentation checks does not merge,
install, deploy or qualify either implementation.

Local audit receipts are retained under ignored `.local/verification/`: the
complete file hashes/navigation report, contract results and example outputs,
CLI help results, library test output and non-Markdown freeze. They are local
verification artifacts, not downloadable repository files.

## Coverage inventory

Every tracked or newly added Markdown document is listed, including root/data
notes, current user and developer guides, dated validation records, library
sources, generated catalog directories and worksheets. Current guides are
checked against relevant source and interface contracts; historical/generated
records are checked for navigation and retained scope. This review does not
revalidate every historical experiment or external source.

| Document | Treatment |
| --- | --- |
| [README.md](../../README.md) | Current guide updated against source |
| [data/PRINTER_SOURCES.md](../../data/PRINTER_SOURCES.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [design-qa.md](../../design-qa.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/README.md](../../docs/README.md) | Current guide updated against source |
| [docs/api-examples.md](../../docs/api-examples.md) | Current guide updated against source |
| [docs/architecture.md](../../docs/architecture.md) | Current guide updated against source |
| [docs/capture-guide.md](../../docs/capture-guide.md) | Current guide updated against source |
| [docs/changelog.md](../../docs/changelog.md) | Current guide updated against source |
| [docs/contributing.md](../../docs/contributing.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/corner-feasibility.md](../../docs/corner-feasibility.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/developer-tools.md](../../docs/developer-tools.md) | Current guide updated against source |
| [docs/development.md](../../docs/development.md) | Current guide updated against source |
| [docs/edge-crossings.md](../../docs/edge-crossings.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/engineering-model.md](../../docs/engineering-model.md) | Current guide updated against source |
| [docs/exports.md](../../docs/exports.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/finite-shape-source.md](../../docs/finite-shape-source.md) | Current guide updated against source |
| [docs/gaussian-response-domains.md](../../docs/gaussian-response-domains.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/material-gradients.md](../../docs/material-gradients.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/ollama-models.md](../../docs/ollama-models.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/ollama.md](../../docs/ollama.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/photo-benchmark.md](../../docs/photo-benchmark.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/pixel-apertures.md](../../docs/pixel-apertures.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/print-planning.md](../../docs/print-planning.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/printer-catalog.md](../../docs/printer-catalog.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/privacy-security.md](../../docs/privacy-security.md) | Current guide updated against source |
| [docs/profile-observations.md](../../docs/profile-observations.md) | Current guide updated against source |
| [docs/project-status.md](../../docs/project-status.md) | Current guide updated against source |
| [docs/psf-calibration.md](../../docs/psf-calibration.md) | Current guide updated against source |
| [docs/raw-source-fit.md](../../docs/raw-source-fit.md) | Current guide updated against source |
| [docs/reference-sensitivity.md](../../docs/reference-sensitivity.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/reference-sheet.md](../../docs/reference-sheet.md) | Current guide updated against source |
| [docs/research.md](../../docs/research.md) | Current guide updated against source |
| [docs/response-calibration.md](../../docs/response-calibration.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/response-rectangles.md](../../docs/response-rectangles.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/roadmap.md](../../docs/roadmap.md) | Current guide updated against source |
| [docs/signed-stencils.md](../../docs/signed-stencils.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/slicers.md](../../docs/slicers.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/source-context.md](../../docs/source-context.md) | Current guide updated against source |
| [docs/troubleshooting.md](../../docs/troubleshooting.md) | Current guide updated against source |
| [docs/validation.md](../../docs/validation.md) | Current guide updated against source |
| [docs/validation/benchmark-correspondence.md](../../docs/validation/benchmark-correspondence.md) | Historical evidence; navigation and scope retained |
| [docs/validation/canonical-arcs.md](../../docs/validation/canonical-arcs.md) | Historical evidence; navigation and scope retained |
| [docs/validation/ci-runtime-budget.md](../../docs/validation/ci-runtime-budget.md) | Historical evidence; navigation and scope retained |
| [docs/validation/contrast-recovery.md](../../docs/validation/contrast-recovery.md) | Historical evidence; navigation and scope retained |
| [docs/validation/corner-blur-domains.md](../../docs/validation/corner-blur-domains.md) | Historical evidence; navigation and scope retained |
| [docs/validation/corner-feasibility.md](../../docs/validation/corner-feasibility.md) | Historical evidence; navigation and scope retained |
| [docs/validation/curved-placement.md](../../docs/validation/curved-placement.md) | Historical evidence; navigation and scope retained |
| [docs/validation/directional-spread-qualification.md](../../docs/validation/directional-spread-qualification.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-alignment.md](../../docs/validation/documentation-alignment.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-complete-2026-11-12.md](../../docs/validation/documentation-complete-2026-11-12.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-current-state.md](../../docs/validation/documentation-current-state.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-latest.md](../../docs/validation/documentation-latest.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-math-state.md](../../docs/validation/documentation-math-state.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-pr70.md](../../docs/validation/documentation-pr70.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-pr72.md](../../docs/validation/documentation-pr72.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-psf-state.md](../../docs/validation/documentation-psf-state.md) | New complete review record |
| [docs/validation/documentation-refresh.md](../../docs/validation/documentation-refresh.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-response-state.md](../../docs/validation/documentation-response-state.md) | Historical evidence; navigation and scope retained |
| [docs/validation/documentation-review-2026-11-12.md](../../docs/validation/documentation-review-2026-11-12.md) | Historical evidence; navigation and scope retained |
| [docs/validation/edge-crossings.md](../../docs/validation/edge-crossings.md) | Historical evidence; navigation and scope retained |
| [docs/validation/engineering-audit.md](../../docs/validation/engineering-audit.md) | Historical evidence; navigation and scope retained |
| [docs/validation/fillet-sweep.md](../../docs/validation/fillet-sweep.md) | Historical evidence; navigation and scope retained |
| [docs/validation/finite-shape-source.md](../../docs/validation/finite-shape-source.md) | Historical evidence; navigation and scope retained |
| [docs/validation/fit-support.md](../../docs/validation/fit-support.md) | Historical evidence; navigation and scope retained |
| [docs/validation/gaussian-response-domains.md](../../docs/validation/gaussian-response-domains.md) | Historical evidence; navigation and scope retained |
| [docs/validation/guided-workbench.md](../../docs/validation/guided-workbench.md) | Historical evidence; navigation and scope retained |
| [docs/validation/material-gradients.md](../../docs/validation/material-gradients.md) | Historical evidence; navigation and scope retained |
| [docs/validation/pixel-apertures.md](../../docs/validation/pixel-apertures.md) | Historical evidence; navigation and scope retained |
| [docs/validation/profile-observations.md](../../docs/validation/profile-observations.md) | Historical evidence; navigation and scope retained |
| [docs/validation/project-import-recovery.md](../../docs/validation/project-import-recovery.md) | Historical evidence; navigation and scope retained |
| [docs/validation/psf-calibration.md](../../docs/validation/psf-calibration.md) | Historical evidence; navigation and scope retained |
| [docs/validation/radial-inverse.md](../../docs/validation/radial-inverse.md) | Historical evidence; navigation and scope retained |
| [docs/validation/raw-source-fit.md](../../docs/validation/raw-source-fit.md) | Historical evidence; navigation and scope retained |
| [docs/validation/reference-sensitivity.md](../../docs/validation/reference-sensitivity.md) | Historical evidence; navigation and scope retained |
| [docs/validation/response-calibration.md](../../docs/validation/response-calibration.md) | Historical evidence; navigation and scope retained |
| [docs/validation/response-rectangles.md](../../docs/validation/response-rectangles.md) | Historical evidence; navigation and scope retained |
| [docs/validation/scientific-model-review.md](../../docs/validation/scientific-model-review.md) | Historical evidence; navigation and scope retained |
| [docs/validation/sharp-corner-resolution.md](../../docs/validation/sharp-corner-resolution.md) | Historical evidence; navigation and scope retained |
| [docs/validation/signed-stencils.md](../../docs/validation/signed-stencils.md) | Historical evidence; navigation and scope retained |
| [docs/validation/source-context.md](../../docs/validation/source-context.md) | Historical evidence; navigation and scope retained |
| [docs/validation/split-plans.md](../../docs/validation/split-plans.md) | Historical evidence; navigation and scope retained |
| [docs/validation/tapered-caps.md](../../docs/validation/tapered-caps.md) | Historical evidence; navigation and scope retained |
| [docs/validation/wall-gradients.md](../../docs/validation/wall-gradients.md) | Historical evidence; navigation and scope retained |
| [docs/validation/wall-localization.md](../../docs/validation/wall-localization.md) | Historical evidence; navigation and scope retained |
| [docs/validation/warp-observations.md](../../docs/validation/warp-observations.md) | Historical evidence; navigation and scope retained |
| [docs/wall-gradients.md](../../docs/wall-gradients.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/wall-localization.md](../../docs/wall-localization.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [docs/warp-observations.md](../../docs/warp-observations.md) | Current guide or data/QA note; source scope and navigation reviewed |
| [reference-library/BUILD.md](../../reference-library/BUILD.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/CHANGELOG.md](../../reference-library/CHANGELOG.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/CONTRIBUTING.md](../../reference-library/CONTRIBUTING.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/GITHUB.md](../../reference-library/GITHUB.md) | Generated source directory; snapshot preserved |
| [reference-library/HANDBOOK.md](../../reference-library/HANDBOOK.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/OPENSCAD.md](../../reference-library/OPENSCAD.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/README.md](../../reference-library/README.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/REFERENCES.md](../../reference-library/REFERENCES.md) | Generated source directory; snapshot preserved |
| [reference-library/RESEARCH-NOTES.md](../../reference-library/RESEARCH-NOTES.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/VERIFICATION.md](../../reference-library/VERIFICATION.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/cadkit/README.md](../../reference-library/cadkit/README.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/examples/README.md](../../reference-library/examples/README.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/templates/CAPTURE-CHECKLIST.md](../../reference-library/templates/CAPTURE-CHECKLIST.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/templates/INDEPENDENT-CHECKS.md](../../reference-library/templates/INDEPENDENT-CHECKS.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/templates/PRINT-ACCEPTANCE.md](../../reference-library/templates/PRINT-ACCEPTANCE.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
| [reference-library/templates/PROJECT-BRIEF.md](../../reference-library/templates/PROJECT-BRIEF.md) | Library guide or worksheet; existing accuracy checks and artifact preservation |
