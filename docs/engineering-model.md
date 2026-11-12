# Engineering model and verification

[Documentation index](README.md) · [Guided workbench review](validation/guided-workbench.md)

The useful engineering concept is a **measurement-assisted 2.5D reverse-engineering
workbench**: reconstruct the boundary of a flat, constant-thickness part, verify
reserved dimensions, then qualify the manufactured prototype for its intended use.
The model is a planar profile extruded through a separately measured thickness.
A single photograph does not identify hidden surfaces, blind holes, internal
features, material properties, loads or process settings.

The guided next step distinguishes missing measurements, invalid design settings,
a model needing a rebuild, and a current model ready for export review. **Solid
ready** means the digital model matches the current settings. The independent
height decision and printer-fit result remain separate checks; neither the guide
nor a successful build establishes physical acceptance. See [print planning](print-planning.md)
and [export checks](exports.md) before moving to manufacturing.

## Define the requirement before tracing

Record the part's function, mating features, required dimensions and allowable
errors before inspecting results. Reserve dimensions that will not set scale:
outside height is supported in the UI; hole diameter, hole spacing and mating
clearance still need independent checks in CAD or on the prototype. Do not tune
an allowance merely to make a result agree. A load-bearing part also needs load
cases, boundary conditions, material/process data and an independent structural
analysis; choosing a preview material supplies none of those inputs.

## Geometry, units and design changes

For working-image outside spans `Bx, By` in pixels, reference endpoint span `s`
in pixels and known feature length `L` in mm, the uniform model is

```
k = L / s                 mm per working-image pixel
W = k Bx                  source width, mm
H = k By                  source height, mm
d = H - M                 discrepancy from independent measured height M, mm
```

Thickness `t` is measured separately. For a planar profile with net area `A` in
working-coordinate units squared, `V = A k² t` in mm³. Fitted circles and arcs
use their analytic geometry, while polygon outlines retain tracing and
simplification error. If XY design scale is `a` and thickness scale is `b`, the
ideal extrusion has `W' = aW`, `H' = aH`, `t' = bt` and `V' = a²bV`, before any
geometry-detail change. Scaling dimensions does not establish a strength law.
Check the generated solid and downstream import after approximation or splitting.

Reference-length drafts retain full numeric precision when switching between
millimeters and inches. The computed width normalizes floating-point contact
with the supported 0.1 mm and 2000 mm limits using
`64 * Number.EPSILON * max(abs(width), abs(limit))`. This is an arithmetic guard
(about 2.84e-11 mm at 2000 mm), not a measurement allowance. Values outside that
narrow guard remain outside the supported range. Endpoint sensitivity scenario
widths are not clipped to these build limits; a collapsed reference span still
withholds the scenario as described in [endpoint placement](reference-sensitivity.md).

The independent height check concerns the **source polygon's bounding spans**,
not a resized design, a local fitted radius, an exported mesh or a printed part.
It remains a global aspect-ratio check even for a fitted profile. Agreement can
miss a shifted hole, local contour error, or a wrong reference measurement.

## Why capture assumptions matter

Consider an ideal orthographic image of a flat part tilted by angle `θ` about
its horizontal axis. If a horizontal reference sets scale, vertical dimensions
are multiplied by `cos θ`. The vertical relative bias is `1 - cos θ`: about
0.38% at 5°, 3.41% at 15°, and 13.40% at 30°. A 50 mm height tilted by 15° reads
about 48.30 mm, a 1.70 mm discrepancy. This is an illustrative camera model,
not a prediction for arbitrary phone photographs.

In an ideal pinhole camera, a top face `t` above the reference plane at camera
distance `D` is magnified relative to that plane by `D/(D-t)`. Before correction,
`t = 4 mm` and `D = 300 mm` give about 1.35% scale bias, or 0.68 mm on a 50 mm
feature. The implemented reference-sheet pipeline estimates plane correction,
one radial lens term and top-face parallax; its assumptions and limits are in
[reference-sheet tracing](reference-sheet.md). These equations explain why a
calibrated capture and independent measured features matter even when a digital
solid is exact.

Blur evidence also has a coordinate frame and processing stage. The production
`edge_blur_mm` diagnostic describes a processed, rectified edge; it is not a
raw optical PSF measurement. The research [source-context](source-context.md)
retains prewarp working values, and [conditional source-edge fitting](psf-calibration.md)
estimates a Gaussian width in working-image pixels under supplied target,
response and noise assumptions. Width squared and its covariance use working
pixels squared. At least three distinct unoriented directions with numerical
rank three in the covariance design are needed to identify all three entries;
opposite normals do not add a new direction. Full numerical rank and an SPD candidate do not
validate the Gaussian model or establish physical calibration. See the
[constructed response and non-Gaussian counterexamples](validation/psf-calibration.md).

Wall correction also depends on which visible boundary supplies the tracing
seed and whether the flat-tone model describes the capture. A low residual or
an accepted shared wall tone is not a proof of a physical silhouette. The
[local search and observation limits](wall-localization.md)
and [bounded lighting counterexamples](wall-gradients.md) explain why this
requires reserved measurements rather than a universal pixel-error allowance.

## Bounded source-height decision

In **Independent height check**, optionally enter:

- an **allowed height deviation** `T > 0`, chosen from the source-reconstruction requirement;
- an absolute **measurement error bound** `B ≥ 0`, justified for the complete independent measurement method.

Both are blank by default. The tool does not estimate either value or equate a
caliper display resolution with a method error bound. An instrument's expanded
uncertainty or stated accuracy is not automatically a guaranteed absolute
bound. If the assumption cannot be defended, leave the decision inputs blank.
The existing endpoint-placement explorer remains a separate hypothetical
scenario; its pixel shift is not substituted for `B`.

Conditional on `actual source height ∈ [M-B, M+B]`, the deterministic source
prediction differs from the actual height by an interval

```
E = [H-M-B, H-M+B] = [d-B, d+B].
```

| Outcome | Rule | Meaning |
| --- | --- | --- |
| Within entered allowance | `abs(d) + B < T` | Every discrepancy in the entered interval is strictly inside the allowance for this dimension. |
| Outside entered allowance | `max(0, abs(d)-B) > T` | Every discrepancy in the entered interval exceeds the allowance. |
| Inconclusive | Otherwise, including boundary contact | The input cannot support either of those conclusions. |
| Undecided | A required input is absent or invalid | No assessment is made. |

A numerical guard of `64 × Number.EPSILON × max(1, H, M, T, B)` keeps floating-point
contact with a limit inconclusive. It is measured in mm internally and does not
represent physical uncertainty. Decisions use unrounded inputs; displayed
values are rounded. If an entered interval extends below zero height, the full
interval is retained conservatively rather than narrowing it without evidence.

For `H = 50`, `M = 50.2`, `T = 0.5` and `B = 0.1 mm`, `E = [-0.3, -0.1] mm` is
within the allowance. With `B = 0.4`, `E = [-0.6, 0.2] mm` is inconclusive.
With `M = 50.9`, `B = 0.1`, `E = [-1.0, -0.8] mm` is outside. A boundary-touching
interval `[-0.5, -0.3] mm` remains inconclusive.

The decision is conditional, dimension-specific and recomputed from the current
source width and outline. It does not quantify uncertainty in the entire
photo reconstruction, assign a confidence level, certify conformance to a
metrology standard, or assess final printed dimensions. A wrong height may
reveal a capture, reference, trace or measurement problem; it does not identify
which one. Investigate or remeasure rather than stretching the profile to fit
the check, which would consume its independence.

![Independent height check with an inconclusive bounded discrepancy](images/engineering-height-check.jpg)

Browser example with synthetic dimensions: a ±0.4 mm entered measurement bound
makes a −0.2 mm central discrepancy inconclusive against a ±0.5 mm allowance.

## A practical verification sequence

| Stage | Evidence to retain | What remains to be established |
| --- | --- | --- |
| Capture | Original photo, reference identity, measured length/thickness, capture conditions | Hidden geometry and unmodelled camera effects |
| Source reconstruction | Reviewed outline, reference scale, reserved height and justified decision inputs | Other functional dimensions and local features |
| Digital CAD | Valid solid, dimensions, topology, export/reimport checks tied to the recipe | Physical process behavior |
| Slicer setup | Actual imported units, per-piece placement, layer preview, qualified machine/material settings | Actual dimensions, layer adhesion and fit |
| Prototype inspection | Independent measurements of critical features and mating tests | Repeatability and service performance |
| Functional qualification | Relevant loads, environment, allowable deformation/failure and repeated tests | Any untested use or process change |

The project JSON preserves `measured_height_mm` and optional `height_check`
inputs (`allowance_mm`, `measurement_bound_mm`), not a cached acceptance status.
A unit change converts all three physical values. New photos and older recipes
without these inputs clear them. Invalid imports are rejected before the current
project is replaced. Geometry exports and print-fit status do not acquire an
approval from this check. Save a separate inspection record for physical tests.

## Basis and evidence limits

[JCGM 106:2012, sections 8.2–8.3](https://www.bipm.org/documents/20126/2071204/JCGM_106_2012_E.pdf)
distinguishes tolerance limits, decision rules and guard bands, and explains
why uncertainty matters near a limit. It is background for making assumptions
and the decision rule explicit. The implementation here is a direct bounded-
interval derivation; it does not implement that document's probability models
or claim a consumer/producer risk level. Reviewed November 11, 2026.

Repository tests establish arithmetic, state handling, recipe preservation and
accessible browser behavior on synthetic inputs. They do not establish a
physical error bound. The [measured-photo benchmark](photo-benchmark.md) still
needs real calipered parts and recorded capture conditions. Prioritize that
experiment, held-out functional dimensions and prototype inspection before
expanding reconstruction scope or making an accuracy claim.

A mathematically valid solid can still contain the wrong fitted curve. The
[tapered-cap repair](validation/tapered-caps.md) fixes an exact noiseless case
where treating slightly tapered sides as parallel changed the boundary while
Profile validation and native solid import still passed. Tangency, source
agreement, analytic area and exported arc identity are distinct checks. This
repair does not establish the adequacy of a Gaussian camera model.

Final free-arc assembly now intersects the current circle with its neighboring
lines, preserves source traversal and requires a separated minimum under an
explicit endpoint-displacement rule. Missing or unresolved joins retain the
affected traced outline with a notice; unrelated accepted rings remain analytic.
The initial fit-support proxy is separate from this final construction. A
consistent emitted circle still does not identify the physical edge; see
[the construction and its limits](validation/canonical-arcs.md).
Free-circle fit residuals precede correction and do not measure the final curve's
physical error. Inspect the actual CAD curve and reserved dimensions, including
when snapping is off; successful topology validation is insufficient.

The [scientific model review](validation/scientific-model-review.md) records
the original whole-circle extrapolation and camera-model limits.
The [radial-domain repair](validation/radial-inverse.md) removes the renderer's
production-inverse dependency and supplies higher-order mismatch cases;
physical camera assumptions remain. The [directional-spread qualification](validation/directional-spread-qualification.md)
documents missed directional cases and unknown outcomes, with no production
warning or correction. Benchmark statistics remain conditional on comparisons.
Residuals describe the selected
model's agreement with sampled points; they do not alone establish source
coverage, identifiable radius, physical uncertainty or complete benchmark
coverage. The [initial-fit support repair](validation/fit-support.md) addresses
the reproduced extrapolation before Gaussian/design reconstruction; it does not
establish final model adequacy. The optional bounded-height decision above retains its separate,
user-supplied assumptions.

A sharp-corner note reports an estimated radius resolution under the assumed
blur model. It is separate from the user-bounded height decision above. The
[corner-resolution record](validation/sharp-corner-resolution.md) reproduces a
known rounded corner whose model estimate is smaller than its actual radius.
Neither that estimate nor a local radius standard deviation is a physical upper
radius bound. Reserve an independent measurement for fit-critical fillets.

The separate [conditional corner analysis](corner-feasibility.md) encloses
data-compatible radii for one fixed Gaussian right-corner model and explicitly
supplied linear-light level intervals. It can retain unknown regions or reject
an incompatible supplied model. It does not infer those observation bounds,
replace the independent height decision, or qualify a physical fillet.

Its [version-2 extension](corner-feasibility.md#joint-blur-domains-version-2)
can include supplied blur intervals as a joint nuisance domain. A radius needs
one common blur pair for all observations; separate per-point fits cannot prove
that. This still does not justify the blur bounds, accommodate spatially varying
or correlated PSFs, or turn residual spread into a physical error bound.

[Version 3](pixel-apertures.md) models known uniform rectangular pixel means
instead of point samples. Finite detector integration can change the measured
level enough to exclude a known radius under a center-sample model. This
extension bounds the explicit mean calculation; it does not calibrate real
pixels, justify signed/interpolated samples, or infer pre-aperture optical blur
from the workbench's processed edge spread.

[Version 4](signed-stencils.md) can include explicitly known signed sampling
stencils. It accounts for negative coefficients, DC/error gain and whole-radius
nonmonotonicity without clamping a response to `[0,1]`. This still does not infer
the production kernel, source-error bounds or photometric baseline calibration.

The [material-gradient study](material-gradients.md) exercises actual local-profile
functions against independent bounded light fields. Its production sampling-grid
repair removes an orientation-dependent numerical artifact in single-crossing
fixtures. Kept crossings can still shift under material-side illumination slopes,
and wall tone/width can be confounded with edge position. Global affine intensity
normalization does not remove those spatial effects. The [record](validation/material-gradients.md)
keeps that model mismatch separate from sampling symmetry and physical accuracy.

The [crossing rule](edge-crossings.md) further distinguishes a uniquely nearest
verified level crossing from an unresolved contact or tie. Its exact ranking
concerns represented residual samples; it does not establish that the closest
visible feature is the intended physical edge or supply a camera-noise bound.

The [bounded wall/lighting model](wall-gradients.md) makes that distinction
constructive: different silhouette labels can yield an identical local source
field even with known wall width. Joint brightness fitting can expose alternatives
but cannot manufacture missing information. Independent wall/feature evidence
and a physically consistent capture remain necessary; no new accuracy decision
or automatic correction follows from the developer experiment.

## Interpret developer fit diagnostics

The [fixed-observation](profile-observations.md), [known-warp](warp-observations.md)
and [raw-source fitting](raw-source-fit.md) tools make supplied digital and
optical models explicit. They run separately from the upload/build path.
Raw-source fitting compares both model and available prewarp samples in the same
retained source projection; a small cost can hide mismatch in omitted modes.
Its raw/complement residuals are divided by supplied input standard deviations,
so their units differ from intensity residuals. Those deviations must be justified
before giving the diagnostics a physical statistical interpretation.

A rank-two brightness design only distinguishes its two coefficients at a fixed
candidate offset. It does not prove that the offset, wall label or camera model
is identifiable. Review flat/tied/endpoint/work flags, competing candidates and
omitted-source residuals together. The finite search provides no global certificate
or confidence interval. Physical/statistical interpretation of these diagnostics
still needs independently justified camera response, optics and noise, followed
by reserved measured captures. Decoding saved values as sRGB supplies no camera
calibration.

The [exact common-response tool](response-calibration.md) makes supplied response
constraints testable while retaining one shared function. Its query envelopes
are marginal possibilities, so choosing separate per-pixel response values does
not establish a common camera model. The [edge/calibration controls](validation/response-calibration.md)
show that endpoint normalization alone can leave many edge positions compatible,
and a wrong tight calibration can reject the true position. Input uncertainty,
channel/stage dependence and any transformed noise model still need justification.
The separate [rectangle extension](response-rectangles.md) now preserves declared
input intervals. Its two quantifiers distinguish choosing one point per box from
requiring one response for every input. Outward Gaussian covers address numerical
evaluation error under a supplied optical formula; they do not justify that
formula or its physical error budget. The separate [continuous Gaussian-domain solver](gaussian-response-domains.md)
now maintains one shared offset and blur width across all observations under a
supplied straight-edge model. Accepted boxes prove every parameter pair has a
common response; excluded boxes have no feasible pair. Unknown boxes remain in
the outer set, including a retained exact feasible line with no accepted box in
the development study. Marginal offset/sigma projections lose correlation and
cannot certify a pair. These conditional set results do not identify camera
optics, justify the supplied calibration/error bounds or replace reserved
physical measurements. See [complete controls](validation/gaussian-response-domains.md).
