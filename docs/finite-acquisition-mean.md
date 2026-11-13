# Source-cell acquisition means

The [previous forward study](finite-acquisition-operator.md) found that matching
Gaussian second moments did not reproduce the supplied acquisition chain, even
at the true geometry. This candidate replaces that approximation with two
explicit developer operators: analytic finite-material cell coverage, followed
by declared discrete acquisition stages. It has no tracing, fitting or HTTP
integration in the main-based runtime documented here. The
[separate local recovery prototype](finite-acquisition-recovery.md) calls these
operators, but is not included in this source or exposed through the workbench.
Numerical qualification follows the
[prospective plan](../studies/finite-acquisition-mean-v1.json). The
[complete result](validation/finite-acquisition-mean.md) retains all 128
comparisons, failed first controls and subsequent resource-accounting repair.
These remain experimental operators.

## Integrate the material over a cell

`backend.finite_aperture.segment_cell_coverage` models

```text
K = {x: ||x-c|| <= R and n·(x-c) <= f*R},
c[i,j] = area(K intersect source_cell[i,j]) / area(source_cell[i,j]).
```

The source grid declares the centre of cell `(0,0)`, pitch, rows and columns.
The archived unit-pitch source starts at `(-16,-16)`; each cell extends half a
pitch from its centre. This distinguishes area averages from point samples and
prevents an implicit half-pixel shift.

The supplied normal must have length one within `64*2**-52`. The implementation
divides its components by the computed length, then uses those represented
binary64 components in exact rational predicates. Their exact squared norm
need not be exactly one. The equations above describe that stored half-plane;
they do not establish a qualified normal-angle derivative.

The independent implementation first clips the cell rectangle by the chord
half-plane. For each resulting polygon edge, it splits at its disk crossings.
An inside segment contributes half its endpoint cross product. An outside
segment contributes `R²*atan2(cross(a,b),dot(a,b))/2`, in disk-centred
coordinates. Summing these signed terms gives disk/polygon overlap without
polygonizing the circular arc. This follows by applying Green's theorem to a
field whose curl is one inside the disk and zero outside. Floating area
evaluation remains an engineering calculation, not certified interval geometry.

Primary work on [disk/grid overlap](https://arxiv.org/abs/1812.10515) also treats
pixel overlap analytically. This implementation derives its own clipped-cell
boundary integral rather than implementing that paper's case tally.
[Unser's sampling review](https://bigwww.epfl.ch/publications/unser0001/)
provides the broader distinction between acquisition prefilters and
reconstruction operators; neither reference qualifies this software.

## Preserve each declared acquisition stage

`backend.finite_acquisition.acquisition_mean` accepts material fractions,
supplied linear `[background,material]` levels, actual finite optical/post
kernels, an output shape, a known affine map and integer output queries. It
returns intensities and immutable stage arrays. The map takes output geometric
pixel centres `(x+.5,y+.5)` directly to source array-index coordinates.

The declared chain is:

```text
cell fractions -> float32 storage -> brightness mix -> float32 source light
  -> explicit optical correlation -> optional grayscale sRGB8 encode/decode
  -> signed Keys resampling -> float32 -> explicit post correlation.
```

The kernels retain their supplied coefficients; no covariance or Gaussian
substitute is inferred. Correlation uses reflected borders excluding the edge
sample (`REFLECT_101`). Keys uses replicated source borders, float64 signed
weights and one output float32 cast. Its intensities can exceed the physical
plateau range and are not clamped. The post kernel is explicit; using a saved
7×7 kernel does not assert bit equality with OpenCV's automatic Gaussian blur.

The optional encoding branch is grayscale sRGB on a 0–255 scale, clipped and
rounded to even 8-bit codes, then decoded with a float32 lookup and sequential
Rec.709 channel accumulation. It models the specified synthetic encoding,
not unknown camera processing. It does not write a PNG container. The prior
archive separately verifies its PNG's lossless code preservation.

Float32 casts make the literal executable map locally constant between rounding
transitions; its changes at those transitions need not be differentiable. PNG
encoding adds further code transitions. The existing Gaussian Jacobian and
exact two-level variable projection cannot be attached unchanged. A tiny
analytic/polygon area difference may cross an encoding bin;
quantization differences must be retained rather than hidden by an inflated
linear tessellation allowance.

For a separately declared, unrounded linear operator `A`, brightness would have
columns `[A*1 - A*c, A*c]`. They sum to the computed `A*1`; substituting
`[1-A*c, A*c]` requires exact constant preservation. The accepted finite kernels
retain their raw coefficients rather than being renormalized. This algebra
does not provide an inverse or a derivative of the rounded API.

## Small executable example

Run this Python block from the repository root after workbench setup. It builds
a supplied semicircle on a 3×3 grid and queries three output pixels. The affine
translation `-0.5` converts output geometric centres to matching source indices;
`origin` remains a separate plane-coordinate quantity.

```python
from backend.finite_aperture import segment_cell_coverage
from backend.finite_acquisition import acquisition_mean

coverage = segment_cell_coverage(
    centre=(1.0, 1.0), radius=1.0, fraction=0.0, normal=(1.0, 0.0),
    shape=(3, 3), origin=(0.0, 0.0), pitch=1.0,
)
prediction = acquisition_mean(
    coverage,
    levels=(240.0, 30.0),
    optical_kernel=[[1.0]],
    output_shape=(3, 3),
    output_to_source_index=[[1.0, 0.0, -0.5], [0.0, 1.0, -0.5]],
    post_kernel=[[1.0]],
    queries=[[0, 0], [1, 1], [2, 2]],
)
print(prediction.statuses)
print(prediction.intensities)
```

The three statuses are `resolved`. This demonstrates the call and coordinate
contract; its supplied parameters do not constitute calibration or recovery.
Set `srgb8=True` to use the declared encoding branch. Use the
[saved-data workflow](../studies/fixtures/finite-acquisition-mean-v1/README.md#verify-saved-data-without-a-model-call)
to inspect the complete published experiment without evaluating a model.

## Refusals, provenance and work

| Input | Accepted contract |
| --- | --- |
| Geometry | Finite coordinates with absolute value at most `1e9`; radius and grid pitch in `[1e-6,1e6]`; chord fraction in `[-1,1]`; complete grid boundaries within the coordinate limit |
| Rectangle area | Ordered `(x0,y0,x1,y1)` bounds; each side positive and at most `1e6`; same centre/radius/fraction/normal contract |
| Grid shapes | Positive integer `(rows,columns)`, at most 65,536 cells in each source/output grid |
| Coverage and levels | Finite 2D coverage in `[0,1]`; two linear `[background,material]` values in `[0,255]` |
| Kernels | Nonnegative, finite, odd dimensions at most 31 each; coefficient sum within `2e-6` of one; original coefficients preserved |
| Output map | Finite 2×3 affine coefficients, each with absolute value at most `1e6`; maps centres to source array indices |
| Queries | 1–4,096 integer `[x,y]` pairs inside the output grid; order and duplicates preserved |
| Encoding and work | `srgb8` is a boolean; `max_work` is an integer in `[1,100000000]`, default 100,000,000 |

Invalid inputs raise `ValueError`. An unresolved area intersection or a
nonfinite acquisition stage raises `ArithmeticError`; it is not a completed
prediction or a zero-valued observation. A whole-call stage-work refusal returns
one `None` intensity and `work_limit` status per query, no stages and zero
performed stage work. Validation copies can be allocated before this refusal.

The hash binds validated float64 coverage **before** float32 storage, levels,
raw coefficients, map, ordered queries, output shape and encoding mode. Distinct
float64 coverage inputs can hash differently even if their stored float32
coverage agrees. Returned arrays are backed by immutable bytes. Stage names are
`coverage`, `source_linear`, `optical_linear`, optional `encoded` and
`decoded_linear`, then `rectified` and `final`. Successful queries have status
`resolved`; this is a numerical status, not a model-adequacy decision.

With `N` source cells, `M` output cells and kernel element counts `Ko,Kp`,
required stage work is `N*(1+Ko+4*srgb8) + M*(16+Kp)`. It evaluates whole grids,
even for one query. Geometry coverage work is source-cell bounded and separate.
`required_work`, `performed_work` and `numeric_workspace_bound_bytes` are
returned alongside intensities, statuses, stages and `input_sha256`.

The workspace bound is
`512*(N+M) + 8*(Py_source+Pxy_source+Py_output+Pxy_output) + 262144` bytes.
For image shape `(h,w)` and its correlation kernel `(kh,kw)`,
`Py=(h+kh-1)*w` and `Pxy=(h+kh-1)*(w+kw-1)`. These terms count the simultaneously
live reflected pads, including extreme aspect ratios. The bound excludes caller
inputs and Python/allocator overhead. It is not a process-RSS guarantee, latency
benchmark or capacity claim.
Model adequacy defaults to `not_evaluated`; numerical completion does not
identify a camera PSF, recover geometry, validate current main's shadow model
or qualify CAD/print dimensions.

The completed study retains both saved-coverage downstream replay and analytic-D
replay, every stage array and query residual, all 32 records and both encoding
lanes. No original capture, Gaussian reference or inverse optimizer is rerun.
The subsequent [area sensitivities and fixed linear operator](finite-cell-sensitivity.md)
qualify a separately declared unrounded model. They do not differentiate this
rounded chain. Independent recovery, treatment of rounding/encoding, source
calibration and final boundary preservation remain requirements before adoption.
The separately frozen [local recovery study](validation/finite-acquisition-recovery.md)
preserves both failed protocols and does not extend this forward qualification
to a general inverse or physical camera.


The later [coupled search](finite-acquisition-coupled.md) reaches **11/12**
matched target passes; the [source-event continuation](finite-acquisition-events.md)
stays at **11/12**. Both complete 24-case protocols still exit 1. Their first
focused suites pass 548 tests/nine subtests and 653 tests/21 subtests, respectively.
The [completed results](validation/finite-acquisition-continuations.md) and
[saved-only audits](finite-acquisition-saved-audit.md) retain the remaining PNG
miss, first failures and 28 historical precision unknowns. Candidate code and
complete local ZIPs remain separate from this main runtime and workbench UI.