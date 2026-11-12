# Wall-localization development record — November 12, 2026

This candidate is based on published documentation head
`0f5f888708b623245854b53458431af495b387fe`
([draft PR #58](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/58)).
Its production baseline is unchanged from `7dfe0fe698c8831e9c02ae960f03bcdc533701dc`
(PR #57), which the paired comparison loads from Git in an isolated namespace.
The primary checkout is preserved. See the [method and remaining model limits](../wall-localization.md).

## Reproduction and final comparison

An independently rendered rectangle with a visible wall reproduces an initial
trace near the wrong boundary. For one 1.2-pixel-blur bright-wall case, the old
local search leaves about 2.92 pixels of error. Expanding hypotheses and updating
the candidate width substantially improves that example. The complete crossed
population prevents that selected example from becoming a general accuracy claim.

The [frozen plan](../../studies/wall-localization-v1.json) crosses six wall levels,
two supplied optical blurs, two phases, two quarter-turn orientations, two
contrast polarities: **96 underlying light fields**, each with point and
uniform-pixel-mean observations, giving **192 observation scenes**. The artifact's
`world_scenes` field counts these observation scenes. Each is evaluated by both
implementations. Original failure cases informed
the plan; neither freezing it nor adding crossed treatments makes it held out.

The actual calls are segmentation of independently encoded sRGB8, subpixel rings
on the independent linear field, and `_refine_walls` with a supplied camera,
scale and thickness. The central-left points are selected before correction.
All selected points remain in final-error summaries, including unchanged seeds.
The denominator is those retained points, not every classified image boundary.
Pose estimation, rectification, earlier image-processing stages, parallax, CAD,
real captures and fabrication are outside this comparison.

The [full CSV](../../studies/results/wall-localization-v1/cases.csv),
[executed plan](../../studies/results/wall-localization-v1/plan.json),
[results](../../studies/results/wall-localization-v1/results.json) and
[independent accounting audit](../../studies/results/wall-localization-v1/audit.json)
retain all **192 paired successful observation scenes**, **zero failed lanes**, identical
initial-ring hashes in every pair and **12 recomputed summary groups**.
All reported successful numerical outcomes are finite. Execution success is
separate from correcting an edge or identifying a physical surface.

| Wall level | Point baseline max error, px | Point candidate max error, px | Pixel-mean baseline max error, px | Pixel-mean candidate max error, px |
| --- | --- | --- | --- | --- |
| 90 | 0.00852 | 0.01263 | 0.01472 | 0.01605 |
| 110 | 0.01834 | 0.02490 | 0.01444 | 0.02531 |
| 130 | 1.00032 | 0.16130 | 0.90174 | 0.02924 |
| 150 | 2.47082 | 0.34570 | 2.40358 | 0.14496 |
| 165 | 2.94750 | 2.94845 | 2.93749 | 2.94783 |
| 170 | 3.04207 | 3.04609 | 3.04216 | 3.04631 |

Each maximum covers 16 worlds, with no failure or unchanged-point exclusion.
The high-tone groups retain large errors, including cases where no shared tone
is selected and the seed remains unchanged. Low-tone controls can worsen.
The [figure](../images/wall-localization.svg) shows every group, rather than only
successful bright-wall examples. Elapsed times were collected while other checks
ran; they are not isolated performance measurements or a UI latency qualification.

## A development window that failed

The first expanded-observation-window candidate passed **1,176 tests** but
failed **two** existing camera-height regressions. Its [regression receipt](../../studies/results/wall-localization-expanded-window-v1/regression.json),
[192-world CSV](../../studies/results/wall-localization-expanded-window-v1/cases.csv),
[summary](../../studies/results/wall-localization-expanded-window-v1/results.json),
[audit](../../studies/results/wall-localization-expanded-window-v1/audit.json) and
[exact differing source](../../studies/results/wall-localization-expanded-window-v1/executed-source/backend/edges.py)
are preserved. The final near-window comparison reuses the same worlds; it is
a repair comparison, not another independent 192-world evaluation population.

For the frontal 440 mm fixture, the failed candidate estimated 426.938 mm,
outside the existing 2 % guard. For the 600 mm long-lens fixture it fell back to
an assumed camera rather than accepting the expected hole-based estimate.
No assertion, camera gate, fixture or accuracy tolerance was loosened.

Independent captured-field ablations isolated the cause. Recomputing corrections
at every original camera trial still produced about 427.2 and 788.0 mm, and simple
alternation did not repair both cases. Even supplying the true camera did not
make the expanded-window wall-refined holes yield the true camera on refitting.

For the long-lens assumed-camera data, the expanded window's bright-wall minimum
near level 161 has SSE about 89,744 versus 93,551 for its dark basin. Keeping the
expanded geometry search with centered local observations instead gives dark
SSE 24,936 versus bright 30,792. Costs from different observation windows have
different data and counts; their absolute magnitudes must not be compared as
improvement scores. Their within-window branch rankings are the useful control.
Grid-phase controls preserve that reversal. At the true camera, the centered
branch gap is only about 58.8; this is not a physical-confidence margin.

The final implementation retains the broader geometry search, coupled width,
SVD refinement and withholding checks, while sampling the local observation
window. Frozen diagnostic scripts, captured arrays, source archive and exact
receipts are preserved locally under `.local/verification/`. They are development
diagnostics, not a separate measured-camera qualification dataset.

## Local-fit, resource and outcome checks

There are **47 new regressions**: independent continuum profiles beyond the old
search, exact one-step aliases, fixed-prior controls, endpoint/flat withholding,
invalid-profile isolation, preallocation limits, batching, aperture quadrature,
coordinate transforms, actual call paths, non-finite result refusal and unknown
study outcomes. The targeted combined invocation passed **69 tests**.

The final complete suite passed **1,178 tests in 215.43 seconds**, with no failures
or skips. Exact results and executed source hashes are recorded in
[the final regression receipt](../../studies/results/wall-localization-v1/regression.json).
The earlier failed invocation remains separate.

The production interface build (`npm run build`) and `make lint` passed. A fresh
service from this checkout then passed **all 74 browser scenarios in 319.39
seconds**, using Google Chrome 157.0.8103.50, Node 22.13.1, npm 10.9.2 and one
worker. The unchanged test configuration retained its normal timeouts and
expectations; there were no failures, skips or flaky outcomes. This includes
the reference-sheet trace/build/export path. The [browser receipt](../../studies/results/wall-localization-v1/browser.json)
records report hashes, source hashes, built-asset hashes and per-file counts.
The dedicated loopback service was stopped after the run. These checks do not
establish native slicer import, an installed release or physical accuracy.

The existing wall-gradient population was also rerun with the final helper:
**840 direct fits**, **576 resolved image fits**, zero execution failures and
zero unresolved rows in that population. Its [full results](../../studies/results/wall-gradients-localization-v2/results.json),
[image CSV](../../studies/results/wall-gradients-localization-v2/image-fits.csv),
[geometry CSV](../../studies/results/wall-gradients-localization-v2/geometry-fits.csv) and
[audit](../../studies/results/wall-gradients-localization-v2/audit.json) remain
separate from the unchanged PR #57 archive. Version 2 of the result schema can
retain unresolved profiles with empty measurements and separate unresolved
counts. A dedicated regression verifies that unknowns are not execution failures;
the audit still reads archived version-1 results.

Separate floating mathematical checks retain 240/240 independent-`erfc` pure
profile aliases and resolve 72/72 positive controls, with maximum position error
about `1.46e-6` pixels. Those checks precede the final window change and bind their
own source; the final regression suite covers the changed window separately.
Allocation checks cover 2,805 grid specifications and preserve oversized-profile
unknown outcomes. None is an exhaustive interval or camera-noise certificate.

## Matched final-sampling prototype

Two [developer](../../studies/verification/wall-keys-forward-prototype-v1.py)
[runners](../../studies/verification/wall-keys-forward-offgrid-v2.py) and their
[first controls](../../studies/results/wall-keys-forward-v1.json) and
[off-grid controls](../../studies/results/wall-keys-forward-offgrid-v2.json)
retain **24 development cases** against the final fixed-window source.

The explicit signed stencil predicts the actual Keys profile within `1.14e-13`
linear-light levels across all 24 controls. Ten nonambiguous off-grid matched cases
recover the declared offset within `1.25e-9` pixels, and both off-grid one-step
controls retain ambiguity. A continuous-profile fit instead selects an offset
near 3.091 pixels in the representative one-step case, while the matched
operator retains interpretations near 0 and 3.095 pixels. Matching Keys alone
to pixel-mean data remains a model mismatch; the matching aperture is needed too.

The stencil intentionally shares the actual Keys weight function. Source fields
use independent standard-library `erfc`; analytic rendered means are compared
with quadrature predictions. This supports the supplied final-operator model,
not an independent validation of all production optics. Earlier rectification,
float32 conversion, smoothing, unknown sensor footprints, camera tone response,
curved geometry and physical-error budgets remain unqualified. The prototype is
not applied to production traces.

## Documentation coverage

The documentation review covers the repository's **77 Markdown documents**,
including the workbench guides, API examples, numerical-tool catalog, research
records, companion-library documentation and templates. Current guides now
describe the expanded candidate geometry, local observation window, numerical
withholding, version-2 study outcomes and separate matched-sampling prototype.
The method, developer commands, architecture, capture advice, roadmap, change
log and evidence navigation link to this source-bound record.

Every Markdown document parsed successfully. All **906 local links**, **59 heading
fragments** and **128 tables** passed a complete audit. The [documentation receipt](../../studies/results/wall-localization-v1/documentation.json)
binds those results to all reviewed Markdown files. The companion library's **19 Python
documentation tests** also passed. Historical reports retain their original
source, populations and counts; generated library artifacts retain their
existing release record. The [earlier complete documentation review](documentation-complete-2026-11-12.md)
records the setup, API and library-guide refresh already included in this base.

## Reproduce and interpret

Use the [method's commands](../wall-localization.md#repeat), fresh result paths
and the exact recorded source. Each CSV auditor recomputes complete keys and
summaries; it does not rerender the data or certify the optimizer. The existing
camera guards remain acceptance regressions for their synthetic fixtures,
separate from real-photo performance. Reserved measurements and additional
informative captures remain necessary for fit-critical reconstruction.
