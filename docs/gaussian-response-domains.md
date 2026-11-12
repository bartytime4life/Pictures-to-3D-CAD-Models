# Shared Gaussian edge and response domains

This developer tool encloses continuous candidate domains for one scalar edge
offset and one positive Gaussian blur width. Every observation uses the same
offset, blur width and continuous nondecreasing response, with externally
supplied calibration and slope bounds. It retains certified, excluded and
unresolved joint parameter boxes. It does not calibrate a camera, correct an
image, select a production trace or add a workbench accuracy label.

Start with [bounded-input response quantifiers](response-rectangles.md) for the
underlying rectangle test, [exact-input calibration](response-calibration.md)
for fixed calibration nodes, and the [developer catalog](developer-tools.md)
for separate research commands. The [complete development and validation record](validation/gaussian-response-domains.md)
contains all 27 analyses, independent replay, source bindings and the joint-box figure.

## What one parameter pair means

For exact supplied scalar positions `p_i`, the declared optical inputs are

```text
u_i(e,sigma) = Phi((p_i-e)/sigma),  sigma > 0
L_i <= f(u_i(e,sigma)) <= U_i
```

`Phi` is the mathematical standard-normal CDF. Positions, offset `e` and blur
width `sigma` must use the same coordinate unit. The CDF output is dimensionless;
the response output has the units of the supplied observation bands `[L_i,U_i]`.
Unit labels do not convert values or establish those physical assumptions.
Response slopes are measured per normalized CDF input, not per position unit.

At one candidate pair `(e,sigma)`, feasibility asks whether **one common response
`f`** satisfies all observations, exact-input calibration constraints and common
secant slope bounds. It cannot choose a different response or parameter pair for
each observation. A different candidate pair can have a different response
witness: the tool is enclosing a set of hypotheses, not fitting one response
simultaneously to every alternative hypothesis.

The response permits plateaus when its lower slope is zero. External constraints
must justify any finite upper slope or positive lower slope. An output unit
label such as a normalized level does not impose an unstated response range.

## Run a declared example

After [workbench setup](development.md), save this as
`gaussian-domain-input.json`:

```json
{
  "version": 1,
  "units": {"position": "declared coordinate unit", "output": "declared level"},
  "observations": [
    {"position": "0", "output": ["0.3", "0.7"]}
  ],
  "calibration": [
    {"input": "0", "output": ["0", "0"]},
    {"input": "1", "output": ["1", "1"]}
  ],
  "offset_bounds": ["-0.25", "0.25"],
  "sigma_bounds": ["0.75", "1.25"],
  "slope_bounds": ["1", "1"],
  "tolerances": ["0.01", "0.01"],
  "cdf_places": 24,
  "max_boxes": 127,
  "max_depth": 24
}
```

```bash
.venv/bin/python scripts/gaussian_response_domains.py gaussian-domain-input.json --output .local/gaussian-domains-new.json
```

Run from the repository root with a fresh output path. The required `--output`
saves the complete JSON report; standard output contains the same report.
No server, photograph, native CAD/slicer application or language model is needed.
The example declares the identity response through its anchors and slopes.
Its observation band admits the entire supplied parameter box, so the expected
certificate is `universal_response`, rather than an estimated offset or blur.

## Order can settle a domain without numerical covers

Positive Gaussian blur preserves position order: `p_i <= p_j` implies
`u_i(e,sigma) <= u_j(e,sigma)` for every allowed parameter pair. Therefore
`L_i > U_j` contradicts every nondecreasing response and excludes the whole
parameter domain. Equal-position observations must also share a single response
value. This is an analytic order contradiction, not rejection of sampled grid
points.

A separate constructive case is available when slopes are `[0,null]` and
calibration inputs are only zero and one, or no calibration nodes are supplied.
The ordered groups of calibration-at-zero, observed positions and
calibration-at-one can admit consistent nondecreasing output levels. Interpolating
those levels at the **actual analytic Gaussian inputs** then constructs a
piecewise-linear response for each `(e,sigma)`. The response can vary with the
parameter pair while remaining shared by all its observations.

This `ordered_response_family` certificate proves `for every pair, there exists
one response`. It does not estimate a single response or require numerical CDF
covers to be independently realizable. Its assumptions do not extend to a
positive lower slope, finite upper slope or arbitrary interior calibration knots.
The default slopes with only endpoint calibration can therefore leave the whole
prior feasible, even with exact observations. That is model ambiguity, not an
estimated offset or blur width.

## How numerical covers classify a box

For a closed box `B=[e_lo,e_hi] x [sigma_lo,sigma_hi]`, with `sigma_lo > 0`, the
solver bounds each standardized coordinate using the four corner values

```text
(p_i-e_lo)/sigma_lo    (p_i-e_lo)/sigma_hi
(p_i-e_hi)/sigma_lo    (p_i-e_hi)/sigma_hi
```

Their minimum and maximum enclose every `(p_i-e)/sigma` in the box. Using all
four corners handles either sign of `p_i-e`; a single assumed direction of blur
monotonicity would not suffice. Outward CDF evaluations then cover every analytic
`u_i` by an input interval. Each interval and its declared output band becomes
one rectangle; exact-input calibration constraints retain their fixed inputs.

These input intervals form a Cartesian outer relaxation. They contain the
shared analytic input vector for every pair in `B`, but they can also contain
vectors that no common `(e,sigma)` generates. The two
[rectangle quantifiers](response-rectangles.md#choose-the-input-quantifier)
therefore have distinct roles:

| Box result | Sufficient test | Meaning |
| --- | --- | --- |
| Excluded | `some` is incompatible | No response fits even the relaxed rectangles, so no parameter pair in this box satisfies the supplied analytic model |
| Accepted, `universal_response` | `all` is compatible | One fixed response works for every covered input, and therefore for every analytic parameter pair in this box |
| Unknown | No available certificate settles the box | Analytic feasibility remains unresolved; relaxed selections alone cannot establish it |

The `universal_response` certificate has the stronger witness `there exists one
f, for every pair in B`. It differs from the analytic `ordered_response_family`
certificate above. Both prove that every parameter pair in the accepted box is
feasible, but only the former supplies one fixed response throughout that box.
Different accepted boxes need not share a witness. Conversely,
`all` incompatibility does not show that a box contains an infeasible analytic
pair: every pair might fit with a different response. A `some` witness alone
does not certify even one analytic pair, because its separately selected inputs
may violate the shared offset or blur relationship.

These classifications are logical certificates under the declared model, not
confidence levels or probabilities. Invalid requests and failed numerical
calculations are not evidence of incompatibility.

## Refinement preserves unresolved regions

When a box is unresolved, the search bisects a coordinate selected by normalized
width and applies the same tests to its children. Resolution, depth and box-work
limits stop refinement without converting the remaining region into an
exclusion. Unknown terminal boxes stay in the outer set with their stopping
reasons.

The retained tree must cover the entire closed root domain. Closed children
share their split face: this boundary overlap is intentional and must not be
treated as a lost region or counted twice as evidence. Tree coverage and a lack
of unresolved boxes answer different questions. An exhaustive cover may still
include unknown leaves.

The supplied root domain is a search prior. Its limits are not bounds inferred
from an image. A result only concerns that domain; it makes no assertion about
offsets or blur widths outside it.

More refinement does not promise a fully classified result at a finite
resolution. Exact constraint boundaries, non-identifiability, the stronger
common-response box certificate and numerical enclosure widths can leave
unknown regions. Smaller boxes or narrower CDF covers can help particular cases;
they do not establish a general convergence or identification guarantee.

## Retain joint boxes when reading projections

The inner set is the union of joint `(e,sigma)` boxes accepted by either
certificate kind. The outer set retains accepted and unknown boxes.
Under the supplied model, the feasible set
lies between those unions; excluded boxes contain no feasible parameter pair.

Coordinate projections and their enclosing intervals are summaries. An offset
in one retained box and a blur width in another do not necessarily form a
retained pair. An enclosing projection interval can also bridge gaps between
separate boxes. Use the joint boxes to assess a proposed pair; membership in
both coordinate ranges does not establish joint feasibility.

Even a pair in an unknown joint box is only retained, not certified. A nonempty
outer set with an empty inner set is unresolved. An empty outer set excludes the
entire supplied prior under the mathematical assumptions; it does not diagnose
which physical assumption or measurement was wrong.

## Read the result and its tree

The CLI nests the core result under `analysis`. The core returns a JSON-ready
dictionary; it is not a calibration object with a `.query()` method.
Computed exact values use rational strings such as `"1/4"`; these are result
syntax, whereas the CLI accepts decimal-string model inputs.

| Field | Interpretation |
| --- | --- |
| `nodes` | Retained tree, including parent/depth, exact `box`, status, reason, proof kind, evidence and any children |
| `inner_node_indices` | Accepted leaves; either accepted proof kind certifies every pair in each listed joint box |
| `unknown_node_indices` | Retained leaves not settled by a certificate |
| `excluded_node_indices` | Leaves proved infeasible under the supplied model |
| `outer_node_indices` | Accepted plus unknown leaves, excluding internal split nodes |
| `outer_projection` | Coordinate hulls `offset` and `sigma`, or `null` for each when the outer set is empty; these are not a joint feasible box |
| `cdf_evaluations` | Cached outward CDF records and their numerical certificates |
| `summary` | Evaluated/created counts, leaf counts, CDF count, response arithmetic work and whether feasibility was certified or remains unresolved |

Node statuses are `accepted`, `excluded`, `unknown` or internal `split`.
`proof_kind` distinguishes `ordered_response_family`, `universal_response`,
`invariant_order_contradiction` and `rectangle_contradiction`. Numerical nodes
retain `some`/`all` witnesses or contradictions and `input_covers` that reference
the shared CDF record array by `lower_cdf` and `upper_cdf` indices. Reconstruct
their rectangles from the fixed calibration nodes followed by those observation
covers. Evidence source indices use that same order: calibration first, then
observations, all zero-based. `observation_index` separately indexes the original
observation list.

Order certificates retain `order_evidence`, including grouped source indices,
output intersections and selected levels or a strict contradiction. A group's
`coordinate` is an observation position or an endpoint calibration input, as
identified by its `kind`; those two coordinate types are not interchangeable.

The top analysis status is `unresolved` whenever unknown leaves remain, even
when some accepted regions are also present. With no unknown leaves, it is
`compatible` if there are accepted leaves, otherwise `incompatible`.
`summary.has_certified_feasible_parameters` records whether the inner set is
nonempty. `summary.feasible_parameters_exist` is `true` when feasibility is
certified, `false` when the whole prior is excluded, and `null` when no accepted
region was found but unknown leaves remain. A null existence answer is distinct
from an empty feasible set.

## Input contract and computation limits

Version 1 requires `version`, `units`, `observations`, `offset_bounds` and
`sigma_bounds`. Each observation has exactly `position` and `output`; each
optional calibration node has exactly `input` and `output`.
Both rectangle tests are selected internally; there is no `input_mode` option.

| Optional field | Default | Allowed values |
| --- | --- | --- |
| `calibration` | `[]` | 0–128 exact-input nodes; calibration inputs lie in `[0,1]` |
| `slope_bounds` | `["0",null]` | Ordered `0 <= lower <= upper`, with `null` only for an unbounded upper slope |
| `tolerances` | `["0.01","0.01"]` | Positive absolute widths in offset/sigma order, using the declared coordinate unit |
| `cdf_places` | `24` | Integer 1–30 |
| `max_boxes` | `127` | Integer 1–4,095 |
| `max_depth` | `24` | Integer 0–48 |

There must be 1–32 observations. Every interval is closed and ordered;
zero-width parameter intervals are allowed, but the whole sigma interval must
be strictly positive. Numeric model values are exact decimal strings. Only
`version`, `cdf_places`, `max_boxes` and `max_depth` use JSON integers; booleans
are not integers for this contract. Unknown fields, duplicate keys, non-finite
JSON constants and numeric/boolean model values are refused. Files are limited
to 512 KiB. `units` contains exactly `position` and `output`, each a nonempty
printable label of at most 80 characters.

The shared parser allows at most 160 characters and 40 coefficient digits per
decimal string after removing leading zeros; trailing zeros count. Both decimal
and adjusted exponents have absolute value at most 64. Parsed exact numbers have
at most 512 bits in the absolute numerator and denominator. Response propagation
uses the [rectangle tool's arithmetic limits](response-rectangles.md#input-provenance-and-api):
8,192-bit rational results and a separate 250,000,000-unit work budget per call.
The CDF helper uses at most 256 terms. These computational limits do not express
a measurement error budget or a latency guarantee.

Only the numerical fallback requires all root-box standardized coordinates to
lie in `[-6,6]`. An unsupported numerical root refuses the whole request rather
than clipping it. An analytic order contradiction or response-family certificate
does not evaluate a CDF and can therefore settle otherwise valid finite inputs
outside that numerical domain. All schema and basic resource checks still apply.

The numerical search visits boxes in breadth-first order. It bisects the larger
`width/tolerance`, with offset winning a tie. `max_boxes` limits evaluated boxes,
not created tree nodes or CDF calls; children already created when that budget
is reached remain unknown with reason `box_limit`. Other unknown reasons are
`tolerance`, `depth_limit` and `numerical_or_arithmetic_limit`; the latter retains
the error text. Raising a budget never turns a prior unresolved result into
physical evidence.

The Python entry point is
`analyze_gaussian_response(observations, calibration=(), *, offset_bounds, sigma_bounds, slope_bounds=("0",None), tolerances=("0.01","0.01"), cdf_places=24, max_boxes=127, max_depth=24)`
in [backend/gaussian_response_domains.py](../backend/gaussian_response_domains.py).
It uses the shared exact parser, accepting decimal strings, bounded Python
integers and `Fraction` values while refusing binary floats and booleans.
The CLI keeps the narrower decimal-string input contract.

## Exit status and provenance

The CLI report format is `pictures-to-cad-gaussian-response-domains-result`,
version `1`, with `units`, the parsed submitted `input`, normalized `analysis`
and `provenance`. Exit **0** means a valid report was produced, including an
`incompatible` or `unresolved` analysis. Read `analysis.status` and its retained
evidence; the exit code alone does not distinguish those outcomes. Invalid
requests, unsupported numerical root domains, source changes and file errors
exit **2** with a brief message on standard error. A local numerical/arithmetic
limit retained as an unknown leaf still belongs to a valid unresolved report.

Existing output files and symlinks are refused. Choose a new filename to preserve
earlier results; missing parent directories are created after analysis succeeds.
No output file is written unless the required `--output` is supplied.

`provenance.input_sha256` binds the raw UTF-8 request bytes, including whitespace.
`provenance.source_sha256` binds five files: the shared exact parser
`backend/response_calibration.py`, rectangle solver `backend/response_rectangles.py`,
CDF helper `backend/normal_cdf_bounds.py`, domain solver
`backend/gaussian_response_domains.py` and this tool's
[CLI](../scripts/gaussian_response_domains.py). Source hashes are checked before
and after analysis. `provenance.git` records the revision and dirty-file entries;
unavailable Git metadata uses null fields with a reason. `provenance.python`
records the interpreter version. Keep these with the external evidence used to
choose the supplied bounds. A revision alone does not identify uncommitted code.

Reports and terminal logs retain measurements, unit labels and repository
filenames. Review them before sharing, as described in
[report privacy and retention](privacy-security.md#numerical-reports).

## Mathematical and physical scope

The standard-normal helper supplies numerical enclosures at exact declared
coordinates. Its directed rounding, series remainder and normalization bounds
do not establish that a capture has a Gaussian PSF, a straight edge, exact
sample positions or a spatially shared response. Supplied observation bands
must separately account for the intended processing stage and measurement
errors. This model does not infer a noise distribution, undo encoding, model
pixel-aperture integration or resampling, or provide a physical fit guarantee.

The method follows the set-inversion idea of enclosing a feasible parameter set
between inner and outer unions of boxes. See
[Jaulin and Walter (1993)](https://webperso.ensta.fr/Jaulin/paper_automatica93.pdf),
*Set Inversion via Interval Analysis for Nonlinear Bounded-error Estimation*,
[DOI](https://doi.org/10.1016/0005-1098(93)90106-4).
This implementation uses response-rectangle certificates for its narrower
supplied model. The paper's convergence results are not a qualification of this
implementation, its finite resource limits or any physical camera.
