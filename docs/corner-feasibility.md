# Conditional corner-radius analysis

This developer tool bounds which radii can explain supplied observations under
one explicit mathematical model. It does not change the workbench's tracing,
CAD geometry or UI, and it does not derive physical error bounds from a photo.
Use it to investigate the [radius/model ambiguity](validation/sharp-corner-resolution.md)
before introducing a correction or an accuracy label.

The model fixes a right-angle corner's apex at `(0,0)`, its material in the
positive X/Y quadrant, a circular fillet, exact observation coordinates and
independent axis-aligned Gaussian blur. Version 1 supplies exact widths and
varies radius only; version 2 supplies blur domains and varies radius and one
shared blur pair. [Version 3](pixel-apertures.md) observes normalized means over
known uniform rectangular pixel apertures. Uncertain pose, coordinate error,
tone response, noncircular geometry, nearby boundaries and model discrepancy
require separate treatment.

## Run the synthetic demonstration

After [workbench setup](development.md), run from the repository root:

```bash
.venv/bin/python scripts/corner_feasibility.py --demo
```

No server, image, AI model or external service is needed. The demonstration
supplies blur widths `(1,1) px`, the apex observation interval `[0.24,0.26]`,
and a radius prior `[0,4] px`. A sharp quadrant has level exactly `0.25` at its
apex. Its observation interval is a synthetic input, not a recommended camera
error budget.

JSON goes to stdout; the demo explanation goes to stderr. Add
`--output corner-result.json` to retain a result, choosing a path that does
not already exist. The CLI refuses overwrites. The full input, exact decimal
bounds, input-byte hash, five implementation-file hashes and Git metadata are
included in the report. An unknown or incompatible analysis is a valid result
and exits 0; invalid input or execution failure exits nonzero.

## Supply a bounded problem

Save this explicit input as a new JSON file:

```json
{
  "format": "pictures-to-cad-corner-feasibility",
  "version": 1,
  "coordinate_unit": "px",
  "points": [["0", "0"]],
  "blur_sigma": ["1", "1"],
  "level_intervals": [["0.24", "0.26"]],
  "radius_domain": ["0", "4"],
  "radius_resolution": "0.1",
  "max_boxes": 64,
  "cells": 32
}
```

```bash
.venv/bin/python scripts/corner_feasibility.py input.json --output result.json
```

All fields are required. Dimensional and level values are **decimal strings**,
preserved without a binary64 conversion. `version`, `cells` and `max_boxes` are
JSON integers; booleans are rejected. Duplicate and unknown fields, nonfinite
numbers and mismatched point/interval counts are refused. A file is limited to
128 KiB, decoded as UTF-8.

| Field | Meaning and numerical limit |
| --- | --- |
| `coordinate_unit` | `px` or `mm`; points, blur and radius must use that same unit |
| `points` | 1–16 exact `(x,y)` pairs; coordinate magnitude at most 1,000,000 |
| `blur_sigma` | Fixed positive `(sigma_x,sigma_y)`, each 0.000001–1,000,000 |
| `level_intervals` | One closed normalized linear-light probability interval in `[0,1]` per point |
| `radius_domain` | Closed supplied prior `0 <= lower <= upper <= 1,000,000`; a singleton is allowed |
| `radius_resolution` | Positive leaf-subdivision stopping width, at most 1,000,000; not a physical uncertainty |
| `cells` | 1–256 cutout-cover strips per probability evaluation |
| `max_boxes` | 1–512 radius-box classifications |

Each decimal string is at most 100 characters. External decimals have at most
40 coefficient digits and, except zero, adjusted
decimal exponents from −12 through 12. The aggregate work setting
`cells × number_of_points × (max_boxes + 1)` must not exceed 65,536. These are
software resource/domain limits, not physical operating specifications.

The level intervals are bounds on the **normalized linear-light model output**,
not pixel-position deviations, radius standard deviations or millimeter error.
The tool does not justify them. If observation error and model discrepancy are
bounded independently, their combined output allowance must be supplied
explicitly; it is not inferred from residual RMS or the existing 0.03 px
heuristic. This CLI does not automatically convert workbench edge traces or
nonlinear image intensities into valid bounded observations.

## Interpret the result

All three versions use the status names and radius `inner`/`outer` sets below. The
remaining field details in this section describe version-1 radius boxes;
versions 2/3 use joint parameter boxes and projections as described next.

| `status` | What is established under the supplied assumptions |
| --- | --- |
| `conditional_compatible` | At least one complete radius box is accepted; the inner set is nonempty |
| `conditional_incompatible` | The outer set is empty; the supplied model, observations, bounds and prior cannot all hold |
| `unknown` | Inner is empty and outer is nonempty; compatibility remains unresolved |

`inner` is the union of accepted boxes. `outer` is accepted plus unknown boxes.
They satisfy `inner ⊆ feasible radii ⊆ outer`. An unknown radius need not be
feasible. `excluded` records rejected regions. Intervals are closed decimal
string pairs; adjacent boxes are merged for display, so a merged unknown
interval can be wider than `radius_resolution`.

`coverage_complete` means no part of the prior was lost during classification,
including on work exhaustion. `classification_complete` means no unknown boxes
remain. `budget_exhausted` and `unknown_reason_counts` distinguish work limits,
radius stopping widths, midpoint stagnation and numerical-enclosure failures.
`boxes_evaluated` counts attempted classifications; `level_evaluations` counts
attempted point/radius evaluations, with cached endpoints reused.

When `prior_ceiling_reached` is true, the outer set reaches the supplied prior's
ceiling. That endpoint is not an image-derived maximum. An empty inner set does
not prove rejection, and rejection does not prove the corner is sharp: the blur,
coordinate frame, level bounds or prior can be wrong. Compatibility does not
determine a unique radius or validate a physical part.

## Joint blur domains: version 2

Use version 2 when independently justified blur bounds are available. Replace
`blur_sigma` with two closed `blur_sigma_intervals`, add two positive numerical
`blur_resolution` stopping widths, and set `version` to 2. Other fields retain
their version-1 meanings. For example:

```json
{
  "format": "pictures-to-cad-corner-feasibility",
  "version": 2,
  "coordinate_unit": "px",
  "points": [["0", "0"]],
  "blur_sigma_intervals": [["1", "2"], ["1", "2"]],
  "level_intervals": [["0.24", "0.26"]],
  "radius_domain": ["0", "0"],
  "radius_resolution": "0.1",
  "blur_resolution": ["0.1", "0.1"],
  "max_boxes": 64,
  "cells": 16
}
```

This is a synthetic sharp-apex control: level `0.25` holds for every positive
blur pair. It does not determine blur. Use the same file command as above;
`--demo` remains the version-1 example. Version 2 requires
`2 × cells × number_of_points × max_boxes <= 65,536`. The other numeric,
string, file and per-field limits remain. Singleton blur intervals are allowed.

The prior is the Cartesian product of radius, sigma-X and sigma-Y domains.
Each parameter box is classified as a whole. **One common blur pair must
satisfy every observation.** Fitting each point with a different pair cannot
establish joint compatibility.

Version-2 reports give `parameter_order: ["radius", "sigma_x", "sigma_y"]`,
`parameter_domain`, and `parameter_boxes` with `accepted`, `unknown` and
`excluded` arrays. Each box contains three closed decimal-string intervals in
that order. `inner` and `outer` remain radius sets:

```text
inner = radius projection of accepted parameter boxes
outer = radius projection of accepted plus unknown parameter boxes
```

Each radius in the inner set has at least one common blur pair satisfying all
observations. Different radii may use different pairs. This does not mean all
prior blurs work or that one pair works for the entire projected radius set.
The outer set retains every possible joint witness, including unresolved boxes.

There is deliberately no version-2 radius-level `excluded` field: a rejected
parameter box can share a radius with an accepted box at another blur. Projecting
rejected nuisance boxes as rejected radii would discard valid answers. The
`coverage_complete` and `classification_complete` flags concern the full joint
domain; `prior_ceiling_reached` concerns its radius projection. Unknown reasons
include `parameter_resolution` when all three stopping widths have been reached.

Blur dependence uses interval division and CDF bounds, not an assumption that
level is monotone in sigma. To limit repeated-CDF dependency loss, each X-strip
mass is also enclosed by strip width times a Gaussian-density interval over the
whole strip and blur domain. Intersecting these two valid mass enclosures keeps
the result valid. The density exponential uses padded correctly rounded Decimal
values. More cells and parameter subdivision can help, but coarse domains,
dependency, tails and work limits can still leave unknowns.

Supplying blur intervals does not justify them or account for model discrepancy.
The family still fixes axes, independence, spatially constant blur, exact point
coordinates and a circular right corner. The [joint-domain validation](validation/corner-blur-domains.md)
retains common-blur counterexamples, interval-dependency probes and known-truth
controls. Observational error and physical model discrepancy remain distinct,
as discussed by [Brynjarsdóttir and O'Hagan](https://www.tonyohagan.co.uk/academic/pdf/simmach.pdf).

## Pixel aperture means: version 3

[Pixel-integrated observations](pixel-apertures.md) replace exact point samples
with known normalized uniform rectangle averages, while retaining one common
blur pair and the version-2 joint-box/projection rules. The guide gives a runnable
input, the bounded antiderivative calculation and a center-sampling counterexample.
Known pixel integration is distinct from arbitrary coordinate uncertainty,
processed-image interpolation and real-camera qualification.

## Why the bounds cover whole radius intervals

Let `X ~ N(px,sigma_x²)` and `Y ~ N(py,sigma_y²)` be independent. The material is
the positive quadrant minus the circular cutout

```text
C_r = {0 <= x <= r, 0 <= y < h_r(x)}
h_r(x) = r - sqrt(2 r x - x²)
U_r(p) = Phi(px/sigma_x) Phi(py/sigma_y) - P((X,Y) in C_r)
```

For a strip `[a,b]`, `h_r` decreases in X. The rectangle of height `h_r(b)` lies
inside the cutout; height `h_r(a)` covers it from outside. Independent Gaussian
rectangle masses are products of CDF differences. Summing inner/outer masses
therefore brackets the complete continuous cutout probability. Subtraction
reverses the bounds. No sampled quadrature error is assumed to vanish.

For `0 < x <= r`,
`d h_r(x)/dr = 1 - x/sqrt(2 r x - x²) >= 0`; separately `h_r(0)=r`.
The X domain also expands, so cutouts are nested and `U_r(p)` decreases with
radius. A radius box `[a,b]` is enclosed by `[lower_U(b), upper_U(a)]`.
This bounds every intermediate radius, rather than only a sampled grid.

A box is excluded only if one full output enclosure is **strictly disjoint**
from its supplied level interval. Boundary contact is retained. A box is
accepted only if every full output enclosure lies within its level interval.
Other boxes are bisected or retained unknown; all queued boxes remain unknown
when the classification budget ends. Version 1 is a one-dimensional
bounded-error set-inversion application; version 2 applies the same rules to
joint radius/blur boxes. Radius nesting holds for every blur pair, and the
version-2 probability bounds enclose the entire supplied blur domain.
Both use the approach described by
[Jaulin and Walter](https://webperso.ensta.fr/jaulin/paper_automatica93.pdf).
Their general theory does not qualify this physical corner model.

## Numerical enclosure and refinement

`backend/decimal_bounds.py` uses 60-digit directed Decimal arithmetic. Square
roots are padded with representable neighbors because Python's correctly
rounded square root uses HALF_EVEN regardless of the requested rounding mode;
see the [Python 3.12 contract](https://docs.python.org/3.12/library/decimal.html#decimal.Decimal.sqrt).
The normal CDF uses an integrated alternating power series with an explicit
first-omitted-term bound after proving tail decrease, and Machin's arctangent
identity to enclose the normalization constant. The underlying error-function
series is given in [NIST DLMF 7.6](https://dlmf.nist.gov/7.6).

At standardized arguments beyond ±8, monotonicity and `[0,1]` give deliberately
coarse tails. The code does not silently saturate to exact zero or one. Series
exhaustion or failed finite arithmetic cannot become a rejection. Caches and
iteration counts are bounded, and computations use explicit Decimal contexts.

More cells can tighten the spatial cover; a smaller radius stopping width can
tighten subdivision. Neither validates the model or supplied observation
bounds. Fixed spatial-cover error or coarse tails can leave unknown regions
even after fine radius subdivision. No unconditional convergence or physical
coverage probability is claimed.

See the [validation record](validation/corner-feasibility.md) for independent
oracles, exact controls, negative/unknown cases and source-bound checks. The
existing workbench's fitted RMS, sharp-resolution notes and geometry remain
separate from this developer analysis.
