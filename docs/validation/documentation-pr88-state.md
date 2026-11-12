# Documentation review after PR #88 — November 12, 2026

This documentation-only follow-up reviews published draft
[PR #88](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/88),
source `ed39d2c71c99636debc1a282a2d6ef738bdfce84`, tree
`30f967ab21bc18cf94101fb8df39d836cde869a5`. All executable, test, study,
fixture, image and generated-library files retain those exact bytes. Work uses
an isolated checkout; the primary `codex/slicer-integration` checkout and the
separate unfinished ring-ROI experiment remain untouched by this change.

## Coverage and corrections

The complete Markdown audit includes workbench guides, mathematical methods,
validation records, companion-library instructions, source catalogs, templates
and fixture provenance. Accurate historical records keep their source, date,
counts and failures; they are not rewritten as later test results. The
[preceding PR #86 documentation review](documentation-pr86-state.md) remains
available with its original scope.

The README, documentation index and validation overview now lead to this review.
The [source-scope guide](../project-status.md) identifies published PR #88, its
exact source and dependencies, and a timestamped repository/hosted-CI snapshot.
Architecture and development instructions distinguish its available Python
operators from the automatic workbench and the absent source-space calibration
stack on another branch.

The [finite-material guide](../finite-shape-inverse.md) documents pixel centres,
crop/global mapping, a runnable supplied-model example, result flags, resource
limits and requirements before automatic tracing or native export integration.
Capture and covariance guidance distinguish unknown thickness and unavailable
directional covariance from zero thickness or established isotropic optics.
The [command guide](../developer-tools.md) explains the retained study exit 1,
the supplemental no-refit audit, exact moment replay and provenance-only archive.
Engineering, research, roadmap and change-log navigation now agree with those
boundaries.

## Verification for this documentation change

The local receipt `.local/verification/documentation-check.json` records all
Markdown files, hashes, local references, fragments, fence/table checks and any
errors. Companion-library documentation tests check its existing counts,
handbook calculations, figures, catalog, generated PDF and navigation.

The supplied-model Python example and integer crop/global equivalence are
checked against this exact backend. Help checks exercise only the listed
finite-centre, moment and supplemental-audit parsers; no recovery study is rerun.
A tracked-file comparison against `ed39d2c` verifies that every non-Markdown
file is unchanged. Whitespace checks cover the complete patch.

The complete check passes **71 Markdown files**, **735 local references**,
including **63 fragment links**, and **98 tables**, with no navigation, fence
or table errors. All **19 companion-library documentation tests pass**. The
four-pixel Python example resolves all probabilities; its equivalent integer
crop differs by at most `1.388e-16`. All three read-only help checks pass, all
**329 tracked non-Markdown files** match `ed39d2c` byte for byte, and whitespace
checks pass.

These checks assess documentation and its examples. The [862-test Python result](finite-free-centre.md#software-regression)
and the preceding [74-scenario browser result](directional-free-arcs.md) retain
their original source and execution scope. Neither is rerun or claimed as a new
result here. No library release, installed-software validation, merge,
deployment, real-camera accuracy, native-slicer acceptance or physical print
qualification follows from this documentation change.
