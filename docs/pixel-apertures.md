# Pixel-integrated corner observations

Version 3 of the [conditional corner CLI](corner-feasibility.md) models a known
uniform rectangular pixel aperture. It averages the blurred material response
over that aperture instead of replacing it with the value at the pixel center.
Radius and one shared Gaussian blur pair remain the joint unknowns.

This is a developer analysis with supplied bounds. It does not read images,
change tracing or CAD, or calibrate a camera. Use versions 1/2 for their stated
point-observation models; their input contracts remain supported.

## Supply a known aperture

Save this synthetic example as a new JSON file:

```json
{
  "format": "pictures-to-cad-corner-feasibility",
  "version": 3,
  "coordinate_unit": "px",
  "pixel_apertures": [[["0", "1"], ["0", "1"]]],
  "blur_sigma_intervals": [["1", "1"], ["1", "1"]],
  "level_intervals": [["0.4683", "0.4685"]],
  "radius_domain": ["0", "2"],
  "radius_resolution": "0.0625",
  "blur_resolution": ["0.01", "0.01"],
  "max_boxes": 64,
  "cells": 16
}
```

```bash
.venv/bin/python scripts/corner_feasibility.py pixel-input.json --output pixel-result.json
```

The example represents the normalized mean over the unit square `[0,1]²`.
Its true synthetic radius is zero. The result is **unknown**, with an empty
inner set and outer radius set `[0,0.0625]`: the numerical stopping width leaves
an unresolved box. Zero is retained. These bounds and stopping widths are
demonstration choices, not a camera error budget.

Every field is required. The version-3 schema replaces `points` with
`pixel_apertures`; supplying both is rejected. All other fields, decimal-string
requirements, input-file limits and numerical caps follow
[version 2](corner-feasibility.md#joint-blur-domains-version-2).

| Field or convention | Meaning |
| --- | --- |
| `pixel_apertures` | 1–16 known rectangles, each `[[x_lower,x_upper],[y_lower,y_upper]]` in the corner's coordinate frame |
| Coordinates | Closed ordered decimal-string intervals; every endpoint has magnitude at most 1,000,000 |
| Nonzero axis width | A uniform probability measure, normalized by its full width |
| Zero axis width | A Dirac point in that coordinate; two zero widths recover the version-2 point calculation exactly |
| `level_intervals` | Bounds on the normalized material-response mean, in `[0,1]`; not total photon flux or encoded image values |
| `blur_sigma_intervals` | One common pre-aperture independent Gaussian blur pair for all observations |
| Work cap | `2 × cells × number_of_apertures × max_boxes <= 65,536` |

The output has `version: 3` and the same joint parameter boxes, radius
projections, status and accounting fields as version 2. Accepted joint boxes
satisfy every known aperture observation throughout the box. Rejected blur
boxes are never projected as rejected radii; numerical or budget limits retain
unknown boxes. The report records the complete input, byte hash, five
implementation hashes and Git/source state. Existing output files are refused.

## Why a pixel center can give a different answer

For a sharp corner at the origin with unit independent Gaussian blur, the point
level at `(0.5,0.5)` is approximately `0.478120335351`. Its average over `[0,1]²`
is approximately `0.468366663446`. A tight interval around the latter need not
contain the point response. Treating that average as a center sample can exclude
the generating radius under the point model.

These are distinct conditional models, rather than a numerical failure of the
point calculation. [Independent checks](validation/pixel-apertures.md) retain
the mismatch cases, matching controls and unresolved outcomes.

[Chao et al. (2015)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4523554/) model
detected pixel intensity as an integral of a continuous image and study the
effect of its numerical evaluation on localization. [Sun and Zhou (2022)](https://scispace.com/papers/a-correction-algorithm-of-the-sampling-effect-and-its-2ti4fcsj)
also distinguish finite-pixel integration and intra-pixel response variation.
These papers motivate the observation model; their application-specific
accuracy results do not qualify this CAD workbench. The enclosure derivation
below is specific to this implementation.

## Bounded integration

Write `Phi` and `phi` for the standard normal CDF and density, and define

```text
H(t) = t Phi(t) + phi(t)       H'(t) = Phi(t)
A(z; [a,b], sigma) = E_P Phi((z-P)/sigma),  P uniform on [a,b]
                  = sigma/(b-a) [H((z-a)/sigma) - H((z-b)/sigma)]
```

The formula applies when `a < b`; at `a = b`, use `Phi((z-a)/sigma)`.
`A(v)-A(u)` is the Gaussian marginal mass in `[u,v]` averaged over the aperture.
The quadrant mean is `(1-A_x(0)) × (1-A_y(0))`. Independence is preserved because
both the Gaussian and the known uniform rectangle are products in the same axes.

The rounded-corner cutout uses the same nested geometry and decreasing-height
rectangle covers as the [point model](corner-feasibility.md#why-the-bounds-cover-whole-radius-intervals).
Replacing marginal CDFs with their aperture averages therefore bounds the
complete continuous pixel integral. No sampled quadrature error is omitted.
Radius nesting still holds after averaging, so an entire radius interval is
bounded by its two endpoint calculations, uniformly over the common blur domain.

All terms use outward Decimal intervals. Monotonicity of `H` reduces its
argument interval to endpoint bounds. The known inequalities
`max(0,t) <= H(t) <= max(0,t)+phi(t)` limit tail cancellation. The averaged CDF
is also intersected with the CDF bounds over the entire aperture support.
X-strip masses additionally intersect a width-times-density enclosure to limit
dependency loss. These intersections combine valid covers; an inconsistent
intersection becomes a numerical unknown, not a rejection.

## Engineering limits

An aperture here is a **known uniform product measure**, not an unknown point
somewhere inside a coordinate box. A rectangle enclosing an uncertain location
does not justify uniform weighting. Rotated or homography-warped sensor pixels
are generally not axis-aligned uniform rectangles in the corner frame.

The model does not cover arbitrary intra-pixel response, demosaicing, clipping,
camera tone mapping, compression or signed interpolation kernels. In particular,
the workbench uses Keys cubic resampling in several paths; its negative weights
cannot be treated as a nonnegative pixel-aperture average. This tool does not
automatically convert those processed samples into valid observations.

The level intervals require independently justified photometric normalization
and error/discrepancy bounds. Input blur describes the Gaussian **before** this
pixel averaging; a fitted spread that already includes sensor integration or
resampling must not be reused as though it were that optical blur. A uniform
axis of width `w` adds variance `w²/12`, but matching that variance does not make
the convolved profile Gaussian.

Pose, aperture calibration, non-Gaussian/correlated/spatially varying optics,
real-camera accuracy and physical fit remain separate engineering work. A
conditional compatible result does not certify those assumptions or a unique
physical radius.
