# Documentation review after draft PR #93 — November 12, 2026

This documentation-only follow-up starts from published draft PR #93, head
`f7d116e74b028beffe2dee797518767d0e5b7222`, tree
`aec6ce2f6acedb0c29ad7681a2fdf13662a8a010`. Its local equivalent is `3770486`.
Main was `1d32c432da633df6bb47db2df7b0e9c23de11c81` at the readback. Work is
isolated in a separate worktree; the primary `codex/slicer-integration` checkout
is preserved. The [source and CI snapshot](../project-status.md) is timestamped,
not a live release indicator.

Published as draft
[PR #94](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/94)
against PR #93. Its initial remote head `3726be6` has tree
`51132965248b53294489d91371921e488496d3a7`, exactly matching the verified
local documentation tree. The final status follow-up records PR #93's newly
successful hosted run and PR #94's initial run separately.

## Coverage and changes

The complete Markdown inventory covers the workbench README, user workflows,
engineering and mathematical contracts, API and architecture, setup, developer
commands, capture and calibration, print/export and slicer guidance, privacy,
troubleshooting, research, roadmap, historical validation, printer attribution,
fixture provenance and the companion reference library's guides and worksheets.
Accurate pages and historical evidence retain their existing content.

Current entry points identify the published PR #93 head and dependency base,
with its own hosted run distinguished from earlier successful CI. The preceding
00:23 source snapshot remains accessible by immutable commit link. The original
affine comparison, 943-test interval, preserved failed continuation comparator
and separate successful saved-JSON audit are unchanged.

The [residual-information guide](../finite-residual-information.md) documents
future work, with no archived-data result or available command in this source.
It distinguishes mean sensitivities from profiled-objective derivatives,
fixed-face brightness directions from the full feasible tangent cone, estimated
projector guards from certified bounds, cutoff sensitivity from confidence, and
covariance-specific projection energy from subtraction of nonnested truncated
fits. It also records acquisition/resampling confounding and the additional
source data needed for a new matched experiment.

Navigation, research, roadmap, developer tools, change log and contributor
guidance now use those same boundaries. The proposed implementation remains in
a separate local worktree under review; this change includes no new runner,
plan, numerical result or pass count. Source Markdown in the companion library
does not change, so its generated HTML, figures, catalog and PDF remain intact.

## Verification

Completed checks on this documentation follow-up:

- **80 Markdown files** parse with locked `marked` 17.0.5. All **863 local
  references**, including **84 heading fragments**, and **109 tables** pass.
  Local image paths, code fences and table columns have no errors.
- All **19 companion-library documentation tests** pass, including source
  counts, navigation, generated-PDF references and worked calculations.
- All **four documented Python examples** execute with runtime warnings treated
  as errors. Coordinate predictions resolve; equivalent integer cropping changes
  them by zero in this run. Archived preparation metadata and disjoint 40/16
  samples match. A signature-bound recorder checks the fit handoff, with
  **zero inverse optimizers**. The affine annulus example resolves both queries.
- All **eight read-only help checks** pass. The documented archive commands
  verify compressed and decoded bytes, then reproduce **1,018/1,018** saved-data
  checks without a new fit, archived sensitivity run or timing benchmark.
- All **370 inherited non-Markdown blobs** match the base, including executable
  code, tests, studies, fixtures, saved results and generated-library files.
  Their before/after SHA-256 values are unchanged. The example harness also
  checks all **284 software**, **22 built frontend** and **24 scientific-closure**
  hashes against their original bindings. Whitespace checks pass.
- Read-only mathematics and navigation reviews find no remaining material
  documentation issue. They perform no study numerics. The local research
  guide separately records its pending implementation-review issue; the
  unpublished runner is excluded from this documentation change.

Local receipts are `documentation-check.json`, `markdown-parse.json`,
`documentation-examples.json` and `documentation-source-integrity.json` under
`.local/verification/`. They keep their distinct scopes. The preceding full
software regression remains the existing source-bound 943-test result, not
a newly repeated full suite for this documentation commit.

The primary checkout remains clean at `d747e30`; no application install, merge
or deployment occurs. Documentation execution adds no browser, optical-model,
installed-slicer, physical-print or live-model evidence. The separate
residual-information research goal remains unfinished.
