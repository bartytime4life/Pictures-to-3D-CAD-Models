# Engineering model and verification

[Documentation index](README.md) · [Guided workbench review](validation/guided-workbench.md)

Use the [source-scope guide](project-status.md) to distinguish this main-based
workbench from separately reviewed research branches.

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

The [scientific model review](validation/scientific-model-review.md) records
the original whole-circle extrapolation and camera-model limits.
The [radial-domain repair](validation/radial-inverse.md) removes the renderer's
production-inverse dependency and supplies higher-order mismatch cases;
physical camera assumptions remain. The [directional-spread qualification](validation/directional-spread-qualification.md)
documents missed directional cases and unknown outcomes for its research
diagnostic. The tracer's own covariance fit adds orientation-support and
per-direction adequacy rules and traces a uniform directional blur by direction
([reference-sheet tracing](reference-sheet.md), §3). Supported edges can also
use their directly measured directional widths when a full
covariance is unavailable. A two-direction shadow-blurring covariance is not an
identified covariance for geometry correction. Supported nonparallel
fillets with an accepted empirical rectified-image covariance use it in their
[Gaussian corner model](anisotropic-corners.md); unresolved covariance fits or
mixed supplied-covariance supports normally retain the affected traced boundary.
If the corrected source ring is invalid, a frozen, already accepted geometric fit
can provide a line-only polygon only after valid-ring, point-cap and
bidirectional whole-boundary tolerance checks. Otherwise the profile is refused.
This [bounded recovery](anisotropic-corners.md#when-the-corrected-source-ring-is-invalid)
uses no generic topology-repair operator or component deletion. It does not
determine the invalid source's intended topology, a corner radius or physical
accuracy. Final profile validation remains. The 5% common blur-scale sensitivity
remains a heuristic, not inferred covariance uncertainty or physical coverage.
Evidence remains synthetic, and
benchmark statistics remain conditional on comparisons.

General free arcs/circles still use a scalar correction, and slot-end placement
retains its directional first-order approximation. These calculations now
[transport a known uniform thickness scale](blur-frames.md) into the blur width
and covariance in the geometry's frame. Mixed free curves, caps and scalar-only
corner fits retain the earlier geometry approximation with a visible warning,
without an averaged covariance or calibrated uncertainty. A mixed scalar
corner's radius remains undetermined, with no sharp-bound/deletion claim;
supplied-covariance mixed corners retain the separate withholding policy above.
Frame consistency does not establish finite-shape
model adequacy. Radius resolution remains
conditional on the chosen Gaussian geometry, fixed edges and heuristic error
allowances. No source-space PSF calibration API is added to this main-based
branch; the separate research draft keeps its own scope.

The [canonical-join port](curved-joins.md) addresses a different error: an arc's
serialized endpoints and interior point must describe its accepted fitted
circle. That consistency does not validate the circle's physical radius or the
blur model that produced it. Unavailable joins retain an affected outline when
valid, with a notice and no rejected-radius claim; otherwise the profile is
refused. Reserve [independent CAD and part checks](exports.md#verify-critical-arc-geometry)
for dimensions that matter. No exact finite Gaussian disk fit is adopted by
this assembly repair.

The separate [finite-material intensity inverse](finite-shape-inverse.md) now
fits a circular segment's centre, radius and chord under supplied optics. Its
conditional numerical results do not replace this automatic tracing path or
the independent dimension checks above. The [original captured-field diagnostic](validation/finite-free-centre.md)
retains initialization and model failures. The later
[measured-ring replay](validation/finite-photo-intensity-v2.md) removes the known
whole-sheet initialization failure and completes all ten available fits, while
only three of twelve declared records meet every target. Its remaining
intensity mismatches still require a supported observation model. The
[moment proposal study](validation/finite-moment-photo.md) retains background
sensitivity. These studies do not establish a physical uncertainty bound or a usable
covariance for an arbitrary photograph.

The [affine evaluation comparison](validation/finite-affine-batch.md) reduces
the computational cost of that same supplied-optics model. Its three fixed
complete-fit medians are 2.75–3.91 seconds, and all archived target passes and
completion flags are preserved. Numerical parity and faster evaluation leave
the observation-model and independent dimensional checks above necessary.

The [completed acquisition-operator study](validation/finite-acquisition-operator.md)
tests that model at supplied true geometry and brightness, before any fitting.
Its 16 new synthetic source scenes give 32 scale records and 128 paired
stage/covariance comparisons. Even matching formal Gaussian second moments
leaves 9/32 unquantized comparisons incompatible with the one-level criterion;
the decoded-PNG lane has 16/32 incompatible and one inconclusive. These are
intensity-model outcomes, not centre/radius recovery or physical accuracy.
The complete 123-artifact package includes an 87-file source snapshot at
`0714aad`, with the original bootstrap failure and separate scalar-normalization
history retained. This evidence does not validate current main: the study uses
flat illumination and its pinned acquisition source, while current main also
fits the paper's soft-shadow light. See the [method and scope](finite-acquisition-operator.md).

The subsequent [independent source-cell mean](finite-acquisition-mean.md) now
reproduces those supplied discrete stages within its frozen engineering checks.
Its [128-comparison record](validation/finite-acquisition-mean.md) is a forward
qualification, not an inverse-recovery result. Analytic pixel-area integration
and explicit sampling replace a Gaussian point approximation; unknown camera
calibration, source response and illumination are not inferred. Quantization
requires separate derivative and recovery treatment before automatic adoption.
Even `srgb8=False` retains float32 storage transitions. The subsequent
[unrounded area sensitivities and fixed linear operator](finite-cell-sensitivity.md)
are declared separately and have their own qualification. They do not
differentiate those rounded stages or recover geometry; small intensity
residuals alone do not establish dimensional accuracy.

A separately frozen [local recovery prototype](finite-acquisition-recovery.md)
uses these operators to fit five geometry parameters and two bounded brightness
levels; its modules are absent from this main-based source. The first protocol
at `7ec6803` passes 4/12 matched cases. The continuation at `e6e2c2` passes 9/12:
four smooth, four float32-staged and one PNG case. Both complete 24-row protocols,
including 12 adverse rows, exit **1**. The continuation's **459 focused test
passes** are separate software evidence, not a full application or camera result.
Reserved pixels entered initialization, so their residuals are conditional checks.
The [retained results and audit limits](validation/finite-acquisition-recovery.md)
do not establish unique geometry, automatic tracing, a GUI/HTTP mode or physical
accuracy.

The later [coupled search](finite-acquisition-coupled.md) reaches **11/12**
matched target passes; the [source-event continuation](finite-acquisition-events.md)
stays at **11/12**. Both complete 24-case protocols still exit 1. Their first
focused suites pass 548 tests/nine subtests and 653 tests/21 subtests, respectively.
The [completed results](validation/finite-acquisition-continuations.md) and
[saved-only audits](finite-acquisition-saved-audit.md) retain the remaining PNG
miss, first failures and 28 historical precision unknowns. Candidate code and
complete local ZIPs remain separate from this main runtime and workbench UI.

The [protected-source-bin design](finite-acquisition-protected.md) retains its
eight failed first controls. The [exact active-face follow-up](finite-acquisition-protected-active.md)
preserves its first test-expectation failure; a separately frozen corrected
selection passes **821 tests and 33 subtests**. Its complete original 24-case
study still fails at **11/12 matched passes**. The later saved-only
[physical-rounding diagnostic](finite-acquisition-physical-rounding.md) verifies
one rational local optimum but finds **zero accepted candidates among 128
adjacent physical corners**, with no arithmetic unknowns. See the
[complete results and source bindings](validation/finite-acquisition-physical-rounding.md).
The separately frozen [inward-margin construction](finite-acquisition-inward-margin.md)
passes 103 selected controls and all five gates for all 128 new adjacent
corners; an independent saved-data audit passes 8,030 checks. The old 0/128
result remains unchanged. The later [paired literal check](finite-acquisition-inward-literal.md)
exactly reproduces the baseline but raises actual training cost from
0.302031169350812 to 0.40923713513984694, so its predetermined candidate is
rejected. Target source cell 62 reaches code 92; collateral cell 33 changes
106 to 105. [Complete negative result](validation/finite-acquisition-inward-literal.md).
Full recovery remains 11/12; fitter integration is still absent.

The subsequent [observed-defect correction](finite-acquisition-defect-corrector.md)
uses one fixed equality-restoration step and one nearest physical tuple. Its
first actual pair reduces training cost **0.302031169350812 to 0.0** on the
135 supplied synthetic PNG training samples. Only source 62 changes code
(93 to 92), with no collateral code change. [Complete paired result](validation/finite-acquisition-defect-corrector.md).
This is a local training result; full recovery has not been rerun, and the
original failed 11/12 protocol and main runtime remain unchanged.

These separate local studies add no main runtime or workbench integration.

A source-derived straight-edge direction may still align the display and
profile when a ring is retained as line geometry. The rigid rotation preserves
distances and radii; axis-aligned width and height depend on that frame. This
coordinate choice is separate from accepted analytic geometry and does not
establish exact snapping or radius accuracy.

Residuals describe the selected
model's agreement with sampled points; they do not alone establish source
coverage, identifiable radius, physical uncertainty or complete benchmark
coverage. The [initial-fit support repair](validation/fit-support.md) addresses
the reproduced extrapolation before Gaussian/design reconstruction; it does not
establish final model adequacy. The optional bounded-height decision above retains its separate,
user-supplied assumptions.
