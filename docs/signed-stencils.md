# Signed sampling observations

Version 4 of the [conditional corner CLI](corner-feasibility.md) evaluates known
fixed signed combinations of pixel-aperture responses. It can represent a
declared linear resampling stencil while preserving its negative coefficients,
gain and overshoot. It does not extract a stencil from a photo or calibrate the
workbench's processing chain.

## Run a signed control

Save this explicit synthetic input as a new file:

```json
{
  "format": "pictures-to-cad-corner-feasibility",
  "version": 4,
  "coordinate_unit": "px",
  "sampling_stencils": [[{
    "weight": "-1",
    "pixel_aperture": [["0", "0"], ["0", "0"]]
  }]],
  "blur_sigma_intervals": [["1", "1"], ["1", "1"]],
  "level_intervals": [["-0.26", "-0.24"]],
  "radius_domain": ["0", "4"],
  "radius_resolution": "0.1",
  "blur_resolution": ["0.1", "0.1"],
  "max_boxes": 64,
  "cells": 32
}
```

```bash
.venv/bin/python scripts/corner_feasibility.py signed-input.json --output signed-result.json
```

This observes `-U(0,0)`, a signed functional with gain −1, not raw negative light.
It returns conditional compatible, inner radius `[0,0.5]`, outer `[0,0.625]`,
13 boxes and no budget exhaustion. The prior and level allowance are synthetic
choices. They do not determine a unique radius or justify a camera error budget.

Every field is required. Version 4 replaces version 2's `points` with
`sampling_stencils`. Each observation is a list of terms, each with exactly
`weight` and `pixel_aperture`. All dimensional values, weights, targets and
resolutions are decimal strings. The existing format, unit, file, integer and
decimal limits remain; versions 1–3 and `--demo` remain supported.

| Input or convention | Contract |
| --- | --- |
| Observations | 1–16 stencils, each with 1–256 raw terms |
| Aperture | The known uniform product rectangle or Dirac axes of [version 3](pixel-apertures.md), in the same corner frame and units |
| Weight | Fixed signed decimal; per-stencil sum of absolute weights at most 4 |
| Weight sum | Arbitrary; weights are never implicitly normalized |
| Targets | Ordered closed signed-functional intervals within `[-4,4]`, with one interval per stencil |
| Work cap | `2 × cells × T × max_boxes <= 65,536`, where `T` is the total number of raw nonzero terms across all observations |
| Zero terms | Kept in input provenance, omitted from computation and `T`; all-zero stencils are allowed |

The work cap charges raw nonzero terms even when repeated apertures can be
combined. Exact duplicate cancellation may reduce actual work; it does not
permit a larger declared workload. The public Python helper separately limits
one call to 256 terms and 256 cells; the aggregate cap applies to CLI analysis.

## Interpret the signed result

The joint unknowns and radius projections retain the
[version-2 rules](corner-feasibility.md#joint-blur-domains-version-2): one common
radius and blur pair must satisfy every observation. Unknown work is retained,
and rejected nuisance boxes are never projected as rejected radii.

Version 4 adds one `stencil_summaries` entry per observation:

| Summary field | Meaning |
| --- | --- |
| `weight_sum` | Exact sum of the supplied weights, or DC gain |
| `negative_sum`, `positive_sum` | Exact sums of negative and positive coefficients; the output always lies between these two values |
| `l1` | Exact sum of absolute weights, also a worst-case source-error gain bound |
| `constant_preserving` | Whether `weight_sum` is exactly 1 |
| `terms`, `nonzero_terms` | Raw input counts; duplicate terms retain their original accounting |

The source means each lie in `[0,1]`; their signed combination need not. Targets
outside a stencil's known range can establish incompatibility. The output is
not clamped to `[0,1]`. An arbitrary gain remains explicit, including gain zero
or −1. A zero functional contains no radius information even when compatible.

`level_evaluations` counts whole-observation box attempts in version 4.
`aperture_evaluations` counts uncached, nonzero aperture/scalar-radius calls.
Duplicates are combined exactly and the local aperture cache is bounded.
The full input, its byte hash, six implementation hashes and Git/source state
are recorded. Existing result files are refused.

## Why whole-radius bounds are necessary

For a fixed radius and common blur, write

```text
F(r,sigma) = sum_j w_j U_j(r,sigma)
U_j([a,b],S) is enclosed by I_j = [lower_U_j(b,S), upper_U_j(a,S)]
F([a,b],S) is enclosed by sum_j w_j I_j
```

Each aperture response decreases with radius, but a signed sum can rise and
fall. Negative weights reverse the relevant interval endpoints. Therefore
the combined observation must be enclosed over the whole radius box before
classification; evaluating only the combined endpoint values is insufficient.

The actual half-phase one-dimensional Keys coefficients are
`[-1,9,9,-1]/16`. With four unit apertures centered at `(1,0.5)` through
`(4,0.5)` and blur `(0.5,0.5)`, independent responses are approximately:

| Radius | Signed response |
| --- | --- |
| 0 | 0.806773419318 |
| 1.5 | 0.809392774216 |
| 6 | 0.179273795102 |

The interior value exceeds both endpoint values. Outward component covers also
certify a separation greater than `0.0025`; this conclusion does not rely only
on quadrature agreement. Endpoint-only exclusion could lose the true interior
radius. [Independent checks](validation/signed-stencils.md) retain this case,
negative and greater-than-one responses, disconnected radius sets and unknowns.

[Keys' cubic-convolution paper](https://doi.org/10.1109/TASSP.1981.1163711)
provides the interpolation context. The whole-box enclosure, accounting and
conditional inference described here are this implementation's methods.

## Error gain and calibration

For source-mean errors bounded by `|e_j| <= epsilon_j`, the output error obeys

```text
|sum_j w_j e_j| <= sum_j |w_j| epsilon_j <= l1 × max_j epsilon_j
```

No independence assumption is needed for that deterministic inequality. It
does not supply the source-error bounds. At half phase a one-dimensional Keys
stencil has `l1=5/4`; a separable two-dimensional stage has at most `25/16`,
and two stages at most `625/256`. The 256-term contract can represent that
declared two-stage composition, within the analysis work cap.

DC gain also affects photometric normalization. If a source value is
`I_j = b + (m-b) U_j`, then the signed output is
`sum_j w_j I_j = b × weight_sum + (m-b) F`. Ordinary affine normalization
commutes with resampling when the gain is 1. Other gains need the corresponding
baseline term; the tool does not infer background or material levels.

Weights, apertures, pre-aperture Gaussian blur, observation bounds and any
discrepancy remain supplied assumptions. Coefficient rounding, unknown kernels,
warped footprints, demosaicing, clipping, tone mapping and other nonlinear
processing require separate evidence. A declared ideal stencil is not a
calibration of the production float/image pipeline. Tracing, API/UI, CAD and
physical qualification are unchanged by this developer analysis.
