# Documentation review after draft PR #95 — November 12, 2026

This documentation-only follow-up starts from published draft
[PR #95](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/95),
head `1f51bae35eb862dca4a259016cc31bf1504207f9`, tree
`1a20178c6c0154cd848937ccac138e0e34696212`. Main was
`1d32c432da633df6bb47db2df7b0e9c23de11c81` at the readback. Changes use an
isolated worktree; the primary `codex/slicer-integration` checkout is preserved.
The [source and CI snapshot](../project-status.md) is timestamped, not a live
release indicator.

## Coverage and changes

The review covers the full Markdown inventory: workbench README and navigation,
setup, user workflows, capture and measurements, engineering and mathematical
contracts, architecture and HTTP behavior, developer commands, privacy,
print/export/slicer guidance, printer attribution, research and roadmap,
fixture provenance, historical validation, and the companion reference library's
guides, build instructions and worksheets. Accurate pages and dated evidence
retain their content. The complete file inventory and hashes are recorded in
the local documentation receipt.

Entry points now identify published PR #95 and its dependency chain instead of
presenting PR #93 as the latest reviewed source. PR #94's successful final-head
hosted run is distinguished from PR #95's own run and local documentation checks.
The preceding status page remains available at an immutable source link.

The [finite-chord derivative proposal](../finite-residual-information.md#finite-chord-shape-derivative-a-derived-proposal)
now derives the signed normal-angle derivative and a Gaussian first moment for
both affine and valid projective maps. It states radians, contrast, observation
frame covariance and the whole-material horizon restriction. Cancellation,
representability, fallback work and independent new-scene numerical validation
remain pending. A separate untested local implementation draft is excluded;
this change adds no operator, prospective experiment or numerical result.

The existing [failed residual study](finite-residual-information.md), all unknown
normal columns, original target/completion flags, saved arrays, audit counts and
post-hoc identity retain their exact evidence. Source contracts and user guides
remain distinct from synthetic recovery, physical optics and print acceptance.

The guide corrections also specify HTTP-loopback-only slicer launch, distinguish
the request framing allowance from the image-file cap, and qualify smooth-light
compensation and interpolation phase bias. The developer fitter's accepted
controls and transform sizes are explicit. Companion-library build instructions
use an isolated environment; its generated-reader inputs and HTML/PDF remain
unchanged, so no regeneration is needed for that setup-guide correction.

## Verification

Completed checks on this follow-up:

- **83 Markdown files** parse with locked `marked` 17.0.5. All **911 local
  references**, including **90 heading fragments**, and **112 tables** pass.
  Local image paths, code fences and table columns have no errors.
- All **19 companion-library documentation tests** pass, including source counts,
  navigation, generated-PDF references and worked calculations.
- All **four documented Python examples** execute with runtime warnings treated
  as errors. Coordinate queries resolve; equivalent integer cropping changes
  them by zero in this run. Preparation metadata and disjoint 40/16 samples match.
  A signature-bound recorder checks the inverse handoff with **zero optimizer
  calls**. The affine annulus example resolves both queries.
- All **11 read-only help checks** pass. The two documented archive-review
  workflows verify compressed and decoded bytes and reproduce **1,018 affine**
  and **9,683 residual** saved-data checks. The saved rotation command reproduces
  its archived JSON byte for byte. No diagnostic replay, fit or timing benchmark
  is repeated.
- All **392 inherited non-Markdown blobs** match PR #95, including executable
  code, tests, studies, saved evidence and generated-library files. The example
  harness also checks its original **284 software**, **22 built frontend** and
  **24 scientific-closure** hashes before and after execution. The preserved
  primary checkout remains clean at `d747e30`; whitespace checks pass.
- Read-only implementation, mathematics and user-guide reviews cover API
  contracts, source behavior and the companion library. No unqualified local
  derivative draft is imported or included.

Receipts under `.local/verification/` are `documentation-check.json`,
`markdown-parse.json`, `documentation-examples.json`,
`documentation-residual-commands.json` and `documentation-source-integrity.json`.
The first example-harness attempt stopped on missing historical frontend files;
their exact source-bound build was restored and all 22 hashes verified before
the passing execution. Existing-output refusal during a later harness repeat
was resolved with a fresh scratch directory, preserving prior receipts.

The inherited 943-test result remains bound to PR #93's software interval;
this documentation follow-up does not rerun or extend the full software/browser
suite. No merge, install, deployment, slicer launch, model download or physical
print occurs. The separate numerical-research work remains unfinished.
