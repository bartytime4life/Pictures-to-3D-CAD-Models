# Studio integration follow-up

Prepared November 17, 2026 after PRs #161–#163. Initial application fixes are commit
`cdb7f0260f0a38a9fc76bd779b22cba96d169fc6`, based on main at
`36ada0982513e2b9e05d4af311cdf234ef8a4fcb`. The follow-up is integrated with
main at `7c6cc0f`, preserving that tested source before the additional keyboard
fixes recorded below.

## Why another change was needed

PR #161 merged the application into main. PR #162 then merged the documentation
into the old application branch rather than main. PR #163 then brought the
documentation onto main. This application follow-up targets that updated main
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

## Initial follow-up verification

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

## Keyboard and science follow-up

The next source review found two keyboard defects at `8f3b95c`:

- Entering, restoring or importing a 20 px endpoint shift made ArrowLeft reduce
  both the value and the slider maximum to 19.75. ArrowRight could not return to 20. The slider now keeps its exploration range fixed during movement; valid
  numeric edits, import and reset choose the range.
- The Science and Knowledge import buttons were followed by visually clipped
  native file inputs in the tab sequence. These proxy inputs no longer receive
  sequential focus. Enter on the visible import button still opens the picker.

All five new browser cases failed at the expected assertions against the
unchanged `8f3b95c` production bundle. The fixes and regression tests are commit
`7243ddc90c437bf34eae9bf88defb55f2e96c57b`. On that application source:

- Production build/typecheck, 30 TypeScript unit tests, `make lint` and whitespace
  checks passed.
- The combined installed-Chrome rerun passed **43 browser cases**, with **one
  optional installed AI-depth case skipped**. This reran the initial follow-up
  suites plus Science/Knowledge import, recovery and all five new keyboard cases.
- Independent source/test review found no actionable issue in the keyboard fix.
- The source-status guide and changelog now distinguish the merged studio and
  documentation from the separate follow-up PR and installed/physical results.

The [independent arithmetic check](evidence/studio-followup/science-audit.mjs)
recomputes three scale cases, six layer boundary examples, three signed-clearance
cases, and diagram bounds at five counts. A deterministic seed of 1711 selects
10,000 layer cases on a 0.01 mm input grid; exact BigInt ceiling division supplies
the independent expected counts and stack heights. All passed. Run it from the
repository root with:

```bash
node --experimental-strip-types docs/validation/evidence/studio-followup/science-audit.mjs
```

This is sampled arithmetic verification, not exhaustive floating-point or
physical validation. The formulas in `frontend/src/science.ts` did not change.
The Science guide's orientation/distance caveats also agree with the abstract of
[Iovenitti's single-image measurement study](https://scispace.com/papers/accuracy-of-three-dimensional-measurement-using-a-single-15p31uj7t8)
and the scene-geometry/reference requirements described in
[Practical single view metrology for cuboids](https://scispace.com/papers/practical-single-view-metrology-for-cuboids-1bu93tytwm).
Those papers motivate the stated limits; they do not validate this application.

Hosted CI and the GitHub review of `8f3b95c` do not cover the later keyboard commit.
The updated PR requires its own hosted checks. Native slicer/Blender operation,
deployment, real-camera accuracy and physical printing remain unverified here.
