# Finite-material centre inverse — November 12, 2026

This candidate adds the conditional developer model in
[finite-material intensity fitting](../finite-shape-inverse.md), based on
documentation PR #87 (`d5d24e5`, tree-equivalent local review commit `28a7157`).
The workbench's automatic trace, native exports and interface are unchanged.
The independently evaluated shape is one complete disk cut by a half-plane;
fixed chord direction, homography and observation-frame covariance are supplied.

## Implementation and independent methods

The inverse fits `(Cx,Cy,R,f)` and profiles two bounded brightness levels.
It retains a complete coarse grid, represented local basins, unknown/work
outcomes, actual-cost checks and raw/transformed residuals. Shape derivatives
use boundary transport; optimization uses both terms of the fixed-active-face
variable-projection Jacobian. The nuisance-projected mean supplies the local
geometry rank, separately from the residual-dependent derivative term.

The finite evaluator starts from the previously reviewed kernel, retaining its
public integer-pixel ring contract. Private geometry/evaluation extraction lets
the parameterized D operator build local analytic curves directly. This avoids
reconstructing a rounded world-coordinate circle that differs from the requested
parameters. Ordinary public-kernel parity and independent tiny-radius/large-
coordinate area controls cover the change. A requested absolute derivative
tolerance of `1e-10` remains unresolved in the extreme-scale control; the default
`1e-8` control is separate and passes. No production tolerance was relaxed.

The [prospective plan](../../studies/finite-free-centre-v1.json) specifies 12
matched configurations and 12 diagnostics. An independent positive-area oracle
transforms the disk to a conic, clips vertical slices by the projected chord,
and integrates conditional Gaussian CDFs using `erfc`. It does not call the
production Green-boundary means. Observed fields supply the circle seed, bounds
and fixed 40 training/16 disjoint held-out pixels. Synthetic truth enters only
subsequent scoring; failed domains are not widened using it.

The initial split-rule wording produced 42/14 pixels despite the stated 40/16
contract. That plan and renderer/derivative receipt were preserved before any
recovery experiment. Correcting only the split rule restored the declared counts;
the plan was frozen again at SHA-256
`f8db267fd848363ba91b56cd5a01086f3123ad699f6c0c404166734f3bc582fd`.
No geometry target, case or fit domain was changed.
The [initial plan](../../studies/fixtures/finite-free-centre-v1/initial-plan.json)
is retained for comparison with the corrected frozen split.

## Independent recovery outcomes

The [complete frozen result](../../studies/results/finite-free-centre-v1.json)
retains all **24 rows**, with zero execution failures. All **12 matched cases**
meet their declared targets, including the absence of work, numerical and
refinement incompleteness. Their evaluation truths lie inside the independently
observed domains. Maximum matched centre error is `9.353e-8` observation pixels,
scaled radius error `8.075e-8` pixels, fraction error `3.480e-9`, and held-out
intensity error `3.620e-6` on the 0–255 scale. These are noiseless, matched-model
numerical comparisons; they are not physical error bounds.

All **19 derivative/rank/invariance controls** and **four closed Gaussian oracle
controls** pass. Of 22 available planned oracle-order comparisons, **21 pass**.
The adverse uniform-pixel-aperture comparison at 4×4 versus 8×8 order differs
by `8.0651e-7` intensity levels, exceeding the unchanged `1e-7` criterion.
The complete study therefore retains **exit 1**. It must not be summarized as
an all-passing experiment.

A [separately bound aperture audit](../../studies/results/finite-free-centre-aperture-audit-v1.json)
uses the same 56 training/held-out pixels, reproduces the original 8×8 values
bit-identically, and compares them with 16×16 integration. Its maximum difference
is `1.4211e-13` levels. This supplements the actual observation's numerical
support; it does not erase the failed planned 4×4-to-8×8 comparison or refit the
case. The [audit runner](../../studies/verification/finite-free-centre-aperture-audit-v1.py)
is separate from the frozen main experiment.

Adverse outcomes remain materially different from the matched cases. The
cropped-chord fit has local geometry rank three, an endpoint result, fraction
error about `0.4517`, mapped-boundary error `4.697 px` and held-out error
`155.33` levels despite a small centre error. Wrong covariance produces centre
error `0.55135 px`; nonlinear response produces radius error `0.1753 px`;
material gradient and neighboring-hole cases also remain biased. Constant and
low-contrast fields are explicitly seed-ineligible. None is removed from the
denominator or relabeled as qualified.

All **14 main CLI/continuation contracts** pass. The actual failure-continuation
run attempts all 24 rows, injects the first fit-entry failure, executes 21 later
fits and retains two eligibility-only rows. All later 23 parsed rows match the
canonical result exactly apart from `runtime_seconds`; source stays unchanged.
An initial 13/14 audit compared Python tuples with saved JSON lists. That audit
and its comparator were preserved; JSON normalization corrected the audit
without repeating or changing the already completed fits. The
[contract receipt](../../studies/fixtures/finite-free-centre-v1/continuation-contracts.json)
and [whole-interval binding](../../studies/fixtures/finite-free-centre-v1/final-binding.json)
retain the scopes and hashes. Ten additional supplemental-audit CLI checks pass;
those use fake-audit flow controls and are not more optical recovery tests.

The frozen case named `contour-only-support` actually selects 24 **edge-band**
integer pixels with different intensities, not equal-valued points on one level
set. Its successful recovery does not contradict the equal-level degeneracy
described in the model guide. A normal case takes roughly 20 seconds in this
bounded research search on the reviewed machine; it is not a qualified default
latency for an interactive photo workflow.

## Captured-field integration diagnostic

The separate [complete actual-field diagnostic](../../studies/fixtures/finite-photo-intensity-v1/README.md)
retains **12 lanes** from the six custom-sheet capture cases: ten fits returned,
seven satisfy the declared completion flags, **one meets every geometry and
held-out target**, and two retain upstream refusals. It is not a successful
integration qualification. Its byte-identical plan, full result, original
runner text and input aliases are archived; the archive does not claim a
standalone replay command or a new production capture run.

The one all-target case uses the observed scalar spread on the small isotropic
field: centre error falls from `0.07545 mm` in the geometric seed to
`0.000942 mm`, with radius error `0.001823 mm` and held-out error `0.87264`
linear levels. Other cases remain part of the same evaluation. In particular,
moment-derived covariance can give small geometry errors while failing the
held-out intensity target; numerical completion and SPD covariance do not
establish model adequacy.

For both small-directional lanes, whole-sheet border pixels corrupt the
background and contour initializer. The observed search boxes exclude the true
part, and three basins remain unfinished. Their large errors must not be called
converged intrinsic model bias. The next bridge needs an observation region
derived from the already measured ring, fixed blur padding and an explicit
crop-to-global homography. That correction was not substituted into the frozen
v1 experiment. No automatic trace or CAD promotion follows from these results.

## Software regression

The full local Python invocation passes **862 tests**, with zero failures,
errors or skips, and runtime warnings treated as errors. Pytest time is
**226.60 seconds**; the wrapper records **227.40 seconds**. All **280 frozen
non-Markdown software inputs** and **22 built files** remain unchanged.
Independent study files have their own bindings and are excluded from that
software-only interval. The production frontend build and complete `make lint`
pass. The 62 focused controls are included in the full total.

| Evidence | SHA-256 |
| --- | --- |
| `backend/finite_centre_fit.py` | `e2019bcc8b5813c0957967b469baf44bbdd784f50855418852c2686cc48b9ab4` |
| `backend/finite_shape.py` | `9102f9e19127ce3666d2bf8744b0356bcc923060f2b142c8a2cbd50a363f5380` |
| `tests/test_finite_centre_fit.py` | `f94255dc8aab9c3db8196c3379ee2f025a1e7d83fca12a086084152c7eddceb4` |
| Full Python JUnit receipt | `2807ecd05ab2a024e6280373fc40c2973e3c1158cf45da8ee4aa9f91726ae5e9` |
| Full Python interval binding | `3180e0b28edb54ecba7971dd229f3a28e0b03781c29902242267e27fd267cfe7` |
| Complete 24-row study | `eb5e85ca199999915ffbc8b283fc98ba749d2460f9e44839af5ccb7f740e7087` |
| Supplemental aperture audit | `83c6964b2a2c77604606ba22891252123873dbff74eef04f770a8ca55777b405` |
| Main continuation/CLI receipt | `359e731eab5d8167a55f562056f8c57f729ababd3338a85b99cd859e60bde719` |
| Independent study interval binding | `a47b32878dd910eb5b628495d62eee78127059e548c45d4c24417da4bca7f4c4` |

The local binding and logs are under `.local/verification/`. No fresh browser
suite was run for these developer-only modules; PR #86's 74-scenario record
remains bound to its own source. Earlier development failures remain in their
original local receipts rather than being relabeled as successful runs.

## Scope of the evidence

Recovery results and adverse controls are reported separately from regression.
An observed field with only one level contour can be fitted with equal levels
at every geometry. Constant/low-contrast fields, incomplete support, wrong
covariance, gradients, response changes, neighboring material, pixel aperture,
active level bounds and numerical/work failures therefore remain explicit
controls. Missing covariance in actual captures is not supplied by a conditional
known-covariance experiment.

The [portable image-moment study](finite-moment-photo.md) retains its own 76
outcomes, including the missed nominal target and background sensitivity.
Moment-derived covariance is a proposal, not Gaussian calibration. Automatic
trace integration, bounded latency, acquisition-model adequacy, real-camera
metrology and print acceptance remain separate work.
