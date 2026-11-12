# Documentation consolidation through PR #51 — November 12, 2026

For the latest documentation coverage, use the
[current alignment record](documentation-alignment.md) and [project status](../project-status.md).
The dated evidence below retains its original source and results.

This documentation-only follow-up starts from
`b366b3f2cda4ca33a34b2b2aa109a9b1718acb0c`, the published head of
[draft PR #51](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/51).
The isolated branch is `codex/documentation-current-math`.
The primary checkout and earlier branches remain unchanged.

## Coverage and corrections

The full documentation set covers the workbench, developer tools and companion
reference library. The [task index](../README.md) routes capture, measurement,
CAD export, print planning, troubleshooting, optional local AI, API use and
development to their guides. The mathematical methods and remaining limits
are described in the [engineering model](../engineering-model.md),
[research guide](../research.md) and [conditional corner CLI](../corner-feasibility.md).

This final pass corrects the current-state navigation and review snapshot:

- The [status page](../project-status.md) identifies every published head and
  base through PR #51, the integrated `main`, and the timestamped hosted-CI state.
- The task index and [validation overview](../validation.md) link this record.
  Earlier documentation reports are explicitly historical and retain their
  original source, counts, failures and observations.
- The latest full Python result is distinguished from the earlier browser/build
  run. Version-1 fixed-blur and version-2 joint-domain examples keep their
  different input/output contracts and physical assumptions.
- Setup commands, browser URLs, development scripts and test-server selectors
  agree with the reviewed source. No further behavior or command correction
  was found in those entry points.

All 16 companion-library Markdown guides and worksheets remain in the complete
Markdown checks. Its revision-7 catalog, generated reader/PDF, release records,
images and source snapshots retain their separate provenance; this follow-up
does not regenerate a library release.

## Verification and source binding

All **63 Markdown documents** parse with the library's locked `marked`
dependency. **614 local links**, including **47 heading fragments**, resolve;
**99 tables** have consistent columns. Whitespace checks pass.
The machine-readable inventory and document hashes are retained locally in
`.local/verification/` along with the exact base and final diff.

The preceding shared-blur source passed **839 Python tests** and **19 companion
documentation tests**. Its [validation record](corner-blur-domains.md) retains
independent mathematical checks, unresolved cases and the frozen source hashes.
Both exact guide examples were run from the clean published `b366b3f` checkout:
saved reports agreed with stdout and recorded the canonical input, input hash,
all four implementation hashes, and clean Git/source state. This documentation
pass checks those receipts and code equality with that source; it does not
represent another full Python run or refreshed CLI Git metadata.

The earlier [PR #49 review](documentation-current-state.md) records its executable
40 × 20 × 3 mm API example, export/deletion checks and 19 documentation tests.
The latest browser/build evidence remains the source-bound
[corner-resolution run](sharp-corner-resolution.md), with 630 Python tests and
74 browser scenarios. No executable source, workflow setting, dependency lock,
frontend or generated library artifact changes in this follow-up, so these
broader suites and native tools are not rerun for documentation.

The [hosted workflow snapshot](../project-status.md#evidence-by-scope) is separate
from local results. Open reviews, successful local checks and successful CI do
not establish a merge, installation, deployment, real-camera accuracy,
live-model answer quality, native slicer acceptance or physical fit. Real
capture and physical qualification remain open engineering work.
