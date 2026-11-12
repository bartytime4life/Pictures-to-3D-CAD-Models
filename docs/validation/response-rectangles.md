# Bounded-input response and mathematical Gaussian covers

This developer candidate is based on published documentation PR #67 at
`b27e48e09079b497d85dea766233db266e13cc90`. It adds exact rectangle-response
feasibility, a strict CLI and outward rational Gaussian bounds. Existing
production tracing, API/UI, CAD generation, dependencies and prior experiments
retain their baseline bytes. The root Makefile adds only a developer study
target. The original checkout and earlier worktrees are preserved.

The [guide](../response-rectangles.md) defines both quantifiers, exact inputs,
proofs, tight extended query bands and the separate CDF API. The earlier
[fixed-input record](response-calibration.md) keeps its original source binding;
this extension does not turn that earlier study's rounded coordinates into
certified optical probabilities.

## Rectangle reduction and independent verification

For one continuous nondecreasing response, a rectangle `[a,b] x [L,U]` can
contain a selected graph point exactly when `f(a) <= U` and `f(b) >= L`.
The image of the interval is `[f(a),f(b)]`; continuity supplies every intermediate
output. Requiring every allowed input instead gives `f(a) >= L` and `f(b) <= U`.
Both quantifiers use one common function and common secant bounds. Original
nondegenerate intervals are not merged as though they were duplicate exact knots.

Endpoint reachability uses genuine half-infinite intervals. `null` lower/upper
query bounds represent negative/positive infinity, separately from unavailable
queries and finite response witnesses. A compatible result retains one finite
piecewise-linear curve and actual per-rectangle assignments. Incompatibility
retains a strict inequality transported from original source endpoints.

The [independent oracle](../../studies/verification/response-rectangles-oracle-v1.py)
checks original-rectangle cone constraints and generic exact difference-constraint
closure instead of production chain recurrences. Its
[complete receipt](../../studies/results/response-rectangles-oracle-v1.json)
passes **390 checks**, with zero failures: 372 mathematical cases and 18 controls.
There are 142 compatible and 230 incompatible cases, including 36 original
selected-input graph comparisons and 76 fixed-slope/intercept checks. The
population retains both modes, permutations, duplicates, finite and infinite
slopes, overlapping inputs, witnesses and original contradiction provenance.

## Outward Gaussian calculation

For exact `z` in `[-6,6]`, the new helper bounds the supplied mathematical
standard-normal CDF. For `x=abs(z)`, its integral uses

```text
Phi(x) = 1/2 + (1/sqrt(2*pi))*I(x)
I(x) = sum[n>=0] (-1)^n * x^(2*n+1)/(2^n*n!*(2*n+1))
t_(n+1)/t_n = x^2*(2*n+1)/(2*(n+1)*(2*n+3))
```

Directed integer rounding on a `10^-60` grid encloses each term and partial sum.
After `N` included terms, `x^2/(2*(N+1)) < 1` bounds every later term ratio;
the alternating remainder lies between zero and the signed first omitted term.
The certificate records those bounds. Machin's arctangent identity and exact
integer-square-root inequalities enclose the normalization; negative inputs use
reflection. Final outward decimal rounding gives width at most `2*10^-places`,
with requested places 1–30 and at most 256 terms. Insufficient work refuses the
calculation without claiming an optical/model contradiction.

The series follows [NIST DLMF 7.6.1](https://dlmf.nist.gov/7.6.E1), with the
[arctangent expansion](https://dlmf.nist.gov/4.24.E3) supplying the constant
bounds. Directed arithmetic and remainder handling are implemented here; the
identities do not qualify a camera's PSF or inferred geometry.

The [independent CDF audit](../../studies/verification/normal-cdf-bounds-oracle-v1.py)
uses a positive error-function series, a separate positive exponential series
with geometric tail bounds, `pi=4*(atan(1/2)+atan(1/3))` and rational bisection for
normalization. It also replays every production certificate field. Its
[canonical receipt](../../studies/results/normal-cdf-bounds-oracle-v1.json)
passes **93 checks**, including 50 named/grid/seeded CDF cases, reflections,
resource refusals and deliberately altered certificate controls. The saved-record
audit helper performs no production CDF call. Injected computation failures
remain in the complete population rather than aborting later checks.

## Complete finite refinement experiment

The [plan](../../studies/response-rectangles-v1.json) fixes nine source positions
from −2 to 2, nine candidate offsets from −1/4 to 1/4 in steps of 1/16, four
calibration regimes, two additional observation halfwidths and CDF precision
levels 6, 12, 24 and 30. Sigma is supplied as one. The same nine-position truth
profile is reused throughout; rows are hypotheses, not independent captures.

The supplied response is `h(u)=u+(3/20)*u*(1-u)`, whose derivative on `[0,1]`
lies in `[17/20,23/20]`. Truth output bands contain `h` applied to an outward
30-place CDF cover, plus the declared additional halfwidth 0 or 1/1024.
Consequently zero additional halfwidth still includes a numerical generation
cover, rather than silently treating an approximate output as exact.

Every candidate retains its original rectangles and both quantifiers' full
witness/assignment or contradiction evidence in
[the complete result](../../studies/results/response-rectangles-v1.json).
All **288 rows** are retained with zero execution failures. The 292 shared CDF
covers and all 219 observed coarse/fine nesting checks are also retained.

| Classification | Rows | Conditional meaning |
| --- | --- | --- |
| `excluded_by_outer_boxes` | 200 | Even the Cartesian outer relaxation is incompatible, excluding the supplied analytic input vector |
| `one_response_for_all_covered_inputs` | 82 | One response works for every input in the covering rectangles, including their supplied analytic Gaussian vector |
| `undetermined_by_boxes` | 6 | Some-box compatibility and all-box incompatibility leave analytic realizability unresolved |

These are logical statements under supplied mathematical assumptions, not
physical confidence levels. No midpoint substitutes for an interval, and no
some-box witness alone is promoted to an analytic optical-model certificate.

With normalized endpoints only, all nine candidate offsets have every-input
witnesses at all precision/observation settings. With five exact or bounded
patches plus slopes, the nonzero tested offsets are excluded. At zero additional
observation halfwidth, truth stays box-undetermined at precisions 6, 12 and 24;
precision 30 supplies an every-input witness. Those are the six retained
undetermined rows. At halfwidth 1/1024, truth has every-input witnesses at all
four precisions. Incorrect identity patches exclude every tested offset in this
population, including truth. A finite empty offset grid does not exclude the
entire continuous offset domain.

Seven named controls retain midpoint rejection, two different outputs at one
nondegenerate input interval, strict-slope quantifier differences, genuinely
unbounded marginals, finite-upper-slope narrowing, shared-offset correlation
and a rounded float outside a 30-place mathematical Gaussian cover. The shared
offset example is compatible only after relaxing its coupling; neither solver
mode is claimed to estimate that coupled parameter.

The [separate replayable audit](../../studies/verification/response-rectangles-study-audit-v1.py)
reconstructs rectangles from the plan and covers without calling production
calibration functions. Its [canonical receipt](../../studies/results/response-rectangles-study-audit-v1.json)
passes **1,733 checks**, including all 288 rows, 576 mode results, 170 common
witnesses, 406 original-source contradictions, 292 independently replayed CDF
certificates, 219 nesting checks, seven named controls and all 32 summaries.
There are zero failed checks. Sixteen CLI, tamper and independence contracts
also pass: corrupted rows/certificates remain visible, later rows are checked,
duplicate JSON keys are refused, and saved-record auditing runs with production
imports blocked.

## Reproduce

```bash
make response-rectangles-study OUTPUT=.local/rectangle-study-new.json
.venv/bin/python studies/verification/response-rectangles-oracle-v1.py --output .local/rectangle-oracle-new.json
.venv/bin/python studies/verification/normal-cdf-bounds-oracle-v1.py --output .local/cdf-oracle-new.json
.venv/bin/python studies/verification/response-rectangles-study-audit-v1.py --run studies/results/response-rectangles-v1.json --output .local/rectangle-study-audit-new.json
.venv/bin/python -m pytest -q tests/test_response_rectangles.py tests/test_response_rectangles_cli.py tests/test_normal_cdf_bounds.py
```

Use fresh output files. Help, missing required arguments and existing/dangling
output refusals run no study population. Seven separately executed study-command
contracts pass, including an injected first-case failure that retains all 288
rows and checks the following 287. The strict CLI separately has 70 focused
tests; the core has 32 and the CDF has 20, for **122 focused tests passed**.
No server, photograph, native CAD/slicer application or language model is needed.

## Source binding and regression

The published parent revision identifies the base checkout, with uncommitted
new-source context retained at execution. It does not claim the new code already
exists in that parent. Per-file hashes bind the actual implementation; sources
are checked before and after the canonical runs. The full regression snapshot
contains 161 frozen source/plan files. Independent CDF/study auditors have their
own source-bound receipts and are separate from that full-suite snapshot.

The full Python regression passes **1,446 tests** with zero failures, errors or
skips in **233.67 seconds**. The [regression receipt](../../studies/results/response-rectangles-regression-v1.json)
binds all **161 frozen files**, checked unchanged after execution. Fresh frontend
typecheck/build and Ruff pass. Existing production source is unchanged, so no
new browser behavior or physical qualification is inferred from this
developer-only extension.

| Source | SHA-256 |
| --- | --- |
| [backend/response_rectangles.py](../../backend/response_rectangles.py) | `674b151b9e8038922aaf234e4919ef96796e9eb326601ee8f720400cb8d2e5e6` |
| [backend/normal_cdf_bounds.py](../../backend/normal_cdf_bounds.py) | `d736eac5fa2c5fa625f86fc70a6b7b78ea534666ddfef49d6600c44a18f45f1d` |
| [backend/response_calibration.py](../../backend/response_calibration.py) | `b8a1c4acf8b5d70db3c3de10c9c2e1972af3bbff7f82193bb1f2e9fdc9a56aa4` |
| [scripts/response_rectangles.py](../../scripts/response_rectangles.py) | `d02ef3888854efb2be3258a6f1b44847b3bdfa7772a4b0f048f2303f0fac941a` |
| [scripts/response_rectangles_study.py](../../scripts/response_rectangles_study.py) | `2ac44e8d70eccc1204ee1cfdfa83d53b1421119e2d890ba24bb65d59571bb862` |
| [studies/response-rectangles-v1.json](../../studies/response-rectangles-v1.json) | `b75def08763538865e051be8801bcdba9846159ca7eab7b55556321f51f2e276` |
| [studies/verification/response-rectangles-oracle-v1.py](../../studies/verification/response-rectangles-oracle-v1.py) | `662120ebbeb737355eccc841ce3f648238ef6f31ea6ce33f297dce18fe73a36c` |
| [studies/verification/normal-cdf-bounds-oracle-v1.py](../../studies/verification/normal-cdf-bounds-oracle-v1.py) | `cf8ffca829c0e249db92bed19150843cad8b6d6ffae8fb16d7ae5e4e741801b8` |
| [studies/verification/response-rectangles-study-audit-v1.py](../../studies/verification/response-rectangles-study-audit-v1.py) | `eb6d66d09ef5f34b51b0953676b08584e723a98878ce63fbd23d4357110b9151` |

## Documentation coverage

Coverage includes the earlier [89-document inventory](documentation-response-state.md#coverage-inventory)
plus the new [rectangle/CDF guide](../response-rectangles.md) and this record.
Current navigation, mathematical contracts, command help and source/review state
are updated; historical receipts and library release/generated artifacts retain
their original bindings. All **91 Markdown documents**, **1,384 local links**,
**86 fragments** and **150 tables** pass the repository-wide structural check.
The five new command-help paths, root `make help`, and guide JSON/Python examples
also pass; these checks do not start a service or download a model.
The existing companion-library suite passes **19 documentation tests**. No
generated-reader input or output, PDF, archive or release metadata is refreshed.
