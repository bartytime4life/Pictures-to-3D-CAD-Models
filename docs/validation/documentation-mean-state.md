# Documentation review: source-cell acquisition candidate — November 13, 2026

This documentation-only follow-up reviews published draft
[PR #105](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/105),
head `0866578dfd139be5fd572fd93fb65fe7607de529`, tree
`68f03a8d408dd10b32f4856e5da87260e53b91ac`. The local base
`85541544047e71e8c494bc95ba90ca8df389376a` has exactly that tree. Main at the
16:58 UTC readback is `f2e0fd6a68a4ab26f6eea92a95ebbda673953193`, including
merged PR #104; PR #105 is still open and draft. The primary checkout remains
separate. See the timestamped [source and CI snapshot](../project-status.md).

## Coverage and corrections

| Documentation area | Review and resulting change |
| --- | --- |
| README, index and contributor guidance | Add direct startup navigation and identify this review as current; retain older reviews as historical records |
| Source status and roadmap | Distinguish main, the unmerged source-cell candidate and earlier snapshots; replace the stale future-mean dependency with remaining objective/derivative/recovery work |
| Acquisition methods and developer tools | Add a runnable 3×3 coordinate example, normal representation, complete input ranges, result stages, ordered queries, exception/refusal behavior, hash inputs and corrected workspace formula |
| Brightness mathematics, architecture and engineering limits | Use `A[b*1+(a-b)*c]` and columns `[A*1-A*c,A*c]`; state when constant-preserving simplification is valid and why literal float32/sRGB8 stages are not the smooth idealization |
| Reference-sheet method | Restore the at-most-16% wall-share condition on the reported `0.2 sigma` inward-shift statement; keep original measurements and regression limits |
| Setup, troubleshooting and Gaussian fitter guide | Separate the explicit source-cell API from automatic tracing and the existing Gaussian fitter; explain unknowns and preserve source-bound validation counts |
| Companion library, worksheets, historical validation and fixture guides | Check Markdown/navigation and preserve their existing revision/source scope and generated outputs; link workbench research from the library README |

The focused mathematical, implementation and user-guidance reviews are read-only.
They make no new capture, reference-model or inverse-optimizer calls. Historical
reports, frozen plans, artifacts, tests and runtime code retain their original
bytes. No new implementation or recovery result is introduced by this review.

## Verification

All **94 Markdown documents** parse with pinned `marked 17.0.5`. The navigation
audit finds zero errors across **1,077 local links, 108 heading links and 123
tables**, with balanced code fences. This is a repository-local check; external
URLs were not exhaustively fetched.

The new Python block executes verbatim and returns three resolved queries.
It makes one coverage call and one acquisition-mean call using supplied
parameters, demonstrating the interface rather than independent scientific
validation. Five documented CLI help modes exit zero: the mean artifact
auditor, preceding acquisition artifact auditor, scalar normalizer, photo
benchmark and library `cadkit`. They launch no services or inverse fits.
The library's **19 existing documentation-accuracy tests pass** again.

All **736 inherited non-Markdown blobs and modes** match the declared base,
including runtime code, tests, study plans/data, generated library products and
images. Only 18 existing Markdown files and this new review record change;
the remaining 75 Markdown files retain their original bytes. The final diff
passes whitespace checks. No full application or browser suite is rerun for
this text-only update.

The earlier [acquisition-evidence review](documentation-acquisition-state.md)
retains its own 90-document inventory and 19 library documentation-accuracy
tests. The source-cell qualification's
1,173-test full-suite result belongs to `521c318`; the later 145 focused tests
and 22-check equivalence proof belong to the admitted workspace repair. Those
results are not relabeled as tests of this documentation revision.

Hosted CI for PR #105 was in progress at the timestamp above. Any CI triggered
by this follow-up is separate. No browser, installed application, camera/caliper,
native slicer or physical-print acceptance is established by these text checks.
