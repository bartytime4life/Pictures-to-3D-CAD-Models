# Signed-stencil observation evidence

Recorded November 12, 2026 on the candidate based on published PR #53 head
`e22ff3d6608896c945bd3bc6ad338ff6a780e889`. The isolated branch is
`codex/corner-signed-stencils`; original checkouts and prior results remain
preserved. [Version-4 method and contract](../signed-stencils.md).

## Mathematical change

Each source aperture response is monotone in radius, but its signed combination
need not be. `backend/corner_signed_stencils.py` therefore sums complete
per-aperture radius-box covers with signed interval arithmetic. The shared joint
engine accepts a whole-box callback, preserving its old default path for
versions 2/3. Eight representative complete version-2/3 result dictionaries
matched the pinned baseline, including accounting fields.

Weights are fixed declared coefficients, never renormalized. Exact integer
coefficient arithmetic supplies DC gain, positive/negative sums and L1, without
ambient Decimal rounding. Duplicate apertures combine exactly; raw input,
statistics and work charges remain intact. A known zero functional resolves
without aperture calls. Signed values are not clamped to `[0,1]`.

The CLI's aggregate work cap uses raw nonzero term count, not observation count.
Source provenance now includes six implementation files. No production sampler,
tracer, fitting threshold, API/UI, CAD geometry, dependency or native-tool path
changes. The fixed signed operator is supplied, not extracted or calibrated.

## Decisive endpoint counterexamples

The actual one-dimensional half-phase Keys weights `[-1,9,9,-1]/16`, applied to
four unit apertures centered at `(1,0.5)` through `(4,0.5)` with blur `(0.5,0.5)`,
give approximately `F(0)=0.806773419318`, `F(1.5)=0.809392774216`, and
`F(6)=0.179273795102`. The interior exceeds both endpoints. The production
`sample_keys` applied to these four independently calculated component means
matches the signed combination within ordinary floating-point tolerance.

At 256 cover cells, the interior response is enclosed by
`[0.80929843591767152612,0.80948733224223875266]`; its lower bound exceeds both
endpoint upper bounds by more than `0.0025`. This is a separate interval
certificate under the model, not an inference from quadrature convergence.

Two further certificates retain an interior below both endpoints: a gain-one
two-term functional `2 U(0.5,0.5)-U(2,2)` with unit blur, and the separable
16-tap half-phase Keys stencil at Dirac points with blur `(0.5,0.5)`. The latter
has approximately `F(0)=0.588339848574`, `F(6)=-0.006858313963` and
`F(12)=3.2532e-8`. Endpoint-only exclusion is invalid for all three examples.

These are limitations of applying monotone-point/aperture rules to a different
signed observation, not newly asserted production-sampler defects. The earlier
models remain conditional on their stated observation functions.

## Frozen 12-case development census

The plan was fixed before this runner executed. Named counterexamples were
already examined and are labeled in the plan. The oracle is the archived
independent erfc/Legendre aperture/angle calculation from the pixel-aperture
study, combined using ordinary scalar signed sums. It does not use production
CDF, antiderivative, height-cover or signed-box code for its reference values.
The shared physical assumptions remain independent Gaussian blur and known
product apertures.

Aperture/angle orders `(48,128)` and `(96,256)` agreed within
`3.6637359812630166e-15`, below the predeclared `1e-12` limit. All 12 generating
radius/blur tuples remained in accepted or unknown boxes, with none excluded.
Seven reports were compatible and five remained unknown. Accepted midpoints
were checked independently; exact rational intrinsic-volume/nonoverlap checks
verified full joint coverage and both radius projections.

| Case | True radius | Status | Radius inner / outer |
| --- | --- | --- | --- |
| Actual four-aperture Keys, prior `[0,6]` | 1.5 | Unknown; budget exhausted | Empty / `[1.125,2.0625]` |
| Same known-radius witness, prior `[1.5,1.5]` | 1.5 | Compatible | `[1.5,1.5]` / `[1.5,1.5]` |
| Two-term negative interior | 4 | Unknown; budget exhausted | Empty / `[3.75,4.3125]` union `[5.34375,6.1875]` |
| Greater-than-one signed response | 0 | Compatible | `[0,0.375]` / `[0,0.5]` |
| Actual 16-tap negative Keys response | 6 | Unknown; budget exhausted | Empty / `[4.5,6.9375]` |
| Four-aperture fixed blur, coarser cover | 1.5 | Compatible | `[0.703125,1.6640625]` / `[0.609375,2.015625]` |
| Same coarser setting, narrow blur domains | 1.5 | Unknown; stopping widths reached | Empty / `[0,2.6015625]` |
| Negative-gain apex | 0 | Compatible | `[0,0.5]` / `[0,0.625]` |
| Zero functional | 1.5 | Compatible; no radius information | `[0,6]` / `[0,6]` |
| Exact duplicate cancellation | 1.5 | Compatible; no radius information | `[0,6]` / `[0,6]` |
| Two-stage Keys, 256 raw terms | 0 | Compatible at supplied singleton radius | `[0,0]` / `[0,0]` |
| Two observations with shared uncertain blur | 1.5 | Unknown; stopping widths reached | Empty / `[0,2.6484375]` |

Unknown outer regions need not all be feasible. Singleton-radius and zero-output
controls verify computation; they do not establish radius identification.
The raw 256-term composition retains L1 `625/256` and gain 1. Exact coalescing
reduces it to 49 aperture evaluations at the singleton radius, while its full
raw work charge remains. A separate regression refuses `max_boxes=17` at the
declared `cells=8` boundary; `max_boxes=16` is allowed.

The retained narrow-band test in the public source uses a different binding:
64 cells, 127 boxes, radius stopping width `0.025` and band
`[0.8093827742160953,0.8094027742160953]`. It returns unknown, outer
`[1.21875,1.7578125]`, 79 boxes, no budget exhaustion. The census's first row
uses 256 cells, 31 boxes and a wider band; these are separate results.

For that observed signed value, interpreting it as the point `(2.5,0.5)` can
exclude the true radius; interpreting it as one unit aperture `[2,3]×[0,1]`
rejects the supplied model. The census retains both wrong-observation-model
outputs alongside the signed result rather than treating a narrow wrong-model
answer as successful recovery.

## Regression and contract evidence

The complete Python suite passed **1,022 tests in 193.75 s**, with no skips.
This adds 65 signed-stencil checks and 28 CLI checks to the 929-test base.
Repository Ruff and whitespace checks pass. All eight frozen implementation/test
hashes stayed unchanged through the complete run.

All **67 Markdown documents** parse; **658 local links**, including **51 heading
fragments**, resolve, and **107 tables** have consistent columns. All four
guide JSON examples ran through the CLI: stdout and exclusive saved files
matched, canonical inputs and byte hashes agreed, and all six implementation
hashes matched the evaluated source.

The [public regressions](../../tests/test_corner_signed_stencils.py) cover
nonmonotonicity, sign reversal, negative/superunit values, exact old-model parity,
DC/error gain, duplicate cancellation, zero operators, strict work/resource
limits, shared blur, exact coverage/projection, numerical unknowns and hostile
Decimal contexts. Ordinary numerical-oracle comparisons allow the declared
quadrature/float tolerance; the interval separation uses a strict Decimal margin.

CLI checks cover all four versions, six-file hashes, exact input bytes and
canonical values, exclusive writes, actual dirty-new-source detection in a
separate fixture repository, signed targets and invalid contracts. The frontend
build/browser suites and library release were not repeated because their
implementation/generated paths are unchanged.

## Local provenance and remaining work

The following ignored local artifacts identify the complete development
outcomes; they are not published downloads or fresh-checkout dependencies.
Plans/results refuse overwrites. The runner records the modified candidate
state, base checkout and six implementation hashes, rather than attributing
uncommitted new code to the base commit.

| Local artifact | SHA-256 |
| --- | --- |
| `signed-stencil-development-plan.json` | `18ac1dfd68bb8d2d42dc563718979dd7ee3b6454ddaa64b2a16beb88eb1d2a6c` |
| `signed-stencil-development.py` | `70521c0ea1db377b9e02b460956b5477c71455b15a76edb37e86fc3a08aa2b96` |
| Archived aperture oracle source | `81b9ec13cca8504845744e6e4d7d28af36ace8e15ff1d53b2616974dc665702a` |
| `signed-stencil-development.json` | `02889a6b848fdcfdf7971aa77e5b67c87c2dd0f28272401854f64d771c699259` |

Source error bounds, coefficient/float arithmetic, DC normalization, sensor
apertures and pre-aperture optics still need independent calibration. Unknown
weights, warped footprints, nonlinear processing, correlated/non-Gaussian optics,
real-camera accuracy and physical fit remain open. This is a developer
observation model, not an automatic production correction or accuracy label.
