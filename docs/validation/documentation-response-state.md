# Documentation review through PR #66 — November 12, 2026

This documentation-only pass uses published [draft PR #66](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/66)
at `81dd0871aab390b1613bedc0d2b7c7f0578cf280`, tree
`944b36b7197de1726259f070fac67cf543575e92`, in the isolated
`codex/documentation-response-state` checkout. The primary checkout remains at
`d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`. Start with the
[task index](../README.md), [setup](../development.md) or
[source/review snapshot](../project-status.md).

## Changes

- Bring the source table through published PR #66 and distinguish the documentation
  branch from the implementation candidate and integrated `main`.
- Refresh exact-head CI observations for PR #65 and PR #66. Preserve incomplete
  runs and older observations under their original scope.
- Add and execute a callable response example; explain original source indices,
  Python query refusals and the CLI's unavailable-query wrapper.
- Clarify exact inputs, decimal input versus rational output syntax, uncertain
  input and rounded optical-value limitations, report contents and retention.
- Add numerical-tool recovery guidance and route current coverage links here.

This pass does not incorporate unfinished work from another worktree. In this
published baseline, response calibration still takes exact input knots; there
is no uncertain-input schema or certified Gaussian-input generator for response
calibration. Other numerical tools have their own bounded-CDF primitives. The
[response implementation record](response-calibration.md) retains its original
regression evidence. Historical validation reports, templates and dated catalogs
keep their original dates and results. The companion library remains Revision 7.

## Verification

All **89 Markdown documents**, **1,335 local links**, **81 fragments** and
**144 tables** pass the repository-wide structural check with no errors.
The complete inventory below is parsed and checked for local file targets,
heading fragments, referenced HTML anchors and table column counts.

The existing library documentation-accuracy suite passes **19 tests**:

```bash
.venv/bin/python -m unittest discover -s reference-library/tests/python -p test_docs.py -v
```

All **28 argparse-based commands** in `scripts/` and `studies/verification/`
return successfully with `--help`; `make help` also succeeds. The nearest-crossing
oracle is excluded from the help census because its `--help` argument runs its
checks and writes a sidecar. No model pull, native launch or photograph upload
is part of these checks.

Seventeen documentation-contract checks pass. They cover both API guides'
**11 HTTP operations** against generated OpenAPI, both documented raw-source
signatures and the common-response keyword-only signature, the response JSON
and Python examples, exact query values, source/input hashes, original-output
preservation, joint incompatibility, unavailable queries, Python query refusals,
numeric-JSON refusal and source preservation. Generating the schema imports the
application without starting an HTTP server or running a CAD build.
Independent read-only reviews found no blocking clarity or mathematical-contract
issues; the response-specific scope above was clarified during that review.

The documented independent commands were also replayed to fresh local outputs:

```bash
.venv/bin/python studies/verification/response-calibration-oracle-v1.py --output .local/response-oracle-new.json
.venv/bin/python studies/verification/response-calibration-study-audit-v1.py --run studies/results/response-calibration-v1.json --output .local/response-study-audit-new.json
```

The graph oracle passes **363 checks**: 343 mathematical cases and 20 resource/
schema controls, with 151 compatible and 192 incompatible cases. The archived
study audit passes **1,319 checks**, retaining all 1,170 candidate rows, 266 common
witnesses and 904 indexed contradictions. There are zero failed checks in either
replay. The latter checks the existing archive; it does not rerun the finite
edge-offset study or produce new optical observations.

All **383 tracked non-Markdown files** match the PR #66 baseline hashes before
and after these checks, including executable source, tests, dependencies,
workflows, archived results and generated library HTML/PDF/catalog outputs.
The edited guides are not generated-reader or PDF inputs, so no library rebuild
or release is created. The separate unfinished worktree is preserved unchanged.
Check receipts and per-file hashes are retained in ignored `.local/verification/`.

These are documentation and bounded numerical replay checks. The earlier
1,324-test full regression remains PR #66's recorded result; this pass does not
claim a fresh full Python/browser run, installed-tool acceptance, camera
calibration or physical fit. Hosted observations remain separate in
[project status](../project-status.md#evidence-by-scope).

## Coverage inventory

Every document below is included in the structural/link audit. Current guides
are compared with relevant source contracts; historical records retain their
source bindings. Generated documents are checked as published artifacts and
are not hand-edited. Structural coverage does not assert fresh external-URL,
runtime or physical verification of every historical claim.

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
| [docs/response-calibration.md](../response-calibration.md) | Current workbench guide or navigation |
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
| [docs/validation/documentation-latest.md](documentation-latest.md) | Historical evidence or source record; retained |
| [docs/validation/documentation-math-state.md](documentation-math-state.md) | Historical evidence or source record; retained |
| [docs/validation/documentation-refresh.md](documentation-refresh.md) | Historical evidence or source record; retained |
| [docs/validation/documentation-response-state.md](documentation-response-state.md) | Current coverage and verification record |
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
| [docs/validation/response-calibration.md](response-calibration.md) | Historical evidence or source record; retained |
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
| [reference-library/BUILD.md](../../reference-library/BUILD.md) | Companion-library guide; separate revision and generation contract retained |
| [reference-library/CHANGELOG.md](../../reference-library/CHANGELOG.md) | Historical evidence or source record; retained |
| [reference-library/CONTRIBUTING.md](../../reference-library/CONTRIBUTING.md) | Companion-library guide; separate revision and generation contract retained |
| [reference-library/GITHUB.md](../../reference-library/GITHUB.md) | Generated dated catalog; retained |
| [reference-library/HANDBOOK.md](../../reference-library/HANDBOOK.md) | Companion-library guide; separate revision and generation contract retained |
| [reference-library/OPENSCAD.md](../../reference-library/OPENSCAD.md) | Companion-library guide; separate revision and generation contract retained |
| [reference-library/README.md](../../reference-library/README.md) | Companion-library guide; separate revision and generation contract retained |
| [reference-library/REFERENCES.md](../../reference-library/REFERENCES.md) | Generated dated catalog; retained |
| [reference-library/RESEARCH-NOTES.md](../../reference-library/RESEARCH-NOTES.md) | Companion-library guide; separate revision and generation contract retained |
| [reference-library/VERIFICATION.md](../../reference-library/VERIFICATION.md) | Historical evidence or source record; retained |
| [reference-library/cadkit/README.md](../../reference-library/cadkit/README.md) | Companion-library guide; separate revision and generation contract retained |
| [reference-library/examples/README.md](../../reference-library/examples/README.md) | Companion-library guide; separate revision and generation contract retained |
| [reference-library/templates/CAPTURE-CHECKLIST.md](../../reference-library/templates/CAPTURE-CHECKLIST.md) | Worksheet and generated-reader input; retained |
| [reference-library/templates/INDEPENDENT-CHECKS.md](../../reference-library/templates/INDEPENDENT-CHECKS.md) | Worksheet and generated-reader input; retained |
| [reference-library/templates/PRINT-ACCEPTANCE.md](../../reference-library/templates/PRINT-ACCEPTANCE.md) | Worksheet and generated-reader input; retained |
| [reference-library/templates/PROJECT-BRIEF.md](../../reference-library/templates/PROJECT-BRIEF.md) | Worksheet and generated-reader input; retained |
