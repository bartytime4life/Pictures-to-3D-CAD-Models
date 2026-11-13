# Finite-material normal-angle sensitivity

This experimental developer operator differentiates a supplied finite circular segment under
a fixed homography and Gaussian observation model. It does not fit an angle,
infer camera optics, change a traced boundary or run through the HTTP workflow.
Its numerical qualification is separate from the original
[failed residual-information study](validation/finite-residual-information.md).
Its [complete qualification](validation/finite-normal-derivative.md) retains one
panel-budget unknown and an independently observed error-estimation limitation
on a compressed perspective map. A resolved flag is not an accuracy guarantee.

The later [determinant and global-error correction](finite-normal-error-control.md)
is implemented in this source. Its [417-scene study](validation/finite-normal-error-control.md)
passes both frozen comparisons and retains the original V1 failure. High-precision
checks confirm the two original candidate controls, while exposing a limit in
the independent oracle's error estimate. The API and statuses below are unchanged.

## Quantity and coordinates

The material is `disc(C,R) intersect {n dot (x-C) <= R*f}`. Increasing angle
means `dn/dphi=J*n`, where `J=[[0,-1],[1,0]]`, with `C`, `R` and `f` fixed.
The result is a **signed probability derivative per source-plane radian**.
It can be negative or exceed one in magnitude. For intensity
`a+(b-a)*P`, multiply by the signed contrast `b-a` once.

`pixels_xy` contains integer observation indices; their centres are index plus
0.5. `centre` and `radius` use geometry-plane units. `homography` maps that
plane to the queried observation frame, and `psf_covariance` is a fixed SPD
Gaussian covariance in that frame, in squared pixel units. A crop needs the
corresponding translated homography. An empirical rectified covariance is not
a calibrated raw-camera PSF. Pixel-area integration, nonlinear lens maps,
resampling kernels, spatially varying blur and thickness are outside this model.

## Python contract

Import `circular_segment_normal_derivative` from `backend.finite_normal`.
Its positional arguments are `pixels_xy`, `radius`, `chord_fraction`; keywords
are `centre`, `normal=(1,0)`, `sensor_shape`, `homography`, `psf_covariance`,
`probability_tolerance=1e-8`, `max_panels=4096`, and
`max_evaluations=2_000_000`.

Input domains match the existing
[finite-segment operators](finite-shape-inverse.md#developer-contract-and-interpretation):
1–2048 unique in-frame integer queries; finite, nonboolean geometry;
`R` in `[1e-3,1e6]`; `f` in `[-0.999,0.999]`; centre components within
`[-1e9,1e9]`; and a unit supplied normal. Covariance must be exactly symmetric
and positive definite, without repair. The nonsingular homography must keep the
**whole finite material** in one supported projective chart. A valid chord alone
is insufficient. Reflection uses the absolute area Jacobian; it does not reverse
the source-angle derivative sign. Invalid supplied geometry or controls raise
`ValueError`, rather than returning a resolved value.

The immutable `NormalDerivative` result retains every query in input order:

| Field | Meaning |
| --- | --- |
| `derivatives`, `statuses`, `estimated_errors` | Per-query signed derivative, status and absolute numerical error estimate; unresolved values/errors are `None` |
| `query_methods` | Supplied-map classification and attempted closed-form/fallback route; `not_attempted` if no analytic budget remains |
| `query_evaluations`, `query_panels` | Per-query charged work, including discarded analytic work and attempted fallback nodes |
| `evaluations`, `panels` | Sums across all retained queries |
| `chart_margin`, `reflected` | Supported chart and map-orientation metadata |
| `method`, `quadrature_certified` | `finite_chord_shape` and `False`; this is not a certified enclosure or physical uncertainty |

`resolved` requires finite output and an estimated error within the requested
tolerance. `work_limit` retains exhausted-work queries; `numerical` retains
represented unsupported arithmetic. Unexpected internal programming errors
propagate. A resolved result establishes neither angle identifiability nor
physical adequacy of the supplied optics.

## Small supplied-model example

Run from the repository root after [workbench setup](development.md). These
four fixed pixel indices and supplied geometry illustrate the API; they are
synthetic values, not measurements or a new qualification dataset.

```python
from backend.finite_normal import circular_segment_normal_derivative

pixels = [(12, 12), (18, 12), (12, 18), (20, 20)]
result = circular_segment_normal_derivative(
    pixels, 6.5, 0.25,
    centre=(16.0, 16.0),
    normal=(1.0, 0.0),
    sensor_shape=(32, 32),
    homography=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    psf_covariance=((1.0, 0.2), (0.2, 2.0)),
)
for pixel, status, value, error in zip(
    pixels, result.statuses, result.derivatives, result.estimated_errors
):
    print(pixel, status, value, error)
```

Read each status before using its value. An unknown retains `None`; it must not
be treated as zero or dropped from the query population. Even `resolved` uses
an engineering error estimate that the compressed-map control has shown can
underestimate actual numerical error. The example does not estimate a normal,
change covariance or run the inverse fitter.

## Mathematics and numerical resolution

The circular boundary contributes zero normal velocity. With `t=J*n`,
`X(s)=C+R*f*n+s*t`, and `ell=R*sqrt(1-f²)`, the chord velocity is `-s`:

```text
dP/dphi = - integral[-ell,ell] s * G_Sigma(p-H(X(s))) * abs(det DH(X(s))) ds.
```

For a positive projective chart, write `w(X(s))=w0+s*w1` and `k=w1/w0`.
The substitution `z=s/(1+k*s)` makes the mapped chord a straight affine
parameterization and reduces the signed integral to a Gaussian first moment.
The [derivation](finite-residual-information.md#finite-chord-shape-derivative-a-derived-proposal)
states its normalization and asymmetric projective limits.

Tail-safe normal-mass differences and density differences reduce cancellation.
If the estimated arithmetic allowance is too large or the closed form is
unrepresentable, the operator attempts original-source-chord quadrature.
It never substitutes an angular finite difference. Non-tail panels must resolve
mapped travel, Gaussian exponent variation and projective denominator ratio.
The last guard matters when mapped travel is tiny but the area Jacobian has a
sharp endpoint concentration. Tails require an absolute contribution estimate;
two integration orders returning zero are insufficient by themselves.

## Resource limits and interpretation

Tolerance accepts `[1e-12,1e-3]`. `max_panels` accepts 1–8192 **per query**;
`max_evaluations` accepts 1–20,000,000 **across the batch**, in input order.
Each analytic attempt charges one panel and two standardized endpoint work
units. Fallback charges two endpoint units per inspected panel plus each
attempted 12/24-rule node. Discarded work remains charged. These are bounded
algorithm work units, not a latency or hardware benchmark.

An unresolved query does not erase later affordable queries. Small budgets can
therefore make query order matter. Check statuses and per-query work rather
than treating an overall count or a retained partial result as complete.
The existing probability result and four-column centre/radius/fraction
Jacobian schemas remain separate from this new derivative.

The [prospective matrix](../studies/finite-normal-derivative-v1.json) and
[compressed-chart supplement](../studies/finite-normal-derivative-compressed-chart-v1.json)
were frozen before any new operator or oracle evaluation. They specify
337 scenes, 3,886 queries, independent source-chord quadrature and supplemental
positive-area angle differences. Their results must be assessed separately
from unit contracts and from later archived-data or physical-capture work.
