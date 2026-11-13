# Affine evaluation of finite-material means

The [finite-material inverse](finite-shape-inverse.md) repeatedly evaluates the
same boundary at different image pixels. For an exactly affine homography,
these queries can share transformed curve samples and quadrature panels. The
Gaussian/material model and supplied optics remain the same. This candidate
accelerates the developer operators; it does not select a new photo-tracing
model or add a workbench control. The [prospective plan](../studies/finite-affine-batch-v1.json)
and [complete validation record](validation/finite-affine-batch.md) retain the
numerical controls, actual-fit timings and adverse outcomes.

## Shared geometry, separate pixel integrals

Let `Sigma = L L^T`, and write the affine homography as `(A x + b) / d`.
The existing chart check chooses `d > 0`; when using a local geometry origin,
its translation is already included in `b`. For a local boundary
parameterization `q(t)` and observation centre `p_i`,
the whitened boundary is

```text
u_i(t) = (L^-1 A q(t) + L^-1 (b - d p_i)) / d.
du_i/dt = L^-1 A q'(t) / d.
```

The per-query translation is formed before whitening. This avoids subtracting
two separately whitened large world coordinates. All queries share the linear
map, curve samples and mapped velocity. Each still has its own probability,
range cover, numerical error estimate, tail bound and completion status.

The unchanged Green-boundary kernel evaluates

```text
P_i = (1 / (2 pi)) integral F(||u_i||^2) (u_ix du_iy - u_iy du_ix),
F(s) = (1 - exp(-s/2)) / s,    F(0) = 1/2.
```

The identity `div(u F(||u||²)) = exp(-||u||²/2)` gives this expression by
the divergence theorem, after Gaussian whitening.
`-expm1(-s/2) / s` preserves the removable limit near zero. Curves retain
their analytic line/arc geometry and material/hole signs. Reflection changes
orientation once. Probabilities are never clipped into `[0,1]` to conceal
roundoff or an invalid winding result.

A bound on the whitened boundary speed partitions each curve into panels
with travel at most 0.5. This travel test is a resolution guard, not a proof
of quadrature accuracy. Each query retains the existing 12/24-point embedded
rule comparison, arithmetic guard and far-field angular/tail checks. A failed
batch query can use the original adaptive scalar evaluator with the remaining
work and panel allowance. Error estimates remain engineering estimates, not
certified integral bounds or physical uncertainty.

Vectorizing related integrals is an established numerical approach; see
[Gladwell's one-dimensional quadrature study](https://scispace.com/papers/vectorisation-of-one-dimensional-quadrature-codes-48elbudhat)
and [Johnson's simultaneous-integrand quadrature paper](https://scispace.com/papers/algorithm-988-amgkq-an-efficient-implementation-of-adaptive-5a38fiaxwm).
Those records motivate the computational pattern. This implementation uses its
own geometry-specific panels and existing Green kernel, rather than their
quadrature algorithms. Its independent positive-area controls and archived-fit
replays must establish its numerical behavior separately.

## Work, memory and fallback contracts

Both the raw supplied matrix and normalized geometry must be exactly affine.
A nonzero represented perspective coefficient stays on the scalar path even
if homogeneous normalization would underflow it to zero. Projective maps are
not replaced by local affine approximations.

Every attempted boundary/query-node evaluation is charged. A panel costs two
endpoint evaluations and, when its near rule is used, another 12 + 24 nodes.
Shared geometry does not discount those query operations. Worst-case work and
batch workspace are preflighted before launching a group. Discarded batch work
remains charged before scalar fallback. Every requested query retains an entry,
including `None` and `work_limit` when its allowance is exhausted.

For `Q` queries and `P` shared panels, the declared workspace bound is
`8192 + Q * (24 * P + 8192)` bytes. It covers three dense contribution arrays
plus a conservative allowance for live NumPy temporaries. The default is
16 MiB, with an explicit maximum of 256 MiB. It is not a Python/process RSS
limit or a bound on caller-owned arrays and the scalar evaluator's storage.
Partition, work or workspace refusal uses the existing scalar path.

`backend.finite_affine.finite_shape_probabilities` is the explicit general-ring
entry point. Its `diagnostics` retain batch/scalar evaluations, panels,
discarded queries, fallback reasons and declared workspace. The existing
`backend.finite_centre_fit.circular_segment_probabilities` returns the same
`FiniteShapeResult` type and serialized fields as before; its affine dispatch
does not expose batch-specific fields through that established result schema.

## Use the developer API

Run this from the repository root with the workbench Python environment. It
evaluates an annulus at two pixel centres without fitting a photograph:

```python
import math
import numpy as np
from backend.finite_affine import finite_shape_probabilities

result = finite_shape_probabilities(
    [[25, 25], [45, 25]],
    [[("circle", (25.5, 25.5), 12.0)],
     [("circle", (25.5, 25.5), 2.0)]],
    sensor_shape=(80, 80),
    homography=np.eye(3),
    psf_covariance=np.eye(2),
    probability_tolerance=1e-8,
    max_panels=4096,
    max_evaluations=2_000_000,
    memory_limit_bytes=16 * 1024 * 1024,
)
assert result.statuses == ("resolved", "resolved")
assert abs(result.probabilities[0] - (math.exp(-2) - math.exp(-72))) < 2e-10
assert result.diagnostics.batched_queries == 2
```

`sensor_shape` is `(height, width)`; queries are 1–2048 unique in-frame integer
`(x,y)` pairs evaluated at `(x+0.5,y+0.5)`. The first ring is material and later
rings are holes. Rings use the existing line, three-point arc and circle
contract. The complete region is integrated, including material outside the
sensor; the sensor bounds the query positions. These are point-centre Gaussian
means, not pixel-aperture averages. Covariance uses squared observation-frame
units after the homography, and must be supplied positive definite.

Invalid inputs raise `ValueError`. Valid calls can still return unresolved
per-query statuses and `None` values when work or numerical guards prevent
completion. Inspect each status, error estimate and tail bound before using a
probability. A resolved conditional integral does not validate source topology,
the supplied optics or a physical dimension.

## Measure the complete fit

Kernel speed alone does not determine fitting latency. If a fraction `alpha`
of the old fit time is spent in means and those means speed up by `s`, the
idealized total speedup is `1 / ((1-alpha) + alpha/s)`. Boundary derivatives,
bounded brightness solves, variable projection and refinement still cost time.
That expression describes an attribution model, not a performance guarantee.

The frozen experiment compares the actual public means and complete fitter
with byte-identical original source in an isolated module namespace. It keeps
all warmups and paired alternating repeats on one CPU with single-threaded
numerical libraries. The actual-fit goal is a geometric mean of at least 3×
across three predeclared 40-training-pixel datasets. All 24 original cases and
12 saved-field records retain their original inputs, targets and adverse
outcomes. Accuracy, work completion and performance are reported separately.

On the recorded fixed-CPU, single-thread run, mean evaluation improves by
10.13× and complete fitting by 3.84× in geometric means of paired medians.
The three complete-fit candidate medians are 2.75, 3.91 and 3.66 seconds.
All 36 archived rows remain present, with the same completion flags and the
prior 12 original matched and three measured-ring target passes. These are
conditional results on the declared datasets. The general Jacobian stays
separate from the mean batching; its small arithmetic reuse does not supply
the mean kernel's speedup. See the [per-workload table and raw archive](validation/finite-affine-batch.md#complete-recovery-and-timing-experiment).

Faster conditional fitting does not establish a supplied covariance, thickness
frame, acquisition model or physical dimension. Those remaining requirements
are described in the [model and integration guide](finite-shape-inverse.md).
