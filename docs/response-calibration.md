# Conditional bounds on one common response

This developer tool asks whether supplied input knots and output intervals can
belong to **one nondecreasing scalar function**, under optional slope bounds.
It returns exact compatibility evidence, tight pointwise bands and a common
piecewise-linear witness. It does not estimate a camera response from photos,
correct an image, compute an inverse, or change the workbench trace or UI.

Use the [developer-tool catalog](developer-tools.md) for related numerical tools,
[raw-source fitting](raw-source-fit.md) for supplied optical means, and
[data handling](privacy-security.md) for the separate photo-upload workflow.

## Declare the quantity and processing stage

Choose the direction of the function before preparing inputs. For example,
`x` might be an independently established relative exposure and `f(x)` its
recorded channel value. All nodes must describe the same function at the same
processing stage, with consistent units, exposure conventions and channel.
The tool does not infer those relationships or combine separate per-node curves.

Input knots are exact supplied values, not input-uncertainty intervals. Output
bands are closed intervals supplied by the caller; equal endpoints specify an
exact value. Exact arithmetic preserves these declarations without establishing
that the measurements or their bounds are physically correct. Unit labels are
text metadata, not dimensional validation or evidence of radiometric calibration.

An input interval cannot be supplied through this version-1 schema. Replacing
it by its midpoint changes the question and can reverse compatibility. Likewise,
converting a rounded Gaussian evaluation to an exact rational preserves that
computed number; it does not certify an enclosure of the mathematical Gaussian
value. Keep those input-model limitations separate from exact propagation of
the supplied values.

For every pair `x1 < x2`, the declared model requires

```text
lower_slope * (x2 - x1) <= f(x2) - f(x1)
f(x2) - f(x1) <= upper_slope * (x2 - x1)  # when an upper bound is supplied
```

Slopes have output units per input unit. The lower bound must be nonnegative;
the upper bound, when present, must be at least the lower bound. Defaults
`["0", null]` require nondecreasing behavior without a finite upper slope.
With the default zero lower slope, flat sections are allowed; nondecreasing
behavior alone does not imply an invertible response.

The domain is the closed span of the supplied knots. There is no extrapolation.
With one distinct knot, only that input can be queried. Duplicate input values
constrain the same output: their bands are intersected and original source
indices are retained. Disjoint duplicate bands are incompatible evidence,
rather than permission to use different responses.

## Exact interval propagation

After intersecting duplicate knots, sort `x_i` and write their bands as `I_i`.
For adjacent distance `d = x_i - x_(i-1)`, the reachable interval propagates as

```text
F_0 = I_0
F_i = I_i intersect [F_(i-1).lower + m*d, F_(i-1).upper + M*d]
```

An empty intersection proves incompatibility. A backward pass intersects each
`F_i` with values able to reach the next tightened interval, now using
`d = x_(i+1) - x_i`:

```text
B_last = F_last
B_i = F_i intersect [B_(i+1).lower - M*d, B_(i+1).upper - m*d]
```

Here `m` and `M` are the supplied slope bounds. With no finite `M`, omit the
corresponding bound. The tightened intervals are exact knot marginals for this
one-dimensional chain. Starting at `B_0.lower`, choose each next value as the
larger of its own lower bound and the preceding witness value plus `m*d`.
Linear interpolation gives a common admissible response. Adjacent secant bounds
also imply every longer secant bound by summing their inequalities.

Between adjacent knots, the query bounds intersect the left and right slope
cones; they do not interpolate one selected witness as if it were unique.
All arithmetic uses rational numbers, with explicit finite resource caps.
An [independent graph oracle](validation/response-calibration.md) checks the
chain using general difference constraints instead of these recurrences.

## Run an exact example

After [workbench setup](development.md), save this as `response-input.json` in
the repository root. These are synthetic normalized anchors and an assumed
slope bound, not camera measurements:

```json
{
  "version": 1,
  "units": {
    "input": "relative exposure",
    "output": "normalized recorded level"
  },
  "nodes": [
    {"input": "0", "output": ["0", "0"]},
    {"input": "1", "output": ["1", "1"]}
  ],
  "slope_bounds": ["0", "2"],
  "queries": ["0.4", "0.5", "0.6"]
}
```

```bash
.venv/bin/python scripts/response_calibration.py response-input.json --output .local/response-result-new.json
```

Run from the repository root and choose a fresh output file. `--output` is
required; the complete JSON report is both saved and printed to standard output.
The command does not need a running CAD server, image, native application or
language model. There is no `--demo` or photograph-input mode.

The example is compatible. Its tight query bands are:

| Input | Possible output |
| --- | --- |
| `0.4` | `[0, 0.8]` |
| `0.5` | `[0, 1]` |
| `0.6` | `[0.2, 1]` |

The reported witness joins `(0,0)` and `(1,1)`, so its value at `0.5` is `0.5`.
That witness proves existence; it need not attain either end of a query band.

## A pointwise band is not a set of independent choices

Each end of a tight pointwise band is attainable by some admissible response.
Different queries can require different responses to attain their endpoints.
Selecting an arbitrary value from every band does not prove that those choices
belong to one common function.

For example, `f(0.4) = 0.8` and `f(0.6) = 0.2` each fit its individual band
above. Together they contradict nondecreasing behavior. To test that joint
claim, append both as nodes and run the tool again:

```json
[
  {"input": "0.4", "output": ["0.8", "0.8"]},
  {"input": "0.6", "output": ["0.2", "0.2"]}
]
```

This is a fragment to add to the example's `nodes`, not a standalone CLI input.
The complete amended request is incompatible. Merely requesting both inputs in
`queries` would not impose the two extra output observations.

## Interpret compatibility and refusals separately

| Outcome | Meaning |
| --- | --- |
| `compatible` | At least one function satisfies all supplied bands and slope constraints on the declared domain; the piecewise-linear witness demonstrates one |
| `incompatible` | Valid supplied constraints contradict one another; the report retains an exact source-indexed inequality, with implied lower output strictly above implied upper output |
| Invalid or resource-limited request | The request could not be evaluated under the implemented contract; this is not mathematical evidence that no response exists |

The report's `calibration` object contains `status`, `source_groups` (sorted
duplicate intersections), `nodes` (tightened feasible knot bands), `witness`,
`contradiction`, `slope_bounds` and arithmetic `work`. For compatible inputs,
linear interpolation of the witness obeys the slope bounds between knots.
The top-level `queries` list contains tight marginal envelopes inside the domain;
an out-of-domain query is refused for a compatible calibration. Incompatible
calibrations instead report each query as unavailable with
`"unavailable": "incompatible_calibration"`. Do not interpret their empty witness
as a narrow response estimate.

Both compatible and incompatible reports exit with status 0. Invalid requests,
unsupported resource requirements and file errors exit with status 2 and an
error on standard error, rather than a mathematical compatibility result.

Results use exact rational strings such as `"1/2"`, not rounded floating-point
endpoints. These output strings are a representation of computed bounds; CLI
model inputs must use decimal strings. Top-level `input` retains the parsed
submitted request. `provenance` records its raw UTF-8 `input_sha256`, the core and
CLI `source_sha256` values, Git revision/dirty-file metadata and Python version.
Unavailable Git metadata is reported explicitly; the input and source hashes
remain separate from that revision. Keep the report when revising bands or
assumptions; a whitespace-only input change can change its byte hash.

## Input and work limits

The version-1 JSON object requires `version`, `units` and `nodes`.
`slope_bounds` is optional and defaults to `["0", null]`; `queries` is optional
and defaults to `[]`. The schema accepts no other fields. `version` is the
integer `1`, not a boolean. All model and query numbers are decimal strings;
JSON numbers and booleans are refused in those positions. Only the optional
upper slope may be `null`.

- `units` has exactly `input` and `output`: nonempty printable strings of at
  most 80 characters each.
- There must be 1–1,024 nodes, each with exactly `input` and a two-value ordered
  `output` band. At most 256 queries are allowed; envelopes are defined only
  inside the knot domain.
- Input files are at most 512 KiB. Duplicate JSON keys, non-finite JSON constants,
  malformed input, unsupported versions and existing output files are refused.
- Exact numbers are bounded by the parser's 160-character, 40-digit, exponent
  and adjusted-exponent limits of magnitude 64, and a 512-bit rational-input cap.
  Rational results are capped at 8,192 bits. Calibration and each separate query
  have their own 250-million-unit arithmetic cap; the reported calibration
  `work` does not include later query calls. The CLI additionally caps query count.
  These are computational limits, not physical error bounds or whole-photo time
  guarantees.

The Python primitive [backend/response_calibration.py](../backend/response_calibration.py)
exports `calibrate_response(nodes, *, slope_bounds=("0", None))`, followed by
`result.query(x)` and `result.to_dict()`. The `*` makes `slope_bounds` keyword-only.
Its public `parse_exact(value)` helper returns a bounded `fractions.Fraction`
without floating-point conversion. The Python API additionally accepts integers
and `Fraction` inputs; floats and booleans are refused. Invalid types and
invalid/resource values raise errors rather than returning a partial
compatibility conclusion. The CLI keeps the narrower decimal-string contract.

For example, run this Python code from the repository root using `.venv/bin/python`:

```python
from fractions import Fraction

from backend.response_calibration import calibrate_response

result = calibrate_response(
    [
        {"input": "0", "output": ["0", "0"]},
        {"input": "1", "output": ["1", "1"]},
    ],
    slope_bounds=("0", "2"),
)
assert result.status == "compatible"
band = result.query("0.4")
assert (band.lower, band.upper) == (Fraction(0), Fraction(4, 5))
```

Check `status` before querying a result. `query` raises `ValueError` for an
incompatible calibration or an input outside its domain; the CLI's
`unavailable` object is wrapper behavior. Source indices are zero-based positions
in the original `nodes` list, before sorting or duplicate intersection. Preserve
that list with a contradiction so its two source bounds can be reconstructed.
The reported contradiction proves a conflict; it does not enumerate every
conflict or claim a smallest inconsistent subset.

## What external evidence still has to supply

One response assumption may fail across channels, spatially varying processing,
changing exposure settings, clipping or local tone mapping. The model does not
identify latent exposure, optical blur, geometry or noise from the same image,
and it does not make a reported interval into an uncertainty budget. A positive
lower slope, finite upper slope and anchor values all need independent
justification for the selected stage and units.

Debevec and Malik's [1997 HDR method](https://people.eecs.berkeley.edu/~malik/papers/debevec-malik97.pdf)
uses multiple exposures and reciprocity assumptions, recovering radiance up to
scale. Grossberg and Nayar's [2003 response-ambiguity analysis](https://cave.cs.columbia.edu/old/publications/pdfs/Grossberg_PAMI03.pdf)
shows why recovering response and exposure requires assumptions that resolve
ambiguities. Those are different estimation methods; this tool only checks
externally supplied constraints. Normalizing anchors to zero and one chooses a
coordinate convention and does not establish absolute radiance or exposure.

Decoding a saved photograph with the standard sRGB curve is an assumed digital
conversion, not a measurement of the camera's complete response. A compatible
response set here does not calibrate that camera or authorize image correction,
an inverse response, a physical likelihood or manufacturing acceptance.

## Repeat the edge and calibration controls

```bash
make response-calibration-study OUTPUT=.local/response-study-new.json
.venv/bin/python studies/verification/response-calibration-oracle-v1.py --output .local/response-oracle-new.json
.venv/bin/python studies/verification/response-calibration-study-audit-v1.py --run studies/results/response-calibration-v1.json --output .local/response-study-audit-new.json
```

All output destinations must be fresh. The fixed study retains every finite candidate,
shared witness or contradiction, alternative edge/response gauges, wrong
calibration, quantization, spatial-response and processing-stage controls.
Its Gaussian-derived float64 coordinates are frozen as exact rational inputs
for a declared synthetic experiment; they are not certified optical probabilities.
The [complete record](validation/response-calibration.md) separates exact model
consistency, finite candidate scans and remaining physical calibration work.
The certificate auditor reads the archived study and checks every witness or
contradiction without calling the production calibrator. A successful replay
checks that archive's declarations; it does not generate new camera evidence.
