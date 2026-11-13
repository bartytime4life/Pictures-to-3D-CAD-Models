# Documentation review: merged acquisition and edge-width work — November 13, 2026

This documentation-only review starts from main
`aa15903c0c3e2415fa5751446c7b871d4d1110cb`, tree
`1c828c0dd54413e78c6f5788d4d702a6c1158d48`. That source includes merged
PRs #105, #107 and #108. PR #106 targeted the earlier research branch;
its documentation reached main through PR #108. The dated
[source and CI snapshot](../project-status.md) keeps branch inclusion and
head-specific hosted checks separate. The primary checkout is preserved.

## Coverage and corrections

| Documentation area | Review and resulting change |
| --- | --- |
| README, index and contributor guidance | Move startup before detailed research, link the current review, and preserve access to earlier evidence |
| Source status and development | Record merged capabilities separately from the four-parameter Gaussian fitter and the unimplemented five-parameter acquisition-aware inverse |
| Capture, architecture, corner/frame and troubleshooting guides | Explain per-direction edge widths when no full covariance is fitted; distinguish the shadow-blurring construction from corner/curve covariance |
| Sensitivity API and mathematical limits | Add full signatures, array/result shapes, channel work/workspace accounting and an explicit no-fit example; clarify the empty chord contribution and conditional brightness-face rank |
| Research and roadmap | Replace stale future-derivative/check statements with links to completed qualifications; keep unknown brightness, rounded objectives, observed-only seeds, rank, work limits and reserved dimensions as future recovery requirements |
| Export, planning, AI and privacy guides | Compare current user flow and data boundaries with source; no new product mode or physical qualification is introduced |
| Companion library | Review its 16 Markdown guides/templates and add the missing dependency-setup prerequisite; retain its revision, source snapshot, generated reader, figures, catalog and PDF |
| Historical validation and fixture guides | Retain their dated source, original failures, counts and saved-only/replay distinctions; do not rewrite frozen plans or archived results |

Three focused read-only reviews cover mathematics, developer contracts and user
guidance. The developer review checks 36 documented entry-point references and
30 parser-bearing Python files statically. Paths exist and the inspected
startup/test/CLI descriptions match their implementations. Those reads make no
capture, reference-model or inverse calls and do not qualify the runtime.

## Verification scope

Repository-wide checks cover Markdown parsing, local links and heading anchors,
tables and code fences. The library's existing documentation-accuracy tests
check its counts, links and worked claims. External URLs are not exhaustively
fetched; the source/PR/CI snapshot is read back from GitHub.

The new example is a documentation smoke check: one area-sensitivity call and
one fixed-linear acquisition call on supplied geometry. It is not independent
derivative validation or a recovery experiment. Its source, example bytes,
checker and expected interface checks are bound before execution. Read-only
CLI help checks launch no services or optimizers.

## Verification results

- All **98 Markdown documents** parse with pinned `marked 17.0.5`.
- The repository-local navigation/structure audit reports zero errors across
  **1,142 local links, 122 heading links and 128 tables**, with balanced fences.
- All **19 existing library documentation-accuracy tests pass**, with no skips.
- The new example executes verbatim with runtime warnings treated as errors:
  **nine resolved source cells and three resolved query rows with six fields**.
  The calls report 9 performed cell-work units and 1,197 linear-stage units;
  those different work counts are not a latency measurement. The eight bound
  implementation/dependency files retain their before/after hashes.
- All **six documented CLI help checks** exit zero: the cell-sensitivity,
  source-cell-mean and acquisition artifact auditors, scalar normalizer,
  photo-benchmark runner and library `cadkit`. No services or inverse fits run.
- All **758 inherited non-Markdown blobs and file modes** match the main base.
  Exactly 20 existing Markdown files and this new review record change; the
  other 77 inherited Markdown files retain their bytes. Existing historical
  validation files, frozen plans, artifacts, tests, images and generated
  products remain unchanged. The final diff passes whitespace checks.

The executed example's SHA-256 is
`6ac3b31e46f679ee151d8751614d6b305903b892f564ec44db146812e74805a2`.
Its expected statuses, shapes and unchanged-source checks were declared before
execution. This receipt checks the documented interface, not numerical accuracy
against an independent oracle. The earlier 259-test result and 33-row study
remain bound to their original source and are not rerun or relabeled here.

No full application/browser suite, installed-tool
handoff, camera/caliper benchmark or physical-print check is added by this
documentation review.
