# Determinant and global error control for the finite-chord derivative

This experimental correction concerns the signed
[normal-angle derivative](finite-normal-derivative.md), under the same supplied
homography and Gaussian observation model. The
[frozen version 2 plan](../studies/finite-normal-error-control-v2.json) preserves
the original 337 scenes and adds 80 prospective scenes. Its
[complete qualification](validation/finite-normal-error-control.md) passes all
frozen comparisons and preserves a separately observed oracle-error limitation.
The original
[failed version 1 study](validation/finite-normal-derivative.md) remains intact.
This work does not fit a normal, identify physical optics or change automatic
tracing.

## Represent the matrix actually evaluated

For the operational homography `h`, the area factor is
`abs(det(h)) / w(x)^3`. Normalization and translation into local coordinates
have already rounded `h` to binary floating point. Computing an exact determinant
of a different, unrounded map would mix two represented geometries.

Every finite binary float is a rational number with a power-of-two denominator.
The fixed 3×3 determinant can therefore be evaluated exactly for the nine
represented entries, using Python's
[exact float-to-Fraction conversion](https://docs.python.org/3.12/library/fractions.html).
This removes cancellation in the determinant calculation. It does not undo
rounding in map construction, whitening or point transformation.

The candidate converts the positive determinant to a binary mantissa and
exponent before taking logarithms. It computes the mantissa conversion residual
using exact rationals and includes an estimated allowance for logarithm arithmetic. The inverse
Cholesky factor supplies the Gaussian density normalizer through its exact
represented 2×2 determinant. Although its mathematical inverse is triangular,
the general numerical solver can leave a tiny nonzero upper entry. The
[software addendum](../studies/finite-normal-error-control-inverse-addendum-v2.json)
preserves that finding and requires the full represented determinant, rather
than silently zeroing the entry or refusing a supported covariance.
One shared normalizer serves the closed
form, tails and quadrature. Its determinant sign supplies reflection metadata.
These floating function allowances remain engineering estimates.

## Spend the allowance across the complete integral

A panel receives either a signed value and estimated error, a zero value with
an absolute omitted-tail allowance, or an explicit requirement to subdivide.
Every non-tail panel must pass the original mapped-travel, Gaussian-exponent
variation and projective-denominator guards. Two integration orders agreeing
alone cannot resolve an unexamined narrow peak.

For a complete frontier of leaves, write

```text
I = sum(I_i)
E = sum(e_i) + error in reducing the represented I_i values.
```

Each `e_i` includes the embedded-rule discrepancy, arithmetic scales from both
rules' absolute contributions, and the shared normalizer allowance. Tail bounds
participate in the same sum. Opposite signs cannot erase those local errors.
Resolution requires the complete estimated error to meet the original requested
tolerance. Otherwise the largest-error leaf is subdivided, with deterministic
ties. A mandatory unresolved panel is subdivided first.

Global adaptive integration and reported absolute error estimates are established
numerical techniques; [QUADPACK's interface](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html)
provides background. This implementation retains its own finite-chord guards,
rules and work accounting, without adding a SciPy dependency.

## Measure the final reduction instead of inventing a floor

Once the local error sum is small enough, let `V` be the exact rational sum of
the represented leaf values, `E_local` the exact sum of their represented
nonnegative error estimates, and `v` the floating `math.fsum` result. The final
reported estimate is rounded upward from

```text
E_local + abs(Fraction(v) - V).
```

This measures the actual final reduction error of those represented values.
It also handles the platform-dependent final rounding described in
[Python's fsum documentation](https://docs.python.org/3.12/library/math.html#math.fsum).
It does not certify any upstream panel, map or function estimate. This additional
work is bounded by the maximum frontier size and adds no quadrature-node units.

A parent remains represented until both children have been inspected. Exhausted
work, nonrepresentable arithmetic or midpoint stagnation returns an explicit
unknown, never a resolved partial integral. All discarded parent and attempted
child work stays charged. The public schema and limits remain unchanged.

## An elementary reference for the compressed-map controls

For `C=0`, `R=1`, `f=0`, `n=(1,0)`, identity covariance and query centre
`p=(0.5,0.5)`, consider

```text
H = [[1, c/2,     1/2],
     [0, c/2 + d, 1/2],
     [0, c,       1  ]],       abs(c)<1, d!=0.
```

On the chord, `x=0.5` and `y-0.5=d*s/(1+c*s)`. Substitution into the signed
boundary integral gives this independently derived reference:

```text
dP/dphi = [exp(-d^2/(2*(1+c)^2)) - exp(-d^2/(2*(1-c)^2))]
          / (2*pi*abs(d)).
```

For represented inputs, `d` is the exact binary difference between the supplied
middle coefficient and `c/2`, rather than the nominal decimal label. A stable
`expm1` difference avoids subtracting nearby exponentials. The reference checks
the original compressed cases without using the production moment formula or
the earlier quadrature oracle. Its floating evaluation still carries its own
arithmetic allowance; it is not a physical measurement.
