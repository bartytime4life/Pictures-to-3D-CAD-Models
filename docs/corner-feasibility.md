# Conditional corner-radius analysis

This developer tool bounds which radii can explain supplied observations under
one explicit mathematical model. It does not change the workbench's tracing,
CAD geometry or UI, and it does not derive physical error bounds from a photo.
Use it to investigate the [radius/model ambiguity](validation/sharp-corner-resolution.md)
before introducing a correction or an accuracy label.

The model fixes a right-angle corner's apex at `(0,0)`, its material in the
positive X/Y quadrant, a circular fillet, exact observation coordinates and
independent axis-aligned Gaussian blur with supplied widths. Radius is the only
unknown. Uncertain pose, blur, coordinates, tone response, noncircular geometry,
nearby boundaries and model discrepancy require separate treatment.

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
bounds, input-byte hash, three implementation-file hashes and Git metadata are
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
when the classification budget ends. This is a one-dimensional bounded-error
set-inversion application inspired by
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
