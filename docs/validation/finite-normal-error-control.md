# Finite-normal error control: qualification and remaining oracle limit

The single frozen-source V2 execution **exited 0**. It retains all 417 scenes
and 4,832 queries: 337 original scenes are explicitly post-hoc regression,
while 80 additional scenes were fixed prospectively. Every query resolves and
passes both frozen comparisons. All 72 supplemental positive-area checks pass.
These are comparisons under supplied Gaussian optics and numerical allowances,
not certified absolute bounds or a physical-camera qualification.

The [method guide](../finite-normal-error-control.md) explains the exact
represented determinants, complete global frontier, exact final reduction and
elementary compressed-map reference. The [portable archive](../../studies/fixtures/finite-normal-error-control-v2/README.md)
retains the complete original result, first attempts and independent audits.
The [original failed V1 study](finite-normal-derivative.md) remains unchanged.

## Frozen design and source

The [main plan](../../studies/finite-normal-error-control-v2.json), SHA-256
`b59d38b3ca92449c4233b947dd061f7a6591ce1944946b6c10e868afaad3adbb`,
was committed at `1f58f4c` before any V2 candidate/test/oracle evaluation.
All 337 old scenes retain the requested `1e-10` tolerance and original caps.
The new design crosses 72 geometry/map/covariance scenes, adds six compressed
maps with three queries each, and two short-chord/endpoint scenes. Only those
six additional compressed scenes request `1e-8`, as declared before execution;
this does not relax any original target.

Preflight found that a general solve of a triangular Cholesky factor leaves a
tiny nonzero inverse upper entry for supported covariance. All 27 solver-only
diagnostic cases retained this entry; no candidate/oracle was called in that
diagnostic. The [software addendum](../../studies/finite-normal-error-control-inverse-addendum-v2.json),
SHA-256 `5703d6fa480ba2801291865b2b9921ba7c8b875ef96adc1beb3d3d4b3bcfb8bd`,
was committed at `53dc454` before repaired-candidate calls. The correction uses
the exact full represented 2×2 whitening determinant, preserving every entry.
Scientific scenes and acceptance criteria did not change.

Canonical source was frozen at local commit `4ac158c`. The operator SHA-256 is
`5038ebe359ae0b3e4e158273ae145a0991feb93258fe723eca942ac49017425f`;
the new runner is
`835814c5c9bf23d1f8945474ca9b9412ae5a12ff0f358d0e09b6e8bea9d5cdc6`.
All 38 bound source files match before and after the canonical execution.
The original probability, four-column Jacobian and inverse callers are unchanged.

## Complete numerical outcome

| Population | Scenes | Query comparisons | Positive-area checks |
| --- | ---: | ---: | ---: |
| Original synthetic regression | 337 | 3,886 / 3,886 pass | 36 / 36 pass |
| New prospective synthetic cases | 80 | 946 / 946 pass | 36 / 36 pass |
| Complete retained population | 417 | 4,832 / 4,832 pass | 72 / 72 pass |

The independent oracle integrates the original source chord at orders 96 and
192, with its own exact determinant and scalar Cholesky calculation. It shares
no production geometry, determinant or first-moment helper. Both comparisons
retain the candidate estimate, independent arithmetic allowance, twice the
order discrepancy, omitted tails and final reduction allowance. The first tests
estimated-error coverage; the second tests the requested tolerance with that
same oracle allowance. Neither is a certified enclosure.

All 4,832 oracle order comparisons converge under the frozen criteria. Across
the complete population, the candidate charges 80,728 evaluation units and
8,864 panels, including discarded work. The largest candidate/oracle discrepancy
is `1.2027157936245203e-8`; its allowance is explicit in the full report. A pass
does not mean that every discrepancy is below its requested tolerance without
the stated oracle allowance.

The unchanged independent positive-area helper supplies means at two orders
and four angular sides (`±h`, `±h/2`) for 24 selected scenes. All 72 checks retain
the raw means, derivative-order differences, noncancelling `1/h`-amplified
mean-order discrepancies, step/half-step comparison and Richardson comparison. No order, step,
scene or threshold was tuned after evaluation.

## Original failures and independent elementary corroboration

| Original case | V2 result at the original `1e-10` request | High-precision reference error |
| --- | --- | ---: |
| `compressed-chart-e16-d0.0001` | Resolves in 356 panels / 12,232 evaluation units; V1 exhausted 4,096 panels / 154,388 units | `4.46595e-12` |
| `compressed-chart-e16-d1e-06` | Resolves in 46 panels / 1,100 evaluation units; preserves the earlier determinant-error diagnosis | `2.59484e-11` |

After the canonical run, the separately derived elementary identity was evaluated
at Decimal precisions 180 and 220 on these two saved inputs only. Four
high-precision evaluations used exact binary-float coefficients and Machin's
formula for π. The two precision results agree within `1.3e-175`. Both candidate
errors are below their own error estimates and the original `1e-10` request.
This is explicitly post-hoc corroboration, not a new prospective population,
model replay or a formally verified transcendental interval.

It also exposes a limitation in the reference quadrature. For the first case,
the oracle192 error is approximately `1.47257e-10`, exceeding its combined saved
allowance `9.95417e-11`, even though both orders nearly agree. The candidate is
closer to the high-precision reference. Computing a small projective denominator
near an endpoint can amplify mapped-node rounding; two orders can share that
bias. This is a diagnosis hypothesis, not a repaired-oracle qualification.
The full canonical pass remains a pass of its frozen empirical criteria;
neither the oracle allowances nor all candidate estimates become certified bounds.

## Software and saved-data verification

The first focused run passes all 94 unchanged contracts plus 38 new controls
(132 total). The inverse-domain correction adds six controls; all **138** pass.
The original 38-test source prefix and all initial receipts remain preserved.
The full Python suite first passes 1,081 tests. Repository lint then identifies
one nested conditional; its equivalent short-circuit form is committed and the
complete final-source suite again passes **1,081 tests**, with runtime warnings
treated as errors. All **432 bound non-Markdown files** and **22 built frontend
files** match before and after that final run. Build, full lint and new-file
format checks pass. Earlier lint failures and a metadata-correction sidecar are
retained, without changing any scientific threshold.

The runner passes 26 invented-payload/CLI contracts with NumPy/backend imports
blocked and zero actual derivative, mean, oracle or area calls. The independent
saved-report auditor passes **1,662,242 checks** with zero failures, reconciling
source pins, populations, work, oracle partitions, all comparison allowances and
the positive-area arithmetic. A separate review passes **811,482 saved-data
checks**, including all source/query/role bindings, oracle forests and area
calculations. Its first passing receipt remains alongside the final checker and
receipt after an unused-variable lint cleanup. These verify saved consistency, not density nodes
or error-bound validity. The high-precision observation above remains a limit
even when saved-data auditing succeeds.

All **90 Markdown files** parse; **1,004 local references**, **94 heading
fragments** and **118 tables** pass. The documented V2 portable workflow
verifies compressed/decoded artifacts and reproduces the saved audit. The V1
workflow also passes in its separate, unchanged source checkout, preserving its
original failed protocol. All **427 other inherited non-Markdown files** remain
byte-identical to the PR #98 base; only the intended operator is changed.
The primary checkout remains clean at `d747e30`. No full browser run or new
library release is claimed by these developer-only changes.

No optimizer, renderer, old residual/photo-archive analysis, automatic tracing
integration or physical acquisition is run. The earlier residual study's unknown
normal columns are not relabeled. Angle identifiability, optical adequacy,
thickness/illumination models and preservation of accepted geometry through CAD
still need separate evidence before adopting a normal-aware inverse in the app.
