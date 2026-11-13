# Documentation audit after PR #109 merged — November 13, 2026

This documentation-only pass uses main
`a6990c957a3a8f0a39425a1074239974d499a805`, tree
`60344358be445ef89178de8728917b7e195e1767`. PR #109 merged at 18:23 UTC;
its tree matches that main revision. The [preceding review](documentation-cell-state.md)
retains the 98-document audit and numerical example on its original base.
The primary checkout and separate frozen experimental recovery source are
preserved. That local candidate is outside this main-based documentation change.

## Coverage

| Area | Inherited Markdown documents | Review scope |
| --- | --- | --- |
| Root README, design QA and printer attribution | 3 | Startup, user workflow, recorded interface checks and catalog provenance |
| Workbench guides and index | 33 | Current capabilities, setup, commands, architecture, mathematics, data boundaries and remaining work |
| Dated validation records | 38 | Revision binding, retained failures, conditional claims and navigation |
| Companion reference library | 16 | Build and generation rules, handbook, native examples, calculators, templates and release history |
| Saved-study fixture guides | 8 | Archive/source binding, saved-only audits, replay side effects and original scientific limits |

The inventory is reviewed against the relevant source and saved records. Accurate
guides remain unchanged. Historical records, frozen plans and recorded outcomes retain their bytes.
The handbook correction requires regenerated reader/PDF outputs; other generated
library products remain unchanged. External catalog links are not
exhaustively refetched by this review.

## Changes

- Refresh the main revision, merged PR #109 state and head-specific CI snapshot.
- Put current tools and remaining integration work ahead of historical snapshots
  in the status guide, without changing those historical paragraphs.
- Correct the handbook's statement that diagonal-only fit is impossible. A
  rotated placement must include the full footprint, height and required
  supports/clearances within the usable volume. Regenerate its reader and PDF.
- Describe the corner radius optimizer's actual early-resolution criterion and
  represented-cost allowance, without promising strict descent.
- Warn that the historical photo-v2 continuation is designed to run nine real
  fits before its old-source equality check, which cannot pass on current main. Direct saved-result review
  to the existing receipts; retain the frozen fixture guide unchanged. Explain
  that normal/residual saved-only audits also compare the checkout's source
  hashes and report provenance mismatches on current main.
- State that both local-model benchmark reports overwrite existing paths; add
  the existing library documentation-test command to contributor guidance.
- Update navigation to this review while retaining earlier documentation records.

## Verification

The library HTML and PDF are regenerated from the corrected handbook with
`make html pdf` in its existing environment. The maintenance note does not bump
Revision 7 or rewrite `verification.json`, its catalog snapshot or release archive.

- All **99 Markdown documents** parse with `marked 17.0.5`. The repository-wide
  navigation/structure check has zero errors across **1,152 local links,
  128 heading links and 131 tables**, with balanced fences. Whitespace checks pass.
- All **180 library Python tests** and **58 JavaScript tests** pass, without skips.
  These are library checks, not the workbench application suite.
- The documented standalone command runs all **19 documentation-accuracy tests**
  successfully with the system Python and no optional PDF dependencies.
- The existing reader browser check passes **112 assertions over `file://`** and
  **112 over loopback HTTP** in separate fresh contexts. Receipts and screenshots
  are retained separately. No photo-transfer or native-CAD browser pipeline is
  rerun by these reader checks.
- The rebuilt PDF retains **59 pages**. Text comparison identifies pages **21–22**
  as changed: the corrected paragraph is on page 21 and pushes the following
  paragraph onto page 22. Rendered pages 20–22 have been visually checked for
  clipping, overlap and page flow.
- All **756 other inherited non-Markdown blobs and modes** match the base.
  The two generated exceptions are `reference-library/index.html` and
  `reference-library/output/pdf/pictures-to-printable-cad.pdf`. Runtime source,
  tests, lockfiles, frozen plans, fixtures and saved numerical results are unchanged.
- All **46 inherited validation/fixture Markdown records** retain their bytes.
  The new review is separate from those historical records.

These checks add no numerical recovery experiment, full workbench/browser-suite
result, live model-quality evaluation, installation, deployment, native-slicer
handoff or physical acceptance. Hosted checks require this change's published
head; earlier successful PR #108/#109 runs remain bound to their own heads.
