# Fixed observation and covariance checks — November 12, 2026

This developer candidate is based on published wall-localization head
`6d2672710e54e9117048613dec6ef3ea448062b7`
([draft PR #59](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/59)).
Production tracing and the frontend remain unchanged from that source.
The [method and commands](../profile-observations.md) describe the new reusable
operator, finite-filter composition and conditional covariance accounting.

## Noise population and denominators

The [frozen plan](../../studies/profile-noise-v1.json) declares four sampling
intervals and three repetition factors. The [complete results](../../studies/results/profile-noise-v1.json)
retain all seven configurations. The two identical 25-sample configurations are
controls in separate density/repeat groups, not different fields. All seven reuse
one ideal Gaussian-blurred step, the same 16 unique input pixels and common
8,192 Gaussian draws with a fixed seed. There are no real-image or camera trials.

All retained ranks are 16. Covariance-aware local information is about
1,388.7744 and predicted position spread about 0.0268339 pixels across every
configuration. The Gaussian trials give about 0.0269624 pixels. The diagonal
independence assumption instead reports 0.0170865 pixels at 25 samples and
0.00599866 at 193, while that estimator's actual conditional spread remains
about 0.0268380 pixels. The complete output retains the analytical and empirical
variances, comparison residuals, matrix hashes and source-pixel identities.

These are linearized known-tone estimators at the declared true edge, not a
study of nonlinear fitted-edge bias, confidence coverage or noisy wall-label
selection. The supplied independent Gaussian pixel noise is not measured phone
noise. Earlier processing and overlapping profiles require their own covariance.

The same results retain three essential countercontrols. A residual `[1,-1]`
against duplicated one-pixel observations has approximately zero pseudoinverse
cost but an outside-support norm `sqrt(2)`. Adding a previously unseen raw
direction genuinely changes information from zero to one. A near-cutoff mode is
retained before repetition and discarded after repetition because the numerical
rank threshold changes. No universal sampling-density invariance is claimed.

Two explicit wall interpretations separated by 3.095238 pixels produce profiles
agreeing within `2.85e-14` levels, while their local free-tone sensitivity scales
are about 0.04373 and 0.04276 pixels. Finite local information cannot remove this
global ambiguity.

## Known smoothing and final sampler

The [complete postblur results](../../studies/results/postblur-operator-v1.json)
retain six development fields crossed with float64/float32, giving 12 cases.
Three supplied optical-spread/orientation pairs `(0.8,0°)`, `(1.3,0°)` and
`(1.3,37°)` each have a one-step alias and a nonambiguous wall.
This is the failure-directed development population from the independent probe,
not a new held-out evaluation. Standard-library `erfc` renders ideal source fields.
Actual identity `rectify_gray`, actual `GaussianBlur` and actual `sample_keys`
supply observations. Identity rectification is checked against the float32 cast.

The explicit seven-tap sigma-0.7 kernel matches the recorded OpenCV impulse
response within `3e-17`. The reusable operator composes the declared 7×7 filter
with Keys sampling and reflected filter borders; it retains replicated final
sampling borders separately. At most 124 samples, 310 unique input pixels and
38,440 matrix cells occur in these controls.

Even giving the final-only comparator oracle second-moment-matched Gaussian
spread leaves truth discrepancies up to 0.06024 linear-light levels and misses
all six one-step aliases. The explicit composed model retains all six. Its truth
prediction discrepancy is at most `1.43e-13` levels for float64 and `2.52e-5`
for float32. Nonambiguous finite-search offset errors are at most `1.10e-9`
and `7.51e-7` pixels respectively. These small matched-model errors do not
establish complete-photo or physical accuracy.

The composed study uses the frozen prior finite-search prototype, pinned by
exact source hash. It does not replace that search by an interval optimizer or
apply covariance weighting to its wall fits. Float32 rounding remains a measured
model discrepancy; nonlinear response, nonidentity warp, uncertain detector/PSF,
texture, curvature and joint camera/shape inference remain unqualified.

## Regression and independent checks

There are 47 new test cases covering actual interpolation/filter composition,
asymmetric signed kernels, reflected/replicated borders and one-pixel axes,
heterogeneous input noise, duplication, rank changes, support refusal, work caps,
both complete studies and CLI output preservation. The targeted invocation
passed all 47. The complete Python suite passed **1,225 tests in 215.00 seconds**,
with zero failures, errors or skips. The [regression receipt](../../studies/results/profile-observations-regression-v1.json)
binds the JUnit result and all 122 frozen Python/source-plan files. Ruff passed
for `backend`, `scripts` and `tests`; Make's new study commands passed dry runs.

An [independent runner](../../studies/verification/profile-observations-oracle-v1.py)
also checked 24 heterogeneous-noise fits and 24 filter
compositions, plus 100,000 Gaussian draws. Largest operator/covariance differences
were about `4.45e-16` and `1.05e-14`; predicted/empirical variance was
1.352061/1.353462. Its [source-bound receipt](../../studies/results/profile-observations-oracle-v1.json)
retains all aggregate checks and the deterministic seed; the complete control
generation is in the runner. This is separate from the 8,192 common draws in
the primary noise study and does not create another physical dataset.

## Documentation coverage

The complete repository audit passed: **79 Markdown documents**, **930 local
links**, **60 heading fragments** and **129 tables**, along with all 19
companion-library Python documentation tests.
Historical counts remain under their original source bindings. Current guides
describe these developer APIs and known operators without treating their
conditional local spreads as physical confidence intervals.

The workbench browser/build record remains the separate
[74-scenario PR #59 run](wall-localization.md#local-fit-resource-and-outcome-checks).
No new UI, installed native-tool, printer or physical check is inferred from
this mathematical module.
