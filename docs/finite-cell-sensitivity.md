# From source-cell areas to intensity sensitivities

These developer operators supply a dependency for geometry recovery: five
unrounded shape sensitivities and a separately declared linear acquisition
operator. They do not fit geometry, estimate a camera model or change automatic
tracing. The [complete qualification](validation/finite-cell-sensitivity.md)
retains the fixed population and deliberate unknowns.

The [preceding source-cell mean](finite-acquisition-mean.md) remains unchanged.
It explicitly stores float32 stages and optionally encodes sRGB8. Its literal
rounded outputs do not have the smooth derivative described here.

## Boundary flux in the represented geometry

Let `m` be the canonicalized normal stored by `finite_aperture`, `q=m·m`,
and material `D={x: ||x-C||<=R, m·(x-C)<=f*R}`. The exact norm of the represented
components need not be one. The angle parameter continuously rotates this
stored `m`, preserving its exact norm; it does not differentiate the input
normal's binary64 canonicalization.

For a fixed cell, retain every exposed circle interval `[alpha,beta]` inside
the cell and half-plane. For `q>f*f`, parameterize the closing chord in
unit-disk coordinates; degenerate or unresolved alternatives are withheld:

```text
u = (x-C)/R = f*m/q + v*Jm,
Jm = (-m_y,m_x),
|v| <= sqrt(q-f*f)/q.
```

Clip that chord to the fixed cell, obtaining `[v0,v1]`. Set `L=v1-v0` and
`V=(v0+v1)/2`. All chord contributions vanish for an empty clipped chord
interval; exposed circle contributions can remain. The area
derivatives, before dividing by the fixed cell area, are

```text
dA/dCx    = R*sum(sin(beta)-sin(alpha)) + R*m_x*L
dA/dCy    = R*sum(cos(alpha)-cos(beta)) + R*m_y*L
dA/dR     = R*sum(beta-alpha)          + R*f*L
dA/df     = R*R*L
dA/dtheta = -R*R*q*L*V.
```

The circle factor `R` comes from arc-length measure `ds=R*dalpha`.
The [DiffVG authors' erratum](https://people.csail.mit.edu/tzumao/diffvg/)
also makes the boundary-measure factor explicit. The equations here are a
separate disk/chord derivation, rather than an implementation of that paper.
They include the chord's displacement; omitting it changes the derivative.
Centre/radius coverage columns have units inverse plane length, the fraction
column is dimensionless and the angle column is per radian.

Circle/line events use exact rational-plus-square-root predicates. Only proven
identical events are merged. Event coordinates and chord moments use bounded
96-digit Decimal arithmetic; endpoint angles, trigonometry and outputs remain
binary64. Small arc moments use midpoint/half-angle identities. Distinct events
that cannot be numerically separated or classified remain unknown. The
arithmetic estimates are engineering guards, not certified enclosures.

## Area-sensitivity API

`backend.finite_aperture_sensitivity.segment_cell_sensitivity` accepts the
same centre, radius, fraction, near-unit normal, grid shape, origin and pitch
as [the area API](finite-acquisition-mean.md#refusals-provenance-and-work).
`max_work` is a positive integer at most 65,536, default 65,536.

```text
segment_cell_sensitivity(*, centre, radius, fraction, normal,
                         shape, origin, pitch, max_work=65536)
```

The immutable result contains:

- `coverage[rows,columns]`, preserving the preceding area evaluator;
- `jacobian[rows,columns,5]` and `estimated_absolute_error` in parameter order
  `centre_x, centre_y, radius, fraction, normal_angle`;
- flat row-major `statuses`, an input hash, work counts and a numeric workspace
  bound of `256*cells+65536` bytes, excluding caller/Python/exact-number storage.

`resolved` means numerical completion. A positive-length chord coinciding with
a cell side returns `nondifferentiable`. Fractions `-1` and `1` return
`parameter_endpoint` for the full Jacobian. Other numerical ambiguity returns
`unresolved`; that status does not assert mathematical nondifferentiability.
Unknown Jacobians contain NaN in every column, even when coverage is available.
They must be serialized as null with their status or explicitly refused.

Work counts one complete cell evaluation per unit, rather than arithmetic
instructions. A whole-call budget refusal returns `work_limit`, all unknown
arrays and zero performed cell work. Input validation still runs first.
Internal Decimal moment cancellation has an explicit precision guard and
propagated absolute allowances; no geometric tolerance moves the boundary.

## Fixed linear acquisition API

`backend.finite_acquisition_linear.acquisition_linear` has the call signature

```text
acquisition_linear(fields, *, optical_kernel, output_shape,
                   output_to_source_index, post_kernel, queries,
                   max_work=100000000)
```

It applies
optical correlation, signed Keys resampling, post correlation and ordered query
selection. Its grid, kernel, map and query limits match the
[rounded acquisition API](finite-acquisition-mean.md#refusals-provenance-and-work).
`fields` has shape `(height,width)` or `(height,width,channels)`.
It accepts one to six finite signed float64 fields, including coverage plus all
five derivative columns. It evaluates one additional constant field, charging
that work explicitly.

Take the computed tap indices and binary64 coefficients as fixed. They define
a mathematical linear operator `A`; its evaluated outputs approximate that
operator in floating arithmetic. No claim is made about differentiating the
literal bit-level arithmetic, or about uncertainty in the supplied map.
There are no float32 storage casts or source-encoding stages in this model.

For `v=A*c`, `a0=A*1` and supplied background/material levels `b,a`,

```text
brightness design = [a0-v, v]
mu = b*a0 + (a-b)*v
J_geometry = (a-b)*A*J_coverage.
```

Raw kernel coefficients remain unchanged, so the constant response must be
computed. Replacing `a0` by one would change the photometric model. Equal
brightness levels give zero geometry signal; checking derivative columns does
not prove identifiable geometry after brightness is fitted.

Results include immutable query values, the computed constant response,
per-field arithmetic estimates, input/operator hashes, work and workspace
metadata. For `C` supplied fields and `Q` ordered query rows, `query_values`
has shape `(Q,C)`, `constant_response` has shape `(Q,)`, and `estimated_errors`
has length `C`: each entry is a uniform per-field estimate built from maxima
over the computed grids, rather than a per-query estimate.
`constant_estimated_error` reports the constant field's
estimate separately. `error_components` contains the three named stage entries
`optical`, `Keys` and `post`; each holds `C+1` channel estimates with the
constant field last. Nonfinite input fields are rejected, so unknown source-cell
derivatives cannot silently become zero contributions. Work refusal returns
absent arrays and explicit statuses; attempted numerical failure retains its
declared work charge.

Those arithmetic estimates treat supplied field values as fixed. They do not
include `segment_cell_sensitivity`'s area/Jacobian estimates. A caller must
propagate incoming field error separately: an infinity-norm field allowance
is amplified by the optical coefficient L1 norm, returned `keys_l1_bound` and
post coefficient L1 norm, then combined with operator arithmetic. Incoming
engineering estimates do not become certified bounds through that propagation.

For `C` supplied channels, `D=C+1`, `N` source cells, `M` output cells and kernel
element counts `Ko,Kp`, work is `D*[N*(1+Ko)+M*(16+Kp)]`, capped at 100 million.
The bound counts packing, products and interpolation taps; coefficient
preparation is separately grid-bounded. Workspace counts channel-scaled
simultaneous pads and query copies:

```text
512*D*(N+M) + 8*D*(Py_s+Pxy_s+Py_o+Pxy_o) + 32*Q*(D+2) + 65536 bytes.
```

`Py_s,Pxy_s` are the vertically and fully reflected source-pad cell counts;
`Py_o,Pxy_o` are the corresponding output pads, using the
[same shape-dependent definitions as the staged API](finite-acquisition-mean.md#refusals-provenance-and-work).
Caller arrays, Python objects and allocator overhead are excluded. Neither count is a latency or process-RSS
guarantee. Arithmetic estimates propagate absolute input scales through signed
weights; cancellation does not justify scaling only by the final output.

## Small executable example

Run this from the repository root with the workbench Python environment.
It evaluates supplied geometry once and propagates six fields once. It does
not fit dimensions or exercise the rounded acquisition chain. Source cell
`(0,0)` is centred at plane coordinate `(0,0)`; the affine translation below
maps output geometric centres `(x+0.5,y+0.5)` to source array indices `(x,y)`.

```python
import numpy as np
from backend.finite_aperture_sensitivity import segment_cell_sensitivity
from backend.finite_acquisition_linear import acquisition_linear

area = segment_cell_sensitivity(
    centre=(1.1, 0.95), radius=0.9, fraction=0.3, normal=(0.6, 0.8),
    shape=(3, 3), origin=(0.0, 0.0), pitch=1.0,
)
if any(status != "resolved" for status in area.statuses):
    raise RuntimeError(f"Unknown area derivatives: {area.statuses}")

fields = np.concatenate((area.coverage[..., None], area.jacobian), axis=2)
linear = acquisition_linear(
    fields,
    optical_kernel=np.ones((1, 1)),
    output_shape=(3, 3),
    output_to_source_index=np.array([[1., 0., -0.5], [0., 1., -0.5]]),
    post_kernel=np.ones((1, 1)),
    queries=np.array([[0, 0], [1, 1], [2, 2]], dtype=int),
)
if any(status != "resolved" for status in linear.statuses):
    raise RuntimeError(f"Unknown propagated values: {linear.statuses}")
print(area.parameter_order)
print(linear.query_values.shape)  # (3, 6): coverage, then five columns
print(linear.constant_response)  # use this response in the brightness design
```

The three query rows demonstrate the interface. They are insufficient to
identify five geometry parameters with two unknown brightness levels.

## Remaining recovery work

The [259-test result and fixed study](validation/finite-cell-sensitivity.md)
support these supplied-model derivatives. Five-query coupled controls test the
columns individually; they cannot establish five-parameter rank with two free
brightness nuisance levels. The reviewed main source has no acquisition-aware
five-parameter inverse. A [separately frozen local prototype](finite-acquisition-recovery.md)
now uses observed-only seeds/bounds, bounded brightness handling and separate
smooth and literal rounded objectives. Its original protocol at `7ec6803`
passes 4/12 matched cases; the continuation at `e6e2c2` passes 9/12 (four smooth,
four float32-staged and one PNG). Both complete 24-row protocols retain 12 adverse
rows and exit **1**. Its **459 focused test passes** are separate software evidence;
they do not make this a qualified general inverse or add a GUI/HTTP mode.

The [coupled seven-parameter proposal](finite-acquisition-coupled.md) and
[paired saved-data auditor](finite-acquisition-saved-audit.md) are newer local
authoring work, with no executed tests, study or audit yet. Their plans preserve
the original population, targets and global work caps. Complete local archive
member checks establish packaging integrity only; neither candidate is added
to this main runtime or the workbench interface.

The following remain requirements before main integration. The local prototype
exercises them with [retained recovery failures and audit limits](validation/finite-acquisition-recovery.md);
the derivative study alone does not qualify the solver. In particular, full-field
initialization uses eventual reserved pixels, so their residuals are conditional
checks rather than independent holdout predictions.

| Concern | Required distinction |
| --- | --- |
| Unknown brightness | In the smooth model, solve bounded levels using `[A1-Ac,Ac]` at every geometry trial; the literal rounded chain needs its own bounded search and actual-cost checks |
| Geometry information | Project mean sensitivities against brightness nuisance directions; with two independent free brightness columns, at least seven independent observations are necessary for rank five, but are not sufficient |
| Active brightness bounds | Report the conditional active-face rank separately from rank allowing both brightness levels; a bound supplies an additional constraint |
| Undefined derivatives and plateaus | Retain unknowns and qualify cost-only search separately; a zero clipped step or a PNG plateau does not establish smooth stationarity |
| Initialization and evaluation | Derive seeds and bounds from observations and declared limits; keep evaluation dimensions out of initialization, ranking and post-hoc bound changes |
| Normal angle | Preserve the stored-normal rotation family; repeated input canonicalization is not literally the derivative qualified here |
| Resource limits | Account for all attempted geometry, brightness and stage evaluations, including failed work and unfinished searches |

Known affine sampling on uniform source cells does not establish arbitrary
projective phone-camera optics. Physical calibration, independent dimensions,
one accepted boundary through CAD exports, and fit/print checks remain separate.
