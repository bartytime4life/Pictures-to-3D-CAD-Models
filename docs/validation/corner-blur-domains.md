# Shared blur domains and safe radius projection — November 12, 2026

This developer-analysis candidate is based on PR #50 head
`be2a58cedb7a69702a57c9953a0e0d1e965feae8`. It extends the
[fixed-corner tool](../corner-feasibility.md) with a version-2 Cartesian domain
for `(radius, sigma_x, sigma_y)`. Production tracing, API, UI and generated CAD
are unchanged. Blur bounds and observation intervals remain supplied assumptions.

## Joint compatibility is stronger than separate fits

For all observations `i`, the feasible set is
`F = {(r,sx,sy) in P : U_i(r,sx,sy) in Y_i for every i}`.
The radius result is its projection, so each compatible radius must have one
common blur pair satisfying every observation. That pair may depend on radius.
This applies [bounded-error set inversion](https://webperso.ensta.fr/jaulin/paper_automatica93.pdf)
to nuisance parameters; it does not make input uncertainty equivalent to
[physical model discrepancy](https://www.tonyohagan.co.uk/academic/pdf/simmach.pdf).

An exact-geometry counterexample uses radius zero, `sx,sy in [1,2]`, and:

| Observation | Supplied level interval | An individual blur witness |
| --- | --- | --- |
| A: `(0,1)` | `[0.420,0.421]` | `(1,1)` gives about 0.42067237 |
| B: `(1,0)` | `[0.420,0.421]` | `(1,1)` gives about 0.42067237 |
| C: `(1,1)` | `[0.478,0.479]` | `(2,2)` gives about 0.47812034 |

Each observation has a witness, but no common pair exists. At radius zero,
`U(0,y)=0.5 Phi(y/sy)` and `U(x,0)=0.5 Phi(x/sx)`. If either sigma is at least
1.5, A or B has level at most `0.5 Phi(2/3)`, about 0.37375, below its target.
When both are below 1.5, C has level at least `Phi(2/3)^2`, about 0.55877,
above its target. This covers the complete blur domain.

The computed unsplit-domain result is **unknown** with a one-classification
budget. With a 31-classification budget, the tool rejects the complete domain
after **three classifications**. Separate singleton-blur controls certify the
three individual witnesses. Combining independent per-point radius projections
would incorrectly keep radius zero as jointly compatible.

Full accepted joint boxes project into the inner radius set; accepted plus
unknown boxes project into the outer set. Rejected joint boxes are reported
separately. Their radius projections cannot be treated as rejected radii:
another blur can explain the same radius. Regression tests explicitly retain a
radius shared by accepted and rejected nuisance boxes. Strict disjointness and
complete pending-box retention preserve closed contacts and budget coverage.

## Probability bounds with uncertain sigma

CDF interval division encloses every positive sigma in a box, without assuming
monotone blur dependence. In fact, Gaussian strip mass on `[1,2]` with mean zero
has an interior maximum at `sigma = sqrt(3/(2 ln 2))`; endpoints 0.25 and 4 alone
miss it. A separate `erfc` oracle and a density envelope exercise this case.

Natural interval subtraction of neighboring CDFs is valid but can lose
dependency on their common sigma. Repeating that subtraction across many strips
can widen a cover. The candidate intersects each X-strip mass with
`(b-a) × D`, where `D` encloses the Gaussian density over the complete strip
and sigma domain. Both intervals contain the same actual mass for every sigma,
so their intersection remains valid. The width is computed outward and the
standardized square range includes zero when appropriate.

`Interval.exp` pads correctly HALF_EVEN rounded Decimal endpoints with their
context neighbors, preserves `exp(0)=1`, retains a positive upper bound after
underflow, and refuses overflow. The [Python 3.12 contract](https://docs.python.org/3.12/library/decimal.html#decimal.Decimal.exp)
supports the rounding step; independent rational Taylor/geometric-tail checks
test it. An inconsistent mass intersection raises a numerical failure and leaves
the parameter box unknown.

A retained adaptive numerical probe uses point `(0.5,0.5)`, radius `2.25`,
sigma domains `[0.49,0.51]` and `[1.49,1.51]`. Level-enclosure widths are:

| Strips | Natural CDF differences | Intersected density/CDF mass bounds |
| ---: | ---: | ---: |
| 8 | 0.10614509 | 0.10614509 |
| 16 | 0.07725293 | 0.07725293 |
| 32 | 0.08228600 | 0.05273219 |
| 64 | 0.12374539 | 0.03619634 |

This is numerical development evidence, not a universal convergence rate.
Broad sigma domains, dependency, coarse tails and stopping/work limits can still
leave unknowns. More cells are not a physical accuracy guarantee.

## Known-truth development cases

A local plan fixed true radius `2.25 px`, true blur `(0.5,1.5) px`, two exact
points `(0.5,0.5)` and `(1.5,0.5)`, synthetic level bands of ±0.05, prior radius
`[0,4] px`, 16 strips, stopping width `0.0625 px` and a 255-classification budget.
Independent angular `erfc`/Gauss–Legendre observations at orders 64/128 agreed
within `1.34e-15`. They share Gaussian physics, but no production CDF, cover,
geometry, renderer or fitter. These are development cases, not unseen captures.

| Sigma-X / sigma-Y domains (px) | Status | Inner radii (px) | Outer radii (px) | Budget exhausted |
| --- | --- | --- | --- | --- |
| `[0.5,0.5]` / `[1.5,1.5]` | Conditionally compatible | `[2,2.4375]` | `[1.6875,2.875]` | No; 41 classifications |
| `[0.49,0.51]` / `[1.49,1.51]` | Conditionally compatible | `[2,2.375]` | `[1.625,3]` | Yes; 255 classifications |
| `[0.45,0.55]` / `[1.35,1.65]` | Unknown | Empty | `[1.375,3.5]` | Yes; 255 classifications |

All three retain the true joint tuple in accepted or unknown boxes. Every
accepted midpoint was checked independently. Exact rational volume accounting
and interior-overlap checks cover the complete joint prior, including globally
degenerate axes. Numerical budgets differ from physical uncertainty: the wider
case remains unknown rather than being relabeled compatible. Finite-run inner
sets need not expand monotonically when a prior is widened and split choices
change; each run retains its own valid enclosure.

## Checks and remaining engineering work

Completed source-bound checks are recorded with the candidate's final local
receipt. The fixed-sigma version-1 demo and file format remain supported; the CLI
now hashes four implementation files and retains the complete input for both
versions. No production fit threshold or automatically inferred error bound is
introduced.

- Complete Python invocation: **839 passed in 137.86 s**, with no skips.
  This adds 50 joint-domain tests, 16 CLI checks and 13 exponential checks to
  the earlier 760-test candidate. The focused numerical/CLI invocation passed
  **209 tests**. Seven changed implementation/test hashes were frozen before
  the full run.
- Full-repository Ruff and whitespace checks passed. The existing companion
  documentation invocation passed **19 tests**; library reader sources,
  generated outputs, dependency locks and release records are unchanged.
- Guide JSON examples, documentation links and their parsing results are
  recorded in the final receipt. All **62 Markdown documents** parse; **600 local
  links**, including **46 fragments**, resolve; **98 tables** have consistent
  columns. Both exact guide inputs ran through the actual CLI with saved/stdout
  output, retained input and byte/source hashes agreeing. Frontend build and browser tests were not
  repeated: no frontend, production API or geometry path changed. Prior browser
  runs, hosted CI, installed state and physical qualification retain separate
  bindings.

Blur/pose/coordinate calibration, spatial variation, correlated or non-Gaussian
PSFs, model discrepancy and reserved real-capture dimensions remain unqualified.
The core model still fixes a circular right corner in a known frame. This
extension addresses one nuisance domain, not general physical adequacy.

Local plans, scripts, all positive/unknown/negative outcomes and logs remain in
ignored `.local/verification/`; the following are provenance identifiers:

| Artifact | SHA-256 |
| --- | --- |
| `blur-domain-development-plan.json` | `40d9eb5f3a328162ef139fae12c617bd76b28ec2595bc54974e535ecf17ba56e` |
| `blur-domain-development.py` | `5315a2d37feee9d544c7d64b345bfc52fd2a68c8bbef098af9164bcaeaa4ed18` |
| `blur-domain-development.json` | `a07585a9d88a13f08e30376fc25975bda0a51d8889588bd2ba4850d10a04029d` |
| `blur-domain-natural-mass-probe.json` | `5bc69decb0a649be001daf0b53856ecda725a5ed8b56aa29d89cccf1ca25d720` |
| `blur-source-freeze.json` | `0fad11765fca7b1c548a7d54226c66908fd7677094fc65bc1447d7c805c4d6ac` |
