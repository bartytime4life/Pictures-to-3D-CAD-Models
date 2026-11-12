# Material gradients and local edge measurements

The [development study](validation/material-gradients.md) examines a production
assumption: the reference-sheet edge search fits a brightness slope on the paper,
while keeping the material-side level flat. That guard prevents a visible side
wall from being interpreted as a lighting gradient. A real material gradient is
another possible explanation of the same profile. The paper-only guard is
retained; the included symmetric-grid repair fixes normal-orientation sampling
without supplying a physical error bound.

## Repeat the study

From a configured checkout, choose a new output directory:

```bash
make material-gradient-study OUTPUT=.local/material-gradients
```

Or run `.venv/bin/python scripts/material_gradient_study.py --output NEW_DIRECTORY`.
The command refuses existing output directories. It saves `plan.json`, every
outcome in `cases.csv`, and `results.json` with summaries, runtime versions, Git
state and hashes of the runner, frozen plan and three production source files.
It returns zero when execution and the aperture-quadrature comparison complete
without failed measurements. Zero is not an accuracy or release decision.
Rejected low-contrast profiles are recorded outcomes, not execution failures.
Image-generation or resampling failures abort execution; an incomplete output
directory is not a completed study.

The [fixed plan](../studies/material-gradients-v1.json) has 576 world scenes:
12 lighting/wall conditions × 2 optical blur widths × 3 directions × 4 pixel
phases × 2 contrast polarities. Four processing stages, two slope treatments
and both normal signs produce 9,216 rows. Reversing the normal tests the
`paper_side` implementation; it is not independent scene replication.
The preliminary gradient probe informed this plan, so these are development
cases, not an unseen evaluation population.

## Independent image formation

Let `t` be signed distance in pixels, positive toward paper. Before blur the
material is `M + m t` for `t < 0` and paper is `P + p t` for `t >= 0`.
For a Gaussian of width `s`, their infinite-affine convolution is

```text
z = t/s
I(t) = M + (P-M) Φ(z) + m t + (p-m) [t Φ(z) + s φ(z)]
I(0) = (M+P)/2 + (p-m) s / sqrt(2π)
```

The oracle uses standard-library `erfc` for `Φ`, independently of the production
Gaussian approximation and synthetic-photo renderer. Its source slopes become
constant outside `[-12s,12s]`, keeping all source levels in `[0,255]`. The exact
tail corrections use truncated Gaussian first moments. Equivalently, an affine
segment `a + b x` on `[l,h]` contributes

```text
(a + b t) [Φ((h-t)/s) - Φ((l-t)/s)]
  + b s [φ((l-t)/s) - φ((h-t)/s)]
```

Flat-wall controls replace a band `[-w,0]` on the material side. Their extra
response is `(W-M)[Φ((t+w)/s)-Φ(t/s)]`. Unit-square pixel apertures are integrated
with 6×6 Gauss–Legendre nodes and compared against 12×12 nodes for every scene.
Agreement of these floating-point calculations is a numerical check, not a
rigorous interval enclosure or a calibrated sensor-response model.

## What each processing stage tests

| Stage | Input and processing | Blur supplied to the crossing search |
| --- | --- | --- |
| `point_known_sigma` | Exact blurred values at pixel centres, then actual bilinear profile sampling | Supplied optical width |
| `aperture_known_sigma` | Uniform pixel-aperture means, then actual bilinear profile sampling | Supplied optical width; finite aperture is deliberately not Gaussianized |
| `aperture_resampled_estimated_sigma` | Aperture means, actual Keys rectification with a fixed translation, float32 output, actual 0.7-pixel discrete Gaussian smoothing | Actual `edge_sigma` estimate |
| `srgb8_aperture_resampled_estimated_sigma` | Independent sRGB encoding and 8-bit rounding, actual linear-luminance decoding, then the preceding rectification/smoothing chain | Actual `edge_sigma` estimate |

The first stage is a sampled-array control, not a direct continuum crossing.
The second-to-third change combines resampling, smoothing and blur estimation;
it cannot isolate any one of their causal effects. The measured width in the
last two stages is not a recovered pre-aperture optical PSF.

Each row measures one supplied straight edge and normal, starting 0.1 pixels
toward paper. The actual `half_level_search` uses the production step, contrast
gate and search-window rule. Ring smoothing is disabled because this is one
profile, not a closed boundary. The two treatments are the production
paper-only slope guard and an explicit two-affine **ablation** with
`paper_side=None`. The latter is not a proposed automatic correction.
No sheet detection, segmentation, pose estimation, closed-ring smoothing,
wall refinement, curve fitting or CAD export is exercised.

## Symmetric profile sampling

The search now uses `t_j = j × step` for integer `j` from `-N` to `N`, where
`N = ceil(reach/step)`. This includes the supplied point exactly and covers the
requested reach, extending each end by less than one step. The previous grid
started at `-reach`; when `reach/step` was noninteger, reversing a normal sampled
different physical positions. The [before/after record](validation/material-gradients.md)
and independent noninteger-window regressions check the resulting fix.

For a fixed single-crossing profile, reversing the normal and `paper_side`
reflects the paired samples, plateau masks and crossing target. The physical
crossing should therefore agree to floating-point precision. This is not a
general guarantee for profiles with several competing crossings. The subsequent
[nearest-crossing repair](edge-crossings.md) ranks actual interpolated distances
and leaves nearest unresolved contacts or equal minima unlocalized. The grid repair does not
infer missing light-field, wall or PSF parameters.

## Why global brightness calibration is not enough

For fixed accepted samples, a positive affine intensity transform `I -> a I+b`
transforms medians, fitted lines and the crossing target by the same rule.
The interpolated crossing fraction therefore cancels `a` and `b`. The normalized
25–75% rise used by `edge_sigma` has the same property. Global gain/offset cannot
remove a spatial material-gradient bias in these fixed-profile equations.
The encoded contrast gate, clipping, quantization, segmentation and channel
selection need separate treatment; they need not preserve acceptance under
the same transform.

A first-order explanation of the guard's displacement uses its material-end
median near `-3.75s`. For material slope `m`, flat paper and contrast `P-M`,

```text
displacement ≈ m s² [1/sqrt(2π) - 1.875]
               / [(P-M)/sqrt(2π) + m s/2]
```

This is an explanatory approximation to a local continuous profile. It is not
an exact bound for the actual fitted windows, tail removal and sampled crossing.

## Why fitting both slopes is not yet a fix

For flat top, wall and paper levels, a narrow wall contributes, to first order,
`(W-M)(w/s) φ(t/s)`. An edge displacement has the same first-order shape. The
equivalent displacement is `-(W-M)w/(P-M)`. Distinguishing the wall from edge
motion requires higher-order information, and allowing material slopes can
also absorb its shoulder. A better gradient-only result does not establish
correct wall geometry.

Wall rows report the pre-refinement crossing relative to the supplied outer
silhouette. They do not test the later wall correction or identify a final
top-face error. All observed offsets remain fixture errors in pixels; no
population rate, physical uncertainty or fabrication tolerance follows from
them. See the [reference-sheet assumptions](reference-sheet.md) and the
[engineering verification model](engineering-model.md).
