# Analytic normal motion in the residual-information diagnostic

The [original residual study](validation/finite-residual-information.md)
could examine covariance under a fixed normal, but all ten normal-angle
finite-difference columns failed their stability checks. The
[analytic normal derivative](finite-normal-derivative.md) now provides a
different numerical route. This separately frozen experiment asks whether it
qualifies on the exact saved observations and whether the apparent covariance
information survives allowing the normal to move.

**Status: the first frozen-source experiment is complete and passes its declared
protocol.** All 578 analytic-normal comparisons qualify, and all ten single
joint trials pass their local linearity check. These trials are not uniformly
better than the saved fixed-normal trials, and smaller residuals do not always
improve synthetic geometry. Read the [complete results and counterexamples](validation/finite-analytic-normal-information.md)
and [lossless archive instructions](../studies/fixtures/finite-analytic-normal-information-v1/README.md).

The [new plan](../studies/finite-analytic-normal-information-v1.json) preserves
all 12 original records, including both upstream refusals. It reuses the saved
brightness, geometry and covariance columns, baseline predictions and fixed-normal
trials exactly. Only the normal block is replaced. The original failed normal
column, independent control and protocol remain historical evidence.

## Distinguish brightness, geometry, normal and blur

For supplied geometry and covariance, the intensity model is

```text
m = a + (b-a)*P
J = [B, G, N, S]
B = [1-P, P] for the free brightness levels
N = (b-a)*dP/dphi.
```

`G` already includes the signed contrast and the saved geometry-domain widths.
`S` already includes the signed contrast and the saved dimensionless SPD
covariance chart. Neither is scaled again. The normal column uses radians
without an additional domain-width factor. Its value uses signed contrast;
its error uses absolute contrast. A dark object on a bright background therefore
does not reverse the geometric rotation convention.

The brightness columns are included only on the saved active face of their
`[0,255]` bounds. A fixed brightness value is not a free nuisance direction.
This is a local fixed-face calculation, not the complete inward tangent cone.
[Variable-projection research](https://www.nist.gov/publications/variable-projection-nonlinear-least-squares-problems)
provides background on separating linear and nonlinear parameters. This
experiment uses a local joint linearization, not a new variable-projection
optimizer or exact brightness reprofiling at a trial.

## Qualify the normal on the actual saved coordinates

Each eligible record retains 40 training and 16 held-out integer pixel indices.
The source geometry is global; the supplied homography maps it to the saved
crop. A queried observation centre is its integer index plus `0.5`. All ten
maps are exact integer crop translations. Their independent reference can
therefore avoid the small projective denominators investigated in the
[preceding arithmetic diagnostic](finite-normal-oracle-conditioning.md).

The material is `disc(C,R) intersect {n dot (x-C) <= R*f}`. The angle `phi`
rotates the source-plane normal counterclockwise, with `C`, `R`, `f` and
`Sigma` fixed. Here `J=[[0,-1],[1,0]]` is the 90-degree rotation, distinct from
the full design matrix named `J` above. With independently normalized `n`, `t=J*n`,
`ell=R*sqrt(1-f^2)`, and `r0=C+R*f*n-p_global`, the signed chord integral is

```text
dP/dphi = -ell^2 * integral[-1,1] u * G_Sigma(r0+ell*u*t) du.
```

The independent implementation uses the exact represented covariance entries,
a direct 2x2 inverse, Decimal normal/length normalization and an independently
computed pi. It evaluates fixed uniform source panels at orders 64 and 96,
with both 80- and 120-digit contexts. Rules are generated once and retained in
hexadecimal. It calls no production geometry, moment or CDF helper and takes
no angular finite difference.

For normalized panel `[u0,u1]`, a complete-panel tail allowance is

```text
ell^2*(u1-u0)*max(abs(u0),abs(u1))
  * exp(-qmin/2)/(2*pi*sqrt(det(Sigma))).
```

`qmin` is the minimum Mahalanobis squared distance over the whole quadratic
segment. Omission requires both precision calculations to pass the frozen
allowance. Other panels must pass the mapped-travel and exponent-variation
guards. Unknowns retain their panels and work; no adaptive retry replaces an
outcome. Four additional diagonal controls compare the chord integral with an
independent elementary first moment, including both normal and contrast signs.

Higher precision and two orders provide engineering evidence, not a certified
quadrature remainder or rule-coefficient enclosure. This translation-only
reference does not repair or qualify the general projective oracle.

## Carry comparison uncertainty into the information calculation

A resolved API status alone does not qualify `N`. Every saved query must pass
the independent comparison at the original requested `1e-10` probability/radian
tolerance and at the API's reported error estimate, with the separately stated
oracle allowances. The old normal FD stability flag stays false.

For API derivative `d_hat`, reference `d_ref`, and signed contrast `c=b-a`,
retain the components of the new level-error array:

```text
E_N = abs(c)*(e_API + abs(d_hat-d_ref) + e_reference)
      + measured level-scaling roundoff.
```

The actual contrast subtraction/product residual is measured against exact
rationals of the supplied levels and represented API derivative. These are
numerical error estimates, not probabilities or confidence limits. Accepted
reference discrepancy is not discarded before constructing the matrix guard.

The complete `N` error enters both the nuisance-projector estimate and the full
training-matrix cutoff. If a nuisance span is not full-column rank under its
guard, its smallest singular value does not exceed its estimated perturbation,
or its projector uncertainty reaches one, covariance uniqueness remains unknown.
[Singular-subspace perturbation research](https://arxiv.org/abs/1605.00353)
explains the role of a spectral gap. Estimated derivative errors do not turn
that conditional calculation into a rigorous perturbation certificate.

## Compare covariance at a matched numerical scale

The original fixed-normal results remain native comparators. A new native
`BGN`-versus-`S` calculation is retained separately. To compare the effect of
adding normal motion, define nuisance spans `T0=[B,G]` and `T1=[B,G,N]` under
one common unprojected `J=[B,G,N,S]` reference and error matrix.

For each qualified full nuisance span, project `S` and propagate its projector
uncertainty into `eta_C0` or `eta_C1`. Both projected spectra then use

```text
tau_shared = max(tau_base, 4*eta_C0, 4*eta_C1).
```

Changing the nuisance projector must not silently change the comparison cutoff.
The nuisance spans themselves retain their qualified full columns; they are not
truncated again at this enlarged projected-covariance cutoff. Raw spectra,
cutoff-sensitivity intervals and residual-dimension ceilings remain explicit.

With exact nested nuisance spans, projected covariance singular values cannot
increase when a nuisance direction is added. Its conditional residual-energy
contribution can increase: the residual and covariance direction both move after
projection. Neither change proves a physical cause, optical identifiability or
statistical significance. The calculation is unweighted because no independent
observation-noise covariance has been established.

For example, let the residual be `(1,-1)` and the covariance direction `(1,1)`.
Their projection energy is initially zero. Removing the nuisance direction
`(0,1)` leaves both as `(1,0)`, whose projection energy is one. The covariance
direction became shorter while its conditional residual energy increased.

## Permit one bounded trial only after qualification

An eligible joint trial solves the full training-only linear system using its
own reported SVD cutoff. It does not substitute the matched projected-covariance
cutoff. One common damping factor enforces the original geometry, covariance,
angle, brightness and domain limits. The plan permits at most one new `BGNS`
forward trial per eligible row, with the original actual-versus-linear criterion.
Held-out responses do not choose damping, a retry or acceptance.

The saved `BGS` trial is a comparator, not another new execution. Original target
passes stay unchanged. Descriptive truth comparisons occur only after all trial
choices and predictions are fixed. Five paired synthetic datasets are not ten
independent captures; the held-out values already influenced preparation and
moments. Physical acquisition, thickness, illumination and optical adequacy
remain separate requirements.

Before any user-facing refinement, a separately qualified inverse must preserve
one accepted boundary through preview and exports, as required by the existing
[integration contract](finite-shape-inverse.md#requirements-before-automatic-trace-integration).
This diagnostic adds no automatic fitting or new interface controls.
