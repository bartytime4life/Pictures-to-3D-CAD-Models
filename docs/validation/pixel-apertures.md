# Known pixel-aperture means: development evidence

Recorded November 12, 2026. This candidate starts from documentation head
`b800edbcf0a20ac2d30b82a9a135cfc46aa76a55` (PR #52), with the shared-blur
analysis from PR #51. The isolated branch is `codex/corner-pixel-apertures`.
Original checkouts and prior evidence remain preserved.

## Model and implementation

[Version 3](../pixel-apertures.md) computes normalized means over supplied known
axis-aligned uniform product apertures. It changes the measured quantity from
a point response to a finite-area mean; it does not widen a point observation
with a guessed error allowance. The blur is one common independent Gaussian
pair before aperture averaging.

`backend/corner_pixel_apertures.py` adds bounded averaged marginal CDFs using
`H(t)=t Phi(t)+phi(t)`, known tail/support inequalities and a density intersection.
The existing cutout-cover geometry still encloses complete continuous means.
The version-2 joint engine accepts an observation callback; its classification,
complete-domain accounting and radius-projection rules are unchanged. Two
zero-width aperture axes delegate to the point calculation exactly.

The CLI preserves versions 1/2, adds exact version-3 dispatch and records five
implementation hashes. No production tracer, fitting threshold, image pipeline,
API endpoint, CAD geometry, dependency lock, AI action or frontend path changes.

## Frozen development census

Eleven case definitions were saved before this runner executed. Four named
mismatch/control definitions came from already examined development examples;
they are explicitly labeled in the plan. Neither those cases nor the new
synthetic definitions constitute an untouched physical or population evaluation.

The census ran on the modified candidate working tree based on `b800edb`.
Its recorded Git revision identifies that base checkout, not a claim that the
new implementation existed in the base commit. Five implementation hashes and
the frozen-source manifest bind the actual evaluated code.

The independent oracle averages erfc Gaussian point probabilities over each
aperture axis using Gauss–Legendre rules. It integrates the cutout in angle,
`x=r(1-cos(theta))`, `h=r(1-sin(theta))`, using separate trigonometric geometry.
It does not call the production CDF, antiderivative, square-root-height cover or
interval functions. Aperture/angle orders `(32,64)` and `(64,128)` agreed within
`1.3322676295501878e-15`; the declared agreement limit was `1e-12`.
This is ordinary numerical cross-checking, not a certified quadrature bound or
independent qualification of the shared Gaussian/product-aperture physics.

All ten cases generated under the aperture model retained the generating
`(radius,sigma_x,sigma_y)` tuple in accepted or unknown boxes, with none in
excluded boxes. Six returned conditional compatible regions and four remained
unknown. The point-data control rejected the deliberately different aperture
model and retained its generating radius under the point model.

| Case | True radius, px | Version-3 status | Version-3 radius inner / outer, px |
| --- | --- | --- | --- |
| Sharp unit-square mean, center mismatch | 0 | Compatible | `[0,0.015625]` / `[0,0.03125]` |
| Rounded unit-square mean centered at `(2,2)` | 2.25 | Unknown | Empty / `[2.2421875,2.259765625]` |
| Rounded unit-square mean centered at `(0.5,0.5)` | 2.25 | Unknown | Empty / `[2.224609375,2.271484375]` |
| Exact point-center data passed to an aperture model | 0 | Incompatible | Empty / empty; the input observation model intentionally differs |
| Nonsquare sharp mean | 0 | Compatible | `[0,0.21875]` / `[0,0.28125]` |
| Rounded nonsquare mean | 1.3 | Compatible | `[1.265625,1.3125]` / `[1.125,1.5]` |
| Rounded offset aperture | 2.6 | Compatible | `[2.5,2.6875]` / `[2.359375,2.828125]` |
| Aperture crossing a negative coordinate | 1.3 | Compatible | `[1.21875,1.359375]` / `[1.078125,1.5]` |
| One zero-width axis | 1.3 | Compatible | `[1.265625,1.3125]` / `[1.125,1.5]` |
| Two observations, narrow common-blur domain | 1.3 | Unknown; budget exhausted | Empty / `[0.84375,1.875]` |
| Two observations, wider common-blur domain | 1.3 | Unknown; budget exhausted | Empty / `[0.09375,3]` |

Every accepted box midpoint was checked with the independent aperture oracle.
Exact rational intrinsic volumes, containment and nonoverlapping interiors
verified complete joint-prior coverage, including singleton dimensions. Radius
inner/outer sets exactly match the appropriate joint-box projections.

For each of the first three aperture observations, the fixed-blur point model
excluded the generating radius at the census's stated cells, priors and level
bands. For the sharp case, the pixel mean is about `0.468366663446` while the
center response is about `0.478120335351`. For the rounded `(2,2)` case, those
values are about `0.894977011010` and `0.901302578480`. These counterexamples
demonstrate model mismatch; the point code remains conditional on point data.

## Retained coarse controls and conditioning

The census's frozen name `rounded-square-retained-control` refers to an earlier
coarser control, not a promise that a later point calculation retains truth.
The census uses singleton blur, 128 cells and radius prior `[1,4]`; its point
model excludes 2.25. The earlier point controls were also reproduced separately:

- Version 1, point `(0.5,0.5)`, blur `(0.5,1.5)`, 64 cells, prior `[0,4.5]`,
  radius resolution `0.025`: unknown, outer `[2.25,2.35546875]`, 23 boxes,
  no budget exhaustion. Finite covers retain the true radius at the boundary.
- Version 2, the same point and prior, 32 cells, blur domains
  `[0.495,0.505] × [1.485,1.515]`, blur resolutions `(0.005,0.005)` and 127 boxes:
  unknown, outer `[2.109375,2.49609375]`, budget exhausted.
- Version 3 with that latter conditioning and unit-square aperture `[0,1]²`:
  unknown, outer `[1.7578125,3.3046875]`, budget exhausted. The generating joint
  tuple remains retained; this coarse comparison does not establish a tighter
  version-3 radius result.

All three use the supplied level band
`[0.3525278979734415,0.3525478979734415]` and a true radius of 2.25.
Different priors, blur domains, cells and work limits retain their own bindings.
A radius projection and a particular radius/blur tuple are distinct checks.

## Numerical and contract checks

The complete Python suite passed **929 tests in 170.65 s**, with no skips.
This is 90 additional tests over the 839-test base: 71 aperture
checks and 19 additional CLI checks. Repository Ruff and whitespace checks
passed. All seven frozen implementation/test hashes remained unchanged through
the full run.

All **65 Markdown documents** parse; **636 local links**, including **50 heading
fragments**, resolve, and **102 tables** have consistent columns. Current guides
link the new observation model; historical reports retain their original source,
counts and observations.

The independent tests cover continuous finite-aperture means, nonzero radii,
uncertain blur, normalization, symmetry, singleton axes, scale/axis transforms,
shrinking footprints, Decimal context isolation, tails and complete joint
coverage. A positive-width three-aperture counterexample accepts each supplied
observation at an individual blur witness but rejects their common blur domain;
separate per-observation fits cannot establish compatibility.

CLI checks cover all three input versions, exact aperture decimals and canonical
input retention, five-file hashes, exclusive writes, malformed/resource-limited
inputs and actual dirty-new-source detection in a separate fixture repository.
The example in the guide remains unknown at its declared stopping width; it is
not presented as an accepted sharp-radius proof.

All three exact JSON examples were extracted from the guides and run through
the CLI. Stdout matched the exclusive saved files; canonical inputs, input-byte
hashes and all five source hashes agreed. The version-3 guide returned unknown,
outer `[0,0.0625]`, 11 boxes and no budget exhaustion, as documented.

The historical controls and independent oracles are executable in
[`tests/test_corner_pixel_apertures.py`](../../tests/test_corner_pixel_apertures.py).
The frontend build/browser suites and companion-library release were not
repeated: those implementation and generated-artifact paths are unchanged.
Earlier browser/library results retain their original source binding.

## Local artifact provenance

These files are local verification receipts, not published data or a promise
that a fresh checkout contains the local runner. Plans and outputs refuse
overwrites. All eleven outcomes, unknowns, parameters and source hashes remain
in the results.

| Local artifact | SHA-256 |
| --- | --- |
| `pixel-aperture-development-plan.json` | `063948ae6eeaf6463e0d71833e5ff665eefbfba8e692a0c0e5daadc10a5ac75e` |
| `pixel-aperture-development.py` | `81b9ec13cca8504845744e6e4d7d28af36ace8e15ff1d53b2616974dc665702a` |
| `pixel-aperture-development.json` | `b892dc35bef31ac2b2e32092f8d5b153b149087eca4ef03a7e54298d3658de2d` |

## Remaining engineering work

Real detector footprints, photometric normalization and the pre-aperture PSF
have not been calibrated here. Uniform product apertures do not justify
arbitrary coordinate-error distributions, rotated/warped footprints, general
intra-pixel response or signed Keys interpolation. Real-camera and physical-fit
qualification remain absent. This developer calculation supplies neither a
production correction nor a photo-derived physical uncertainty label.
