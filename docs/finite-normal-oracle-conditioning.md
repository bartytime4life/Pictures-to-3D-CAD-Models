# Projective node arithmetic in the normal-derivative reference

The [V2 normal-derivative study](validation/finite-normal-error-control.md)
passes its frozen comparisons, but its independent high-precision check exposes
an optimistic reference-quadrature allowance. This separate investigation asks
where that reference loses precision before its result is used to assess a
fitting algorithm. It does not change the production derivative, automatic
tracing or the original study.

The [frozen diagnostic plan](../studies/finite-normal-oracle-conditioning-v1.json)
declares two post-hoc controls and 24 new synthetic controls. It compares the
unchanged reference arithmetic with two exact-rational/Decimal paths and a
binary64 endpoint-interpolation path. Every arithmetic path reuses the same
generated arrays for each order within this diagnostic.

The [single completed comparison](validation/finite-normal-oracle-conditioning.md)
retains all 26 scenes and passes its frozen criteria. For the first original
control, most of the error arises before higher-precision map evaluation begins:
the rounded source node has already lost information. Endpoint interpolation
reduces the two original order-192 errors to about `8.28e-13` and `2.19e-12`.
These findings concern this restricted reference path, not a replacement general
oracle or a new production fitting result.

## Why two integration orders can agree and still be wrong

On a source chord, let `w(s)` be the positive projective denominator and `N(s)`
the homogeneous observation residual. If `L L^T = Sigma`, define
`u(s) = L^-1 N(s) / w(s)`. Apart from its signed source factor, the integrand is

```text
F(s) = -s * abs(det(H)) / (2*pi*sqrt(det(Sigma))*w(s)^3)
       * exp(-||u(s)||^2/2).
```

Holding the numerator fixed, its logarithmic denominator sensitivity is

```text
partial log(abs(F)) / partial log(w) = -3 + ||u||^2.
```

For the compressed controls, `w(s)=1+c*s`. Near an endpoint this subtracts
nearly equal quantities. A small absolute denominator error can therefore have
a much larger relative effect on the integrand. Both orders repeat the same
coordinate arithmetic; agreement between their sums does not measure a shared
bias. Accurate final summation cannot recover information already lost at a node.

Source-node displacement moves the numerator and denominator together. For the
restricted family its different sensitivity is

```text
d log(abs(F)) / ds = 1/s - 3*c/w - d^2*s/w^3,   s != 0.
```

A denominator-only allowance therefore cannot substitute for source-node error
accounting. At zero, use the finite absolute derivative instead of this relative
expression.

## Keep node placement separate from subsequent arithmetic

For panel `[a,b]` and represented rule node `xi`, the exact affine source
coordinate is `s=(a+b)/2+(b-a)*xi/2`. The diagnostic compares four paths:

| Path | Coordinates and evaluation | What its comparison can show |
| --- | --- | --- |
| Original binary64 | Unchanged V2 node, map, whitening and log-density calculations | Reproduction of the saved controls under the current pinned environment |
| Rounded-source Decimal | Preserve the original rounded `s`; evaluate the represented map with exact rationals and Decimal arithmetic | Combined error after source-node placement, including mapping, normalization, functions and reduction |
| Exact-source Decimal | Form `s` exactly from panel endpoints and the represented rule node; otherwise use the same Decimal path | Source-node placement error relative to the preceding Decimal path |
| Endpoint binary64 | Compute homogeneous endpoints exactly, round once and interpolate their denominators and residuals | Whether a practical stable evaluation reduces the combined arithmetic error on this declared population |

Both Decimal paths use the same exact panel half-width and represented rule
weights. Their difference does not mix a change in quadrature rule or panel
width with source-node placement. Decimal precision is fixed at 80 and 120;
the independent elementary boundary identity is evaluated at both precisions.
Python documents [correct rounding for Decimal exponential evaluation](https://docs.python.org/3.12/library/decimal.html#decimal.Decimal.exp).
That property alone does not enclose the complete calculation or integral.

## Evaluate positive denominators from panel endpoints

For `lambda=(1+xi)/2`, affine homogeneity gives

```text
w(s) = (1-lambda)*w(a) + lambda*w(b).
N(s) = (1-lambda)*N(a) + lambda*N(b).
```

When both endpoint denominators are positive, the denominator interpolation
adds nonnegative contributions instead of subtracting nearly equal large terms.
Exact rational endpoint construction also avoids losing a small denominator
before interpolation begins. Residual components can still cancel, and the
normalizer, functions and final sums still round. This changes several arithmetic
steps; improvement by itself would not identify denominator rounding as the sole
cause of the earlier error.

A conditional propagation result helps define future error accounting. Suppose
the whitened homogeneous numerator has absolute norm error at most `eta_N`,
the denominator has absolute error at most `eta_w`, and `w_hat > eta_w`.
For `u_bar=N_hat/w_hat`, exact arithmetic then gives

```text
||u-u_bar|| <= (eta_N + ||u_bar||*eta_w)/(w_hat-eta_w) = E_u
abs((||u||^2-||u_bar||^2)/2) <= ||u_bar||*E_u + E_u^2/2.
```

These inequalities assume actual bounds on their inputs. This diagnostic does
not supply a general interval implementation of those bounds. Division,
normalization, exponential evaluation and the signed source factor need their
own accounting. Near `s=0`, an absolute interval calculation is needed instead
of a relative bound on `log(abs(s))`.

## What remains outside this diagnostic

All controls use one exact source chord, identity covariance and a restricted
homography family with an elementary integral. They test arithmetic under a
supplied model. They do not qualify arbitrary covariance conditioning, material
geometry, tail selection, a general adaptive oracle, camera optics or an inverse.

Rule coefficients remain represented floating values. The original V2 report
does not retain literal node arrays, so this diagnostic saves newly generated
arrays in hexadecimal and checks original-value reproduction separately.
[NumPy documents testing `leggauss` through degree 100](https://numpy.org/doc/stable/reference/generated/numpy.polynomial.legendre.leggauss.html);
the order-192 coefficients have no established enclosure here. Decimal evaluation
at fixed represented nodes does not remove coefficient or quadrature-truncation
error. [NIST's quadrature treatment](https://dlmf.nist.gov/3.5) distinguishes the
quadrature formula from its remainder.

The next application-facing dependency is a separately frozen
[normal-aware residual-information diagnostic](finite-residual-information.md).
It must give the analytic normal column its own statuses, error estimates and
work accounting while retaining the original finite-difference failure. Only
after that diagnostic should a bounded normal-aware inverse and one reviewed
refinement candidate be considered for the interface.
