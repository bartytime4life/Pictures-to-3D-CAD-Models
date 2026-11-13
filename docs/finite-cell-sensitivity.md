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
`V=(v0+v1)/2`; both contributions vanish for an empty interval. The area
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

`backend.finite_acquisition_linear.acquisition_linear(fields, ...)` applies
optical correlation, signed Keys resampling, post correlation and ordered query
selection. Its grid, kernel, map and query limits match the
[rounded acquisition API](finite-acquisition-mean.md#refusals-provenance-and-work).
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
metadata. Nonfinite input fields are rejected, so unknown source-cell
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
simultaneous pads and query copies. Neither count is a latency or process-RSS
guarantee. Arithmetic estimates propagate absolute input scales through signed
weights; cancellation does not justify scaling only by the final output.

## Remaining recovery work

The [259-test result and fixed study](validation/finite-cell-sensitivity.md)
support these supplied-model derivatives. Five-query coupled controls test the
columns individually; they cannot establish five-parameter rank with two free
brightness nuisance levels. A bounded inverse still needs observed-only seeds
and bounds, prospective reserved dimensions, rank/contrast checks and an
explicit policy for nondifferentiable cells and rounded source encoding.

Known affine sampling on uniform source cells does not establish arbitrary
projective phone-camera optics. Physical calibration, independent dimensions,
one accepted boundary through CAD exports, and fit/print checks remain separate.
