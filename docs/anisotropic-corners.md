# Directional Gaussian blur at a fitted corner

[Documentation index](README.md) · [Reference-sheet method](reference-sheet.md) · [Blur frames](blur-frames.md)

A reference-sheet trace can measure different edge spreads in different
directions. For a fillet between two nonparallel lines, replacing that blur by
one average width can change the fitted radius even when the local residual is
small. The corner model now uses the supplied two-dimensional Gaussian
covariance directly. This changes the existing reference-sheet fitting path;
there is no additional workbench control or camera-calibration step.

This guide describes the model, refusal paths and a source-bound independent
conditional study. The study does not establish camera accuracy or a physical
radius bound. The [validation record](validation/anisotropic-corners.md)
separates integrated regressions from the local model checks.

## What covariance means here

For a unit edge normal `n`, a Gaussian covariance `S` predicts a directional
variance `sigma_n² = n.T @ S @ n`. The tracer estimates `S` from clean edge
profiles with the orientation-support, numerical-rank and per-direction
adequacy checks in [reference-sheet tracing, §3](reference-sheet.md#3-segmentation-and-sub-pixel-edges).
Passing those checks supports that empirical model on the sampled profiles; it
does not establish that a physical camera has a spatially constant Gaussian PSF.

The matrix is in **rectified measurement pixels squared**. It describes spreads
after rectification and the measurement pipeline's resampling and smoothing.
It is not a raw sensor-space optical covariance. The scalar summary
`sigma = det(S)**0.25` is the geometric mean of the principal standard
deviations; it cannot preserve the blur's orientation at a nonparallel corner.
No additional covariance is inferred for corner fitting when the matrix is absent.
The tracer can still use per-direction measured edge widths for a two-direction
part and construct a matching covariance solely to blur its paper-shadow model.
That construction does not identify the missing covariance cross term or supply
the matrix to this corner model; corner and curve corrections keep one width.
See [two-direction edge tracing](reference-sheet.md#3-segmentation-and-sub-pixel-edges).

The public numerical helper has this call outline with caller-supplied geometry:

```python
from backend.fitting import corner_level

# points, centre and radius use one common coordinate frame;
# covariance uses that frame's squared units.
levels = corner_level(
    points, centre, radius, start, sweep, sigma,
    covariance=covariance,
)
```

`points` is an array of query coordinates; `start` and `sweep` are angles in
radians, with `0 < sweep < pi`. `radius` may be zero. With a covariance, the
forward calculation uses the matrix; callers should keep the inherited scalar
summary consistent with it when using the fitting path. Without a covariance,
the helper retains the scalar Gaussian model.

## Whiten the blur and transform the geometry

The local shape is a circular fillet plus two tangent half-lines extending
away from it. It is star-shaped from the fillet centre `c`. Write its physical
radial reach at angle `phi` as `R(phi)`: the circle radius across the arc, the
appropriate tangent-line intersection beyond its ends, and infinity in the
unbounded opening.

Factor the supplied positive-definite matrix as `S = L @ L.T`. Under
`z = solve(L, x - c)`, the Gaussian becomes isotropic with unit covariance.
The geometry must transform with it. A unit whitened ray `e(theta)` maps back
to the physical vector `L @ e(theta)`, so its whitened reach is

```text
R_whitened(theta) = R(arg(L @ e(theta))) / norm(L @ e(theta)).
```

Transition rays at the arc/tangent joins are also transformed. Keeping a
circular reach in whitened coordinates would instead change the shape: a
physical circle generally becomes an ellipse. The implementation integrates
the radial Gaussian analytically and the remaining angle numerically. Gaussian
standardization and ray integration are established principles; see
[Das and Geisler (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8419883/).
The star-centred reach construction above is this implementation's own recipe,
rather than a use of the authors' software.

## Numerical acceptance and radius interpretation

The covariance branch requires a finite symmetric positive-definite `2 × 2`
matrix with enough numerical separation from singularity. It compares angular
quadratures with successively doubled panel counts, accepting a maximum level
change of `5e-8`. Panel and node budgets are bounded. Unsupported input,
unresolved convergence, nonfinite arithmetic or a failed local radius refinement
returns a failure to the caller instead of substituting an isotropic fit.

That convergence check is an estimated numerical agreement between resolutions,
not a certified enclosure. The existing normal-tail approximation and
nine-standard-deviation angular truncation remain. Nor does convergence prove
that the local unbounded corner describes a finite part with nearby edges,
holes, walls, shadow or a different response curve.

The radius fit keeps the centre constrained by its two tangent lines and uses
the covariance-aware half-level model. It requires a represented cost decrease
and a local stopping condition; exhausting its iteration or line-search budget
does not count as convergence. Accepted modelled fillets are excluded from the
later generic curvature correction, so that correction is not applied twice.

The reported radius spread still combines sampled residual noise with assumed
systematic terms: a `0.03 px` line-position scale and a **5% common blur-scale
heuristic**. For covariance `S`, that last sensitivity scales all principal
standard deviations together, equivalently `S -> k² S`. It does not estimate
uncertainty in the covariance entries, anisotropy ratio or orientation, and is
not a confidence interval with calibrated coverage.

A corner classified as sharp carries a conditional model radius-resolution
estimate. Before bisection, the covariance path must actually find a residual
crossing. A search cap is not an upper bound; failure to find a crossing leaves
the fit unresolved. A finite estimate therefore remains conditional on the
selected geometry, supplied covariance and heuristic noise floor, rather than
a physical upper bound on an unobserved rounding.

## Thickness correction changes the covariance frame

Covariance is measured before the piecewise top-face parallax map. For a
top-face homothety with linear scale `k = (camera_height - thickness) /
camera_height`, a corner's geometry scales by `k` and its covariance must scale
by `k²`. Unmoved bottom-edge points keep `k = 1`.

The trace carries this scale for each point. A nonparallel corner with supplied
covariance whose support shares one scale uses the corresponding `k² S`. When
its support mixes top- and bottom-edge maps, one stationary covariance cannot
represent that piecewise map. The supplied-covariance corner fit is then unresolved. The caller normally keeps
the **affected boundary ring as a traced outline**, while other supported rings
remain eligible for analytic fitting. Numerical covariance-fit failures use the
same recovery. There is no accepted scalar replacement for a failed covariance
corner fit.

The scalar-only mixed-corner path has a distinct, explicitly approximate
contract: retain legacy geometry with a mixed-frame warning, infinite internal
radius-spread diagnostic, and no sharp-bound or sharp-deletion claim. An
unusable scalar-model radius keeps an eligible positive initial geometric arc
without another generic blur correction, or becomes unresolved if no such arc
is available. This does not supply a common Gaussian frame or identified radius.
[Blur frames](blur-frames.md#mixed-support-approximation-or-withheld-radius)
also describes uniform transport for free curves and slot caps. The
source-bound study below retains its original supplied-covariance conditions.

### When the corrected source ring is invalid

The piecewise thickness map can make the corrected measured boundary cross
itself. In that case, retaining those points does not produce a valid CAD
profile. One narrow recovery is allowed: an already accepted initial geometric
fit, frozen before snapping or blur reconstruction, may supply a nearby
**line-only polygon**. This is an approximation of the source boundary, not an
accepted Gaussian radius fit.

The frozen candidate is sampled into lines and must form one valid,
positive-area ring, stay within the `1900`-vertex cap, and pass bidirectional
whole-boundary containment: each complete closed boundary must lie within the
other's existing geometric-fit tolerance tube. In rectified pixels that
tolerance is `max(0.03 * ppm, 0.15 * sigma)`. Arc sampling targets one sixteenth
of that tolerance; the final containment checks on the resulting line boundary
remain decisive. There is no outward allowance beyond the fitting tolerance.
This separate check does not enlarge the ordinary
`0.05 mm` standard polyline-detail tolerance. It uses no generic polygon-repair
operator or component deletion, and final profile validation still applies.
The invalid source has no accepted polygon topology: tube proximity does not
certify which topology was intended. If the frozen candidate is absent or
fails any check, the normal invalid-profile refusal remains.

The reference notes and warnings distinguish the nearby polygonal recovery
from a retained trace and state that its corner radius remains undetermined.
Both paths omit the rejected radius from later blur correction and
radius-equalization claims. Inspect the retained outline and independently
measure important radii before fabrication. A valid nearby polygon establishes
neither physical accuracy nor that a self-crossing trace had one intended
topology.

## Remaining scope

- General free arcs and circles still use the existing scalar-summary curvature
  series, rather than this covariance-aware unbounded-corner forward model.
- Near-parallel slot end caps retain their existing constrained geometry and
  first-order directional tip correction; they are a separate approximation.
- Line snapping and repeated-radius equalization remain design-intent choices.
  A modelled corner fit does not independently verify those choices or the
  final exported boundary.
- A covariance inferred from the current part's edge spreads is not independent
  optical calibration. Unknown tone mapping, non-Gaussian or spatially varying
  blur, finite-shape interactions and physical measurement error remain outside
  this change.

## Independent conditional evidence

The [predeclared 16-case study](../studies/corner-anisotropy-v1.json) uses a
separate conditional positive-area Gaussian CDF integral, rather than the
production angular/radial integration, to construct half-level observations.
Its [runner](../studies/verification/corner-anisotropy-v1.py) and
[complete result](../studies/results/corner-anisotropy-v1.json) retain every row,
the scalar comparisons and before/after source hashes. All 48 predeclared checks
passed, with no execution errors and unchanged bound source files.

These are exact-input tests of the local infinite-corner model with supplied
covariance and known tangent lines. The numerical seed is the true radius
except in the sharp/small cases, which use half the scalar spread. Segmentation,
line refitting, finite neighbouring boundaries and physical calibration are
outside this study. Its quadrature comparisons are engineering evidence,
rather than rigorous probability enclosures.

Among the 12 predeclared radius controls, the maximum covariance-model radius
error was `1.03053e-7 px`. For the right-angle example with true radius `4 px`
and `S = diag(0.36, 4) px²`, the scalar-summary fit returned `4.541239481 px`,
with heuristic spread `0.10454 px` and residual RMS `0.0374 px`. The
covariance-aware result was `4.000000025 px`; its forward levels at the true
geometry agreed with the independent integral within `1.1e-8`.

The four additional adverse cases remain part of the result:

| Declared case | Covariance-path result | Interpretation |
| --- | --- | --- |
| Sharp, true `R = 0 px` | No exact fit returned | Unresolved; no finite radius bound is manufactured |
| Small, true `R = 0.6 px` | Fitted `R ≈ 0.600000605 px`; sharp-resolution estimate `1.18178 px` | Conditional sharp classification, despite a numerically close fitted radius |
| Transition, true `R = 1.5 px` | Fitted `R ≈ 1.500000037 px`; no sharp bound | A returned fit with heuristic radius diagnostics, not a physical resolution guarantee |
| Weak 30° arc, true `R = 4 px` | Fitted `R ≈ 4.000000981 px`; sharp-resolution estimate `7.05967 px` | Weak radius information; conditional sharp classification |

Passing all study checks therefore does not mean all 16 radii were resolved.
The reported spreads and sharp-resolution estimates were not independently
qualified as uncertainty bounds. These cases supply no population rate or
camera qualification. Historical scalar and photo tables in the reference-sheet
guide retain their original conditions.
