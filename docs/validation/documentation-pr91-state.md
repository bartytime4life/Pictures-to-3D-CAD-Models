# Documentation review on main after PR #91 — November 12, 2026

This documentation-only follow-up reviews integrated main
`ec41b0ce34746c8fffd17fd7beec2b7cba33413c`, after
[PR #91](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/91)
at `65399053b45f3c38a9d6d2084bc2315aac9bd87e` merged through PR #90.
Main also contains PR #85's separate shadow-harmonic change. All executable,
test, study, fixture, image and generated-library files retain main's exact
bytes. Work uses an isolated checkout. The primary `codex/slicer-integration`
checkout and the separate unfinished affine-performance experiment are preserved.

## Coverage and corrections

The complete Markdown inventory covers workbench usage, capture, measurements,
mathematics, API, setup, developer commands, exports, printing, privacy,
troubleshooting, research, roadmap and validation. It also covers printer-source
attribution, fixture provenance, companion-library build/use instructions,
handbook, source snapshots, cadkit, examples and worksheets. Accurate documents
and dated reports are retained without cosmetic rewrites.

The README, documentation index and validation overview now lead to this review.
The [source-scope guide](../project-status.md) identifies PR #91's exact source,
its inclusion through PR #90 and a fresh main/hosted-CI snapshot. The shadow-blur
change and its historical evidence remain separately identified. The preceding
[PR #88 review](documentation-pr88-state.md) keeps its original revision,
counts and timestamps.

The [finite-material guide](../finite-shape-inverse.md) now includes a no-fit
example that exactly reproduces an archived observation preparation and a
caller-controlled handoff to the inverse. It distinguishes crop dimensions,
local indices, global geometry, supplied covariance and the preparation-width
policy. Development and evidence navigation point to the inherited 899-test
software result without turning it into a main, CI, browser or installed result.
Research and engineering guides retain all paired-study misses and upstream
refusals. The roadmap states the remaining model, performance and CAD-integration
requirements; no unqualified acceleration is listed as available software.

## Verification for this documentation change

The local receipt `.local/verification/documentation-check.json` records the
complete Markdown inventory and hashes, local references, fragment targets,
code fences, tables and errors. Companion-library documentation tests check
its existing counts, worked calculations, catalog, figures, generated PDF and
navigation. Generated library outputs and dated release receipts are unchanged.

Executable checks cover the supplied-model coordinate example, its equivalent
integer crop, archived measured-ring preparation, and the helper-to-fitter
argument mapping without starting an optimizer. Read-only help checks cover the
finite-centre, moment, aperture-audit and three measured-ring runners. A complete
tracked-file comparison against `ec41b0c` binds every non-Markdown file to the
reviewed source. Whitespace checks cover the whole patch.

The completed checks pass:

- All **74 Markdown files** parse with the locked `marked` 17.0.5 dependency.
  **778 local references**, including **76 fragment links**, and **103 tables**
  pass navigation/fence/table checks with zero errors.
- All **19 companion-library documentation tests pass**, including the dated
  PDF/count/navigation and worked-number checks. No library output is rebuilt.
- All three Python examples execute with runtime warnings treated as errors.
  The four supplied-model probabilities resolve; equivalent integer cropping
  changes them by at most `1.111e-16`. Archived preparation metadata matches
  exactly, with origin `(119,119)`, crop shape `(63,52)` and disjoint 40/16
  samples. The handoff's complete signature and argument values pass a
  record-only call; **zero inverse optimizers run**.
- All **six read-only runner help checks pass**. All **345 tracked
  non-Markdown files** match `ec41b0c` byte for byte and stay unchanged during
  executable checks. Complete whitespace checks pass.

Example and help receipts are in
`.local/verification/documentation-examples.json`; parsing has its separate
`markdown-parse.json` receipt. No recovery study, browser suite, live AI model,
native slicer or physical print is rerun by this pass. The inherited
[899-test result](finite-photo-intensity-v2.md#software-regression),
[paired scientific result](finite-photo-intensity-v2.md#results-and-source-binding)
and earlier browser runs retain their exact source and execution scope. This
documentation review does not merge, install, deploy or qualify a physical part.
