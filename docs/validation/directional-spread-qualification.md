# Directional-spread diagnostic: frozen qualification

Recorded November 12, 2026 against published baseline
`2d76aeaa41580494794cbaec0dd9ef659a068ee9` (PR #44). **Research only: do not add
production warnings, retune thresholds on these cases or change geometry from
these results.** The diagnostic misses strong directional blur in some cases and
does not identify a unique optical cause. An unflagged result cannot establish
accurate geometry or an adequate blur model.

## Scope and frozen method

The 30-case plan was fixed before execution. Diagnostic thresholds, robust
regression, local Jacobian and capture functions were unchanged from the earlier
Keys-sampling prototype; this cohort used new seeds, poses or shapes. The earlier
examined held-out correction failure remains development history, not a new
holdout. No experimental anisotropic correction was used. **The ordinary
published scalar `correct_blur` path remained active and unmodified.**

The run loaded backend modules and `tests/synthetic.py` from `git show` at the
pinned baseline into process memory. Ten source hashes were verified against
that commit. The filesystem renderer differed from its committed hash; that
work in progress was excluded. Images were generated locally and retained only
as hashes and byte counts; none were uploaded. No production edits, full shared
suites, native CAD tools or model inference were used in this experiment.

For each accepted profile, the prototype fits
`s_i² - 0.49 = (J_iᵀ n_i)ᵀ Σ_photo (J_iᵀ n_i)`, where `s_i` is measured
rectified edge spread, `J_i` is the local inverse-warp Jacobian and `n_i` is its
edge normal. The `0.49 px²` term removes the known final rectified smoothing
variance. The isotropic scale is the median of
`(s_i² - 0.49) / ||J_iᵀ n_i||²`; its disagreement statistic is the median absolute
variance residual divided by `s_i²`. The fitted tensor is empirical, not a
calibrated optical covariance.

Eligibility requires at least 60 accepted profiles, accepted fraction `> 0.6`,
design condition `< 10`, positive-definite covariance and tensor median relative
variance residual `< 0.1`. A flag additionally requires eigenvariance ratio
`≥ 2` and isotropic median relative variance residual `≥ 0.15`. These exploratory
thresholds stayed frozen; they are not confidence levels or uncertainty bounds.

## Complete outcomes

All 30 planned cases were generated. **27 traced: 6 flagged, 16 eligible but
unflagged, and 5 ineligible. Three failed before a usable diagnostic.** The
default-plate convenience feature oracle was available for 20 cases; unavailable
measurements remain distinct from trace failures.

No case with an injected isotropic Gaussian PSF flagged: of 13 cases, 10 were
eligible-unflagged, one ineligible and two trace failures. Of nine injected
directional Gaussian cases, four flagged, three were eligible-unflagged, one
ineligible and one failed tracing. The three eligible misses were the two
anisotropic rectangles and capsule. These constructed counts are **not population
sensitivity or false-positive rates**.

Here, **flagged** means `directional_spread_mismatch`, **unflagged** means
`no_large_directional_variation_detected`, **ineligible** means
`model_not_identified` (unknown), and **failed** means `trace_failure`.

| Case | Outcome |
| --- | --- |
| `iso-clean-new-pose` | Unflagged |
| `iso-shadow-gradient-jpeg` | Ineligible |
| `iso-wall3` | Unflagged |
| `iso-wall7-soft-shadow` | Unflagged |
| `iso-jpeg35` | Unflagged |
| `iso-gamma1p4` | Unflagged |
| `iso-gamma3` | Unflagged |
| `iso-low-contrast` | Failed |
| `iso-material-stripes` | Unflagged |
| `iso-narrow-paper-shadow` | Failed |
| `iso-saved-unsharp` | Unflagged |
| `iso-saved-clipped-contrast` | Unflagged |
| `aniso-ratio1p7-new-angle` | Flagged |
| `aniso-angle104` | Flagged |
| `aniso-strong-jpeg-shadow` | Ineligible |
| `aniso-wall5` | Flagged |
| `aniso-gamma1p4` | Flagged |
| `aniso-low-contrast` | Failed |
| `motion-length6-angle23` | Flagged |
| `motion-length10-angle83-wall` | Flagged |
| `disk-radius2p5` | Unflagged |
| `disk-radius4-jpeg` | Unflagged |
| `gaussian-mixture-core-halo` | Unflagged |
| `double-exposure-offset6` | Ineligible |
| `spatial-isotropic-sigma1to3` | Ineligible |
| `spatial-opposed-anisotropy` | Ineligible |
| `rectangle-two-directions-iso` | Unflagged |
| `rectangle-two-directions-aniso` | Unflagged |
| `rectangle-two-directions-cross` | Unflagged |
| `capsule-directions-aniso` | Unflagged |

## Orientation counterexamples

Directions below are transformed to the photo frame by the local inverse-warp
Jacobian, modulo 180°. Descriptive buckets are X: `[0,10)` or `[170,180)`,
Y: `[80,100)`, and other: the remainder. They do not change eligibility or flags.
Residuals are isotropic relative variance residuals, not millimetre errors or
uncertainty intervals. The orientation audit regenerated the same four image
hashes and exactly the same diagnostic outputs.

| Case | X count / median residual | Y count / median residual | Other count / median residual | Pooled median | Eigenratio / condition |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rectangle-two-directions-iso` | 10 / 0.002253 | 90 / 0.010594 | 4 / 0.211128 | 0.010499 | 2.117 / 5.560 |
| `rectangle-two-directions-aniso` | 11 / 5.874254 | 90 / 0.007102 | 3 / 0.093852 | 0.008388 | 8.650 / 6.779 |
| `rectangle-two-directions-cross` | 11 / 0.019580 | 90 / 0.012332 | 2 / 0.201007 | 0.013424 | 2.771 / 8.191 |
| `capsule-directions-aniso` | 4 / 0.129178 | 83 / 0.007238 | 19 / 0.686024 | 0.009032 | 7.492 / 3.011 |

The axis-anisotropic rectangle's 90 near-Y profiles dominate its 104 accepted
profiles. The 11 near-X profiles have median residual 5.874254, yet the pooled
median is 0.008388. For the capsule, 83 of 106 profiles are near Y; 19 other
profiles have median residual 0.686024, yet the pooled median is 0.009032.
Numerically large minority-direction disagreement disappears from the decision
statistic. Full rank and condition below 10 do not establish balanced evidence.

Removing the isotropic-median gate is unsupported: the isotropic rectangle's
eigenratio is 2.117, so that change would falsely flag it. This demonstrates
confounding in the empirical tensor; its exact cause has not been isolated.
Sampled corners and estimated normals supply extra numerical directions, which
are not automatically valid independent straight-step profile equations.

An independent algebraic oracle supplies two positive-definite covariances,
`[[2,0],[0,5]]` and `[[2,1.5],[1.5,5]]`. Both predict normal variances 2 and 5
on perpendicular X/Y edges. Those two directions give a rank-2 design for the
three symmetric covariance entries; a third 45° normal raises it to rank 3.
A rotated anisotropic Gaussian can likewise have equal X/Y normal variances
while retaining a nonzero cross term. The full-trace cross-angle rectangle has
only two accepted profiles outside X/Y despite numerical rank 3 and condition
8.191. Identifiability under the assumed model and balanced physical evidence
are separate requirements.

## Negative and unknown results

- Gamma 1.4 and 3.0 cases remain eligible-unflagged. Their small-hole maximum
  errors are 0.201211 and 0.150257 mm; outer errors are 0.263878 and 0.198105 mm.
  These are digital errors for those cases, not isolated paired estimates of
  gamma's causal contribution or physical phone accuracy. Saved-value sharpening
  and clipped contrast also remain unflagged despite nonzero geometry errors.
- Both uniform-motion cases flag and pass Gaussian-like profile filters; double
  exposure is ineligible. A flag does not identify a Gaussian optical mechanism
  or a motion path. Small tensor residuals and accepted profiles do not establish
  that the PSF is Gaussian.
- Disk kernels and a core/halo Gaussian mixture remain eligible-unflagged. The
  filters do not reject every non-Gaussian PSF; the mixture's small-hole error is
  0.038349 mm.
- Both spatially varying cases are ineligible, with tensor median relative
  residuals 0.114246 and 0.113885 above 0.1. These are unknown/model-not-identified
  outcomes, not evidence of isotropic or accurate blur handling.
- Strong shadow/gradient/JPEG and strong anisotropic shadow/JPEG cases are
  ineligible. Both low-contrast cases fail sheet finding; the narrow paper-shadow
  case fails with the part-reaches-sheet-edge refusal. All remain in the planned
  denominator.
- Three successful default-plate traces fail the convenience feature oracle's
  five-circle/one-other assumption: wall 7, anisotropic wall 5 and double exposure.
  They remain measurement-unavailable, rather than omitted or called failed traces.

## Decision and research limits

Keep the prototype local, ignored and diagnostic-only. **Do not add a production
warning or automatic correction.** A separately specified successor should
distinguish descriptive orientation spread from full covariance estimation,
examine balanced orientation summaries and independent low-curvature/patch
support, and retain an explicit unknown state. Freeze those definitions before
using a genuinely new cohort. These 30 examined cases are now development
evidence and cannot become untouched validation after retuning.

No new optical-cause claim or physical error bound is supported. At the pinned
baseline the renderer shared production radial inversion, and the convenience
oracle shared production `arc_geometry`. Every optical distortion here has
`k1=0`; the later [independent lens-stress work](radial-inverse.md) is separate.
Motion shifts use bilinear resampling; disk kernels are digital
pixel-centre constructions, and spatial kernels are declared digital models.
Profiles from one synthetic scene family are correlated samples, not independent
capture repetitions. No real-camera population or physical print was qualified.

## Local artifact provenance

The artifacts below reside under `.local/verification/` in the research workspace.
**They are local and are not bundled with this public document.** Names and
SHA-256 hashes identify the archived evidence; they are not download links or
a promise that a fresh checkout contains a runnable reproduction.

| Local artifact | SHA-256 |
| --- | --- |
| `directional-spread-qualification-2d76aea.py` | `bf86f96c29d0489fb2cc01107818fbccabfc6da69a74164cda3927fd715a5c3e` |
| `directional-spread-qualification-2d76aea-plan.json` | `a3a43b7e98f366679f58cdeeb00acee9b0c89198fa046da261aa9133e530202e` |
| `directional-spread-qualification-2d76aea.json` | `75553d347f6791f8731fda810a88de317bdc8b42eaa1374a302743e8c5e812b5` |
| `directional-spread-orientation-audit-2d76aea.py` | `d48bd2321595bc8f86395404d17f77d821491a5da9d543eb3ad5606620689b78` |
| `directional-spread-orientation-audit-2d76aea.json` | `a5d3775944fc3cc6f31554c1a2bc92f9ec04cdbe7ac9ab40fb5b5f32284b0853` |
| `directional-spread-qualification-2d76aea-analysis.json` | `92e23e84da1d1a0a67d8910fb6979cfcff436bcec394239c19fab42bfabd97cd` |

The machine-readable assessment retains all outcomes, source hashes, orientation
data and proof that filesystem renderer work in progress was excluded. Local
runners refuse to overwrite plans/results: reproduction requires unused plan
and output paths, with the plan frozen before execution. The orientation audit
repeats only the four already-examined counterexamples and checks identical
image hashes and diagnostic values; it is not a fresh holdout.

The frozen receipt's phrase “No circle correction is installed, called, or
evaluated” refers to an **experimental anisotropic circle-correction override**.
The ordinary published scalar correction was active. This clarification
preserves the original receipt rather than rewriting it.
