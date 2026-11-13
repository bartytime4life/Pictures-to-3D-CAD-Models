# Source-cell acquisition means

The [previous forward study](finite-acquisition-operator.md) found that matching
Gaussian second moments did not reproduce the supplied acquisition chain, even
at the true geometry. This candidate replaces that approximation with two
explicit developer operators: analytic finite-material cell coverage, followed
by declared discrete acquisition stages. It has no tracing, fitting or HTTP
integration. Numerical qualification follows the
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

Rounding makes geometry and brightness dependence nonsmooth. The existing
Gaussian Jacobian and exact two-level variable projection cannot be attached
unchanged. A tiny analytic/polygon area difference may cross an encoding bin;
quantization differences must be retained rather than hidden by an inflated
linear tessellation allowance.

## Refusals, provenance and work

The API limits source/output cells, queries and finite kernel dimensions before
stage allocation. Input errors raise `ValueError`; a stage-work budget refusal
returns one `work_limit` unknown per query and zero performed stage work. The
hash binds effective coverage, levels, coefficients, map, queries, output shape
and encoding mode. Returned arrays are backed by immutable bytes.

Work counts source mixing cells, kernel products and interpolation taps, with
encoding/decoding counted separately. Geometry coverage work is source-cell
bounded and separate. The numeric workspace bound excludes caller inputs and
Python/allocator overhead. It is not a latency benchmark or capacity claim.
Model adequacy defaults to `not_evaluated`; numerical completion does not
identify a camera PSF, recover geometry, validate current main's shadow model
or qualify CAD/print dimensions.

The completed study retains both saved-coverage downstream replay and analytic-D
replay, every stage array and query residual, all 32 records and both encoding
lanes. No original capture, Gaussian reference or inverse optimizer is rerun.
Independent recovery, derivatives, source calibration and final boundary
preservation remain subsequent requirements before automatic adoption.
