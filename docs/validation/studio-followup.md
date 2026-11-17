# Studio integration follow-up

Prepared November 17, 2026 for PR #163. Application fixes are commit
`cdb7f0260f0a38a9fc76bd779b22cba96d169fc6`, based on main at
`36ada0982513e2b9e05d4af311cdf234ef8a4fcb`. The combined branch preserves that
application source and also carries the documentation previously merged in #162.

## Why another change was needed

PR #161 merged the application into main. PR #162 then merged the documentation
into the old application branch rather than main. The follow-up targets main
directly and retains the original documentation commits and evidence records.

The [review finding on #161](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/161#discussion_r4595125679)
identified a retained-studio lifecycle bug: after a relief build, clearing all
temporary exports from Flat part deleted the relief's files but left its download
controls enabled. The regression test confirmed an actual STL changed from HTTP
200 to 404 while the old page did not provide invalidation/rebuild guidance.

Separately, [the #162 CI run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/44013885378/job/133807066630)
passed 1,566 backend tests (11 skipped) but failed one of 122 browser cases:
119 passed, two skipped, and the 320 px overflow assertion reported `SPAN.sr-only`.
The same failure was reproduced locally before changing the browser bundle.
These are historical results, not a pass for the follow-up revision.

## Corrected behavior

Successful cleanup now invalidates retained Relief exports synchronously. Its
picture, settings and local preview remain available; downloads and Blender
opening require an explicit fresh build. Failed cleanup preserves valid results.
Generation checks suppress late build responses, retry timers and download
completions from before cleanup, so they cannot restore deleted exports or
replace a newer model's state. Cleanup messaging names both studios.

The command label's hidden suffix is anchored inside its parent rather than at
an automatic inline position beyond the clipped phone label. The complete
accessible name remains available. The original strict overflow assertion is
unchanged; the test also checks the complete accessible name at 320 and 360 px.

## Follow-up verification

- Production build and TypeScript check: passed.
- TypeScript unit tests: 30 passed.
- `make lint` and authored whitespace/Markdown formatting: passed.
- Installed-Chrome browser rerun: 31 passed; one installed AI-depth case skipped
  because its optional model was unavailable.
- Independent source review found no actionable issue in the shared invalidation
  logic or its regression tests.
- Combined-branch comparison confirmed that application source and tests match
  the tested fix commit exactly. Documentation and original evidence were added
  without changing that application source.

The browser rerun covered the new shared-export cases plus the existing
workbench, studio navigation/accessibility, relief and slicer suites. The three
new cases verify real deletion and a fresh valid STL download, failed cleanup,
and a completed server build whose response arrives only after its files have
been deleted. Native launch availability is mocked; no native tool is launched.

Hosted checks for the new head are a separate result. Backend source did not
change in this follow-up. Native slicer import, deployment and physical printing
remain outside these checks.

The [initial interface review](precision-studio.md) and
[previous PR verification](precision-studio-pr.md) retain their original revisions,
counts and limitations. The historical interface manifest is unchanged.
