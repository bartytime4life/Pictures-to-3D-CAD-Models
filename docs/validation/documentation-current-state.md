# Current-state documentation review — November 12, 2026

This documentation follow-up uses the reviewed source
`a3a2397cde2b1afbeda133ac86218eaae5a22edc`, including open PRs #47 and #48 on
integrated `main` at `5c07d0f`. The isolated branch is
`codex/documentation-current-state`. Original checkouts, pending numerical
research and earlier evidence were preserved.

The [project-status page](../project-status.md) identifies the source and review
chain. The [older documentation review](documentation-review-2026-11-12.md)
retains its original test counts, baselines and follow-ups; this record does not
replace it or represent a new full product qualification.

## Scope and corrections

All repository Markdown is included in parsing, local-link, fragment and table
checks. Manual review covered the user/developer guides, mathematical claims,
API contracts, evidence navigation, AI/privacy boundaries and all 16 companion
library Markdown documents and worksheets. Generated catalogs and dated
release reports retain their source data and original dates.

| Area | Correction or retained boundary |
| --- | --- |
| Setup and navigation | Explicit browser URLs, `make dev` starts both services, current source/evidence entry point, and separate smoke/browser server selectors |
| API and geometry | Endpoint map, executable rectangle example, error/deletion semantics, default `fallback=false` versus the initial browser upload's opt-in, source pixels versus constructed CAD millimeters |
| Edge interpolation | Continuous symmetric-step result separated from discrete phase error; finite kernel/phase fixtures do not prove arbitrary-edge cancellation |
| Radius notes | Linearized `r_sd` can be unreliable without necessarily underestimating nonlinear spread; “or more” is not calibrated coverage |
| Historical records | Preserve original results and add nearby conditional-resolution interpretation to old “bound” wording; point the old weak-edge finding to its later repair |
| User recovery | Explain unresolved radius searches and conditional estimates; direct fit-critical features to independent measurement or explicit CAD construction |
| Library maintenance | Isolated Python install, explicit interpreter selection, and rerun verification/archive generation after correcting an interrupted release record |
| Evidence | Separate rendered images, continuum observations and numerical checks from absent real-photo, native slicer, live-AI and physical-fit qualification |

Only explanatory docstrings changed in `backend/fitting.py` and
`tests/test_fidelity_math.py`; the CI edit is a comment. No executable
product logic, test assertion, workflow setting, dependency lock or library
reader-generation input changed. Pending Decimal interval files remain in a
separate unpublished worktree and are excluded from this documentation branch.
Conditional feasible-radius inference remains proposed work.

## Verification

- All **59 Markdown documents** parse with the library's locked `marked`
  dependency. **565 local links**, including **43 fragments**, resolve;
  **90 Markdown tables** have consistent columns.
- The existing library documentation-accuracy invocation passed **19 tests**.
  It checks worked numbers, catalog counts, links, figures, command coverage
  and the recorded PDF page count. This is not a full library release run.
- The focused sharp-resolution and phase-fixture invocation passed **10 tests**
  in **2.41 s**, with 64 unrelated tests deselected. No assertions changed.
- The exact Python block from the new API guide ran against this checkout's
  CAD service on loopback port 18020. It checked 40 × 20 × 3 mm dimensions,
  2400 mm³ volume, the server-provided STEP download and HTTP 204 cleanup.
  A follow-up request confirmed the deleted model returns 404. The owned
  service was stopped after checking it.
- The generated OpenAPI contract matches all **11 API operations** in the
  endpoint map. The trace fallback default and strict build schema agree;
  separate invalid-dimension and missing-model requests returned the documented
  422/404 responses with string `detail` messages.
- After removing docstrings from both Python ASTs, each is identical to its
  baseline. Parsed workflow settings are also identical. Ruff and whitespace
  checks passed. Library reader sources, generated outputs, catalog/release
  records and dependency locks are unchanged.
- The revised library release commands were checked against the Makefile and
  with `make -n release verify dist dist-check` using the local interpreter.
  This dry run did not execute a release, archive, native renderer or printer.

The full Python/browser suites and frontend build were not repeated for this
documentation follow-up: executable product behavior and frontend sources are
unchanged. Earlier 630/74 results retain their original run/source binding.

Local receipts are kept under `.local/verification/` and are excluded from
publication: `documentation-check.json`, `documentation-source-check.json`,
`library-docs.log`, `focused-python.log`, `api-example.log`,
`api-contract-check.json`, `library-release-plan.log` and `ruff.log`.
The final document inventory contains the reviewed paths and hashes.

Documentation checks do not refresh external-site availability, software release
or model-license metadata. They do not turn earlier Python/browser results into
a fresh full run, or establish an installed application, deployment, native
slicer acceptance, manufacturing accuracy, physical fit or complete accessibility
conformance. See [validation overview](../validation.md) for the separate records.
