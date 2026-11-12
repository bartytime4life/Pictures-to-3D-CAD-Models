# Warp composition and optical-source checks — November 12, 2026

This candidate is based on published fixed-observation head
`778c3392c6dfe111d8f422959fbdbc09ad8ba75b`
([draft PR #60](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/60)).
Production tracing, frontend and dependencies are unchanged. The
[method and commands](../warp-observations.md) explain the fixed `S G R` operator,
source optical models and remaining physical/parameter-selection limits.

## Complete digital population

The [plan](../../studies/warp-observations-v1.json) declares six source arrays:
constant, ramp, smooth trigonometric field, fixed-seed random field, impulse and
Gaussian step. Each goes through three supplied maps, three `k1` values and two
output scales, giving 108 processed chains. Three profile locations read each
chain: interior, corner and outside the rectified grid, giving **324 readouts**.
All keys are unique and complete. The source arrays are reused across treatments.
They are already-linear numerical fields, not encoded camera captures.

The [complete results](../../studies/results/warp-observations-v1.json) retain
every readout, matrix hash, source-array hash, stage error and runtime version.
The float64 staged reference intentionally shares production's map/sampler;
separate tests independently calculate the coordinates, and an independent
raw-edge implementation checks the composed result below.

| Quantity over all 324 readouts | Recorded maximum |
| --- | --- |
| Matrix versus staged float64 profile | `1.99e-13` linear-light levels |
| Matrix versus actual float32 pipeline | `2.96e-5` levels |
| Reconstruction error after measured cast/blur stage deltas | `1.79e-13` levels |
| Measured-stage triangle envelope | `3.23e-5` levels |
| Source pixels in one local operator | 317 |
| Matrix cells in one local operator | 15,533 |
| Partition-of-unity discrepancy | `3.11e-15` |

There are zero measured-envelope violations after the recorded numerical
allowance. The stage deltas are measured for each input. This is an accounting
identity and finite numerical control, not a vendor-arithmetic proof or a bound
for unseen images. Float32 rounding remains distinct from supplied raw noise.
Under declared unit independent raw-pixel noise, adjacent readouts have
correlations about 0.99071–1, with roundoff-scale overshoot above one retained.
This is not a measurement of camera noise or postselection-calibrated covariance.

## Optical-source controls

The [independent runner](../../studies/verification/raw-gaussian-warp-edge-v1.py)
and [canonical results](../../studies/results/raw-gaussian-warp-edge-v1.json)
retain **18 fields**: an identity-Jacobian map, three nonidentity affine maps and
two homographies, each at three plane-normal orientations. All source fields use
supplied translation-invariant Gaussian optical spread in raw sensor coordinates.
A positive inverse projective chart is checked over the entire finite raw sensor.
The "identity" control includes translation; it is not pixel-aligned rectification.

Independent 128-node Gaussian half-plane integration agrees with the raw-line
CDF within `6.22e-15` probability. Exact and direction-specific affine fields
agree exactly after the actual float32 pipeline in these controls. The frozen
Jacobian approximation reaches 0.147875 levels of discrepancy for homographies;
a geometric-mean scalar reaches 8.47010 levels across the fields. Skipping raw
rectification reaches 0.287232 levels. These retain demonstrated source-model
and interpolation effects, rather than attributing everything to blur width.

The composed operator differs from independently implemented float64
rectification/filtering/sampling by at most `4.84e-13` levels and from the actual
float32 chain by `3.18e-5`. Its largest local matrix has 395 source pixels and
50,955 cells. The known digital smoothing kernel is verified against the
recorded runtime's impulse, rather than assumed to be an API guarantee.

Two additional radial quadratures, with 128 and 256 nodes and a ten-sigma tail
window, retain a supplied `k1=0.25`, optical sigma 3 pixels and an off-centre curved
boundary. Response at the boundary is about 0.4985125165; the half-level shift
is 0.0111858853 raw pixels. The two shifts differ by `2.85e-14` pixels. The omitted
Gaussian-tail probability is bounded analytically and evaluated in floating
arithmetic; it does not bound quadrature discretization error. This separate
control is not a complete radial image pipeline or physical error certificate.

## Regression and review

The targeted invocation passed **71 tests**, including 24 new cases. New coverage
includes generic nonlinear maps, independent scalar projective/radial mapping,
different source/output sizes, ppm units, homogeneous sign, border order, source
noise sharing, non-finite coordinate refusal, resource caps, zero-functional
preservation, all 324 readout keys and fresh-output CLI contracts.

Independent review found and reproduced a zero-functional defect in the first
development builder: a valid zero filter was refused by subsequent warp methods.
The final implementation preserves zero and still refuses its zero-rank noise
factorization. No production camera or accuracy threshold was changed.

The malformed-horizon negative control is low-level geometry only. Its projected
corner order is nonconvex; no failure from a valid sheet photograph was reproduced.
The new builder refuses it before integer conversion. Separate independent
generic-field comparisons retain agreement within `6.26e-13` levels on their
48 source-chain controls; source-bound development receipts remain locally under
`.local/verification/` in the preserved PR #60 worktree.

The complete Python suite passed **1,249 tests in 216.60 seconds**, with no
failures, errors or skips. The [regression receipt](../../studies/results/warp-observations-regression-v1.json)
binds the JUnit output and 127 frozen Python/source-plan files. Ruff passed for
`backend`, `scripts`, `tests` and the new independent runner. The new Make target
and fresh-output CLI contracts have separate checks.

## Documentation coverage

These are the checks at this PR #61 source. The later
[documentation alignment](documentation-alignment.md) records repository coverage
through PR #62 and updated hosted observations separately.

The complete repository audit passed: **81 Markdown documents**, **953 local
links**, **61 heading fragments** and **130 tables**, plus all **19** companion-
library Python documentation tests. Historical reports retain their own source
hashes, populations, counts and environments.

Browser/build evidence
remains separately bound to the [PR #59 run](wall-localization.md#local-fit-resource-and-outcome-checks).
No segmentation, fitted-ring/CAD evaluation, native-tool acceptance, physical
dimensions or real-camera confidence result is inferred from these studies.

The separately inspected [hosted PR #59 run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43214844810)
passed all 1,178 Python tests in 527.19 seconds. Its log then records 58 browser
passes, with no failed scenario before cancellation near the configured
30-minute job budget. That is incomplete hosted-browser evidence, separate
from the complete local 74-scenario record. The validation workload/budget needs
follow-up; cancellation is not a successful suite or a reproduced assertion
failure. PR #60's library run has passed, while its workbench run was still in
progress at this observation.
