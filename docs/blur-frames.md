# Blur after thickness correction: coordinate frames

[Documentation index](README.md) · [Reference-sheet tracing](reference-sheet.md) · [Corner model](anisotropic-corners.md)

Thickness correction can move measured points into a different coordinate
frame. Their blur widths must move with them. This change transports a known
uniform point scale through the existing free-circle, free-arc, slot-cap and
line-refitting calculations. It does not infer a new blur model or add a
workbench control.

Uniform transport and mixed support have different contracts. Mixed free curves,
caps and scalar corner fits retain explicit geometry approximations; a mixed
nonparallel corner with supplied covariance remains withheld. The
[validation record](validation/curve-blur-frames.md) separates model checks,
integration outcomes and retained failed experiments.

## One homothety, one transported Gaussian

The reference-sheet pipeline estimates blur in its rectified measurement field
before top-face parallax correction. A point formed by the top edge is mapped
about the camera nadir `N` by

```text
T(p) = N + k (p - N),    k = (camera_height - thickness) / camera_height > 0.
```

The corresponding length and covariance transformations are

```text
c' = T(c),    r' = k r,    sigma' = k sigma,    S' = k² S.
```

Unmoved bottom-edge points have `k = 1`. The scale is a known result of the
selected geometric correction, conditional on its camera/height assumptions;
it is not inferred from a radius residual. The matrix `S` remains an empirical
rectified-image Gaussian covariance, rather than a calibrated optical PSF in
the original camera frame.

For a shape `K` convolved with a Gaussian, an exact common homothety gives the
model identity

```text
U[T(K), k² S](T(p)) = U[K, S](p).
```

Both shape and blur must transform. Correcting the geometry while leaving the
blur width unchanged applies a different model. This coordinate identity does
not establish that the photographed object, processing response or blur follows
the assumed Gaussian model.

## Homogeneity of the existing curve approximations

The free circular-edge radius series is

```text
C(r, sigma) = r + sigma²/(2r) - sigma⁴/(24r³).
C(k r, k sigma) = k C(r, sigma).
```

The slot-cap calculation uses the forward circular shrink series

```text
B(R, sigma) = sigma²/(2R) + 5 sigma⁴/(24R³),
B(k R, k sigma) = k B(R, sigma).
```

For a directional blur, the cap's leading shrink along a unit direction `u` is

```text
D(R, S, u) = det(S) / (2 R u.T S u),
D(k R, k² S, u) = k D(R, S, u).
```

Its inherited isotropic higher-order term is homogeneous in the same way.
The slot radius still comes from the fitted side spacing; the blur model places
its centre along the slot. Uniform transport makes these calculations use
consistent units. It does not make the truncated series exact at small radii,
remove the directional approximation, or solve finite interactions between
nearby boundaries.

Free arcs and circles still take a scalar width. When the directional
estimator supplies a covariance, their inherited scalar summary is
`sigma = det(S)**0.25`. Under uniform scaling this summary becomes `k sigma`,
but it still discards orientation at a partial free arc. The separate
[nonparallel-corner model](anisotropic-corners.md) uses the full supplied
covariance when available.

## Which point scales belong to a primitive?

`reference.trace_on_sheet` carries a positive scale for every corrected measured
point. Uniformity means the stored scales are exactly equal on the relevant
support. The implementation does not average, cluster or tolerance-match
different values into one Gaussian frame.

| Calculation | Support used to choose its frame |
| --- | --- |
| Free circle correction | The complete measured ring |
| Free arc correction | The arc's own inclusive cyclic point span |
| Constrained fillet or slot cap | The combined context from the preceding line's start through the following line's end |
| Straight-line refit window | That line's own inclusive cyclic point span |

An inclusive span can wrap past the end of the ring. Its point indices and
scale vector must address the same original measured ring. Changing scales
outside a free arc's support does not make that arc mixed; changing a neighboring
line inside a cap's fitting context can make the cap mixed even when its arc
points alone share one scale. These are support rules, not a new estimate of
which points were physically formed by a top or bottom surface.

## Line windows and numerical ties

The reference caller starts with a tangent-region exclusion margin of three
times the scalar spread, or three times the largest principal spread when a
covariance is available. `refit_lines` multiplies that margin by the **largest
point scale on each line's support**. For a uniform map this is the common
homothety scale. For mixed scales it is a conservative choice of exclusion
window, without assigning one effective Gaussian to the line or its neighbors.

For a positive margin, points must lie numerically beyond the exclusion window.
A small tie guard uses

```text
16 eps (abs(along) + abs(tangent) + local_margin),
```

where `eps` is binary64 machine epsilon and all terms are lengths in the current
working frame. The guard is intended to keep a rounded window-boundary tie from
changing which whole sample is accepted after a coordinate change. It is an
engineering arithmetic guard, not a rigorous
floating-point error enclosure or an added physical allowance. The inherited
minimum-support fallback still uses the full line span when too few points
survive exclusion.

## Mixed support: approximation or withheld radius

A support containing both `k = 1` and a contracted top-face scale is not one
common homothety. No single transported stationary covariance follows from
those point labels. The implementation does not invent an average `k` or `S`
or assign calibrated uncertainty to the mixture.

| Mixed support | Policy |
| --- | --- |
| Free circle or free arc | Retain the legacy scalar-series approximation using the original pre-map spread, with a mixed-frame marker |
| Slot cap, scalar or directional | Retain the legacy cap-placement approximation using the original pre-map blur values, with a mixed-frame marker |
| Nonparallel corner, scalar blur only | Retain the legacy geometry approximation with a mixed-frame marker and an undetermined radius; do not claim a sharp-resolution bound or delete the corner as sharp |
| Nonparallel corner with supplied covariance | Withhold the unsupported common-Gaussian radius and use the existing retained-boundary recovery or refusal |

The mixed scalar-corner path explicitly sets its internal `r_sd` radius-spread
diagnostic to infinite, rather than presenting the local scalar model's finite spread as an
identified radius. It does not emit a sharp-bound claim from that fit. This
preserves an inspectable geometric approximation without asserting that one
Gaussian describes the piecewise point map.

If that legacy scalar fit proposes a zero, negative or nonfinite radius, it does
not become a sharp deletion or degenerate arc. A positive finite initial
geometric arc with finite centre is retained at this stage and marked
`blur_correction_withheld`, so the generic blur-correction pass does not alter
it again. If no such initial arc is available, the fit is marked unresolved.
This guard does not resolve the radius or change the later design-intent and
profile-validity checks.

If such a marked curve survives into the described fitted geometry, reference
notes and warnings say:

> Some curved edges use measurements from both the top and bottom of the part.
> Their blur correction is approximate; measure important radii.

That notice concerns emitted curves. A candidate rejected before final assembly
does not generate a mixed-curve warning about geometry that was not used. Other
radius-resolution or retained-boundary notices may still apply.

For the withheld supplied-covariance path, the
[existing recovery policy](anisotropic-corners.md#when-the-corrected-source-ring-is-invalid)
remains: retain a valid traced boundary, or use an eligible frozen initial fit
as a line-only polygon after the existing bounded checks; refuse the profile
when those checks fail. No new polygon cleanup, component selection or topology
inference is introduced by blur-frame transport. The rejected cleanup
experiments remain recorded separately from production behavior.

## What these checks can establish

Uniform frame-commutation checks compare a calculation on a transformed input
with the transformed result of the same approximation. They can expose a stale
blur width, a wrong support span or a window-selection inconsistency. They do
not, by themselves, compare the fitted radius with a physical part or establish
the approximation's finite-shape accuracy.

The [predeclared study plan](../studies/curve-blur-frames-v1.json) separates
independent finite Gaussian observations, uniform transport checks, mixed-frame
controls and adverse cases where no half-level contour exists. Results and
integrated regressions are tracked separately in the
[validation record](validation/curve-blur-frames.md), with source binding and
retained development failures. Existing scalar and photograph tables retain
their original conditions.

Important radii still need independent measurements. Empirical blur estimation,
camera height, wall brightness, tone response, non-Gaussian blur, snapping,
equalization and final join/export geometry retain their separate limitations.
The common 5% blur-scale sensitivity and fixed pixel error allowances are
heuristics; transport consistency does not qualify their coverage or make all
thresholds and radius diagnostics scale-invariant.
