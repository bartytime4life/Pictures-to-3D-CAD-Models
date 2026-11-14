# Scope and roadmap

## Current product boundary

This page concerns the [main-based source described here](project-status.md).
Research PRs targeting other branches are not additional current capabilities.

The workflow is a single-user photo-to-profile workbench for one connected, constant-thickness source part. It provides visible outline review, scale from the complete outside width, two points on a known feature or a reference sheet, a separate thickness input, an optional independent source-height comparison, explicit design scales, relative-detail choices, approximate color/material preview, editable printer-volume planning, and optional straight-cut parts. Browser-saved recipes use version 2 for polygon profiles and version 3 for fitted/reference-sheet profiles, preserving design choices and optional reference/check inputs. Versions 1, 2 and 3 remain importable. Server handoff recipes do not carry the browser-only measurement notes; see [exports](exports.md).

Known-feature endpoints can be selected on the working-image preview or entered numerically. Their measured length defines one uniform scale, and the outside-height comparison does not adjust geometry. This endpoint method does not correct camera distortion. The separate [reference-sheet pipeline](reference-sheet.md) estimates perspective, one radial lens term and thickness parallax under stated assumptions; neither method quantifies general physical accuracy or certifies fabrication suitability. See the [capture guide](capture-guide.md) for the coordinate frame, assumptions, and held-out checks.

The deterministic **Next step** guide, workflow navigation and footer distinguish
missing measurements, invalid settings, processing, stale geometry and current
CAD without an AI service. Preview updates, direct correction paths and grouped
export choices keep the existing engineering tools available. The [guided audit](validation/guided-workbench.md)
records their tested behavior; the [documentation index](README.md) maps the guides.

An optional local Ollama assistant provides text guidance and reviewable trace/design/print-setting proposals. Its integration is separate from geometric conversion; model downloads and live quality comparisons are still subject to the [recorded verification status](ollama.md).

The current implementation and [validation results](validation.md) are the source of truth for what works. Items below are future work, not hidden capabilities or delivery promises.

PR #88 introduced a [conditional finite-material Python inverse](finite-shape-inverse.md),
with [matched and adverse numerical evidence](validation/finite-free-centre.md).
It has no automatic trace/build integration. A subsequent
[measured-ring developer bridge](validation/finite-photo-intensity-v2.md) supplies
explicit observation-region selection and immutable paired samples. Supported
covariance and thickness frames, independently evaluated source adequacy, latency
and preservation of final CAD geometry remain prerequisites for user adoption.
The [affine batch upgrade](validation/finite-affine-batch.md) supplies bounded
work accounting and fixed-workload performance evidence: 3.84× faster complete
fits with all earlier target passes retained. Its 2.75–3.91-second medians do
not qualify interactive adoption. The moment initializer's background-sensitive
proposals are experimental.

The [local residual-information replay](validation/finite-residual-information.md)
is complete with a failed normal-angle control. That diagnostic retains fixed-normal
covariance sensitivities and ten bounded training-only steps; normal-aware steps
remain withheld there. The [finite-chord normal derivative](finite-residual-information.md#finite-chord-shape-derivative-a-derived-proposal)
now has an analytic derivation for valid affine and projective maps. An [experimental implementation and independent study](validation/finite-normal-derivative.md)
now retain one work-limited query and a compressed-map error-estimation
limitation. This checkout retains those V1 numerical limits. Preserve both
original failed studies when reviewing subsequent corrections.
Later [analytic-normal research](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/blob/0f1adbd391f7fa015f458cca60dcfe2a0e2dad9e/docs/validation/finite-analytic-normal-information.md)
has its own recorded branch and does not qualify the current-main operator.

The [known acquisition-operator study](finite-acquisition-operator.md) preserves
complete stages from source `0714aad` for 16 new scenes and 32 output-scale
records. Under the declared one-level criterion, nominal Gaussian PNG
comparisons are 5 compatible/27 incompatible. Moment matching leaves 15
compatible/16 incompatible/1 inconclusive PNG comparisons and 23 compatible/9
incompatible unquantized comparisons. Its [full record](validation/finite-acquisition-operator.md)
retains the pre-capture failure and 320 raw scalar-serialization failures;
separate saved-only conversion changes no category. Those findings motivated
the source-cell forward model below. The recorded-source archive
does not retest current main's newer shadow-lighting model. Older processed-field
archives still lack their complete original acquisition chain, so these new
scenes cannot explain their historical errors.

The experimental [acquisition-aware mean](finite-acquisition-mean.md) now has
[complete saved-capture qualification](validation/finite-acquisition-mean.md):
32 output records and 128 passing comparisons, including analytic-D cell
coverage and explicit discrete stages, with no changed encoding codes.
Its [archive](../studies/fixtures/finite-acquisition-mean-v1/README.md) retains
first failed controls, audit arithmetic discrepancies and the later workspace
repair. The subsequent [area and fixed-linear operators](finite-cell-sensitivity.md)
now have [independent derivative checks](validation/finite-cell-sensitivity.md).
Main still has no acquisition-aware five-parameter inverse. A separately frozen
[local prototype](finite-acquisition-recovery.md) now has two complete 24-row
protocols, each retaining 12 adverse rows: the original at `7ec6803` passes 4/12
matched cases; the continuation at `e6e2c2` passes 9/12 (four smooth, four
float32-staged and one PNG). Both exit **1**. Its **459 focused tests** are
separate from recovery qualification. Next: resolve the retained PNG misses and
identifiability limits before proposing integration, while preserving separate
smooth and literal rounded objectives. The [record](validation/finite-acquisition-recovery.md)
also retains the original study's first audit and its 14 unverifiable pre-cast
area-delta checks.
Neither prototype has a GUI/HTTP mode. Supplied-stage agreement does not qualify
an unknown camera, current-main shadow fitting or automatic correction.

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
Full recovery remains 11/12; acquisition-aware fitter integration is absent from main.

The subsequent [observed-defect correction](finite-acquisition-defect-corrector.md)
uses one fixed equality-restoration step and one nearest physical tuple. Its
first actual pair reduces training cost **0.302031169350812 to 0.0** on the
135 supplied synthetic PNG training samples. Only source 62 changes code
(93 to 92), with no collateral code change. [Complete paired result](validation/finite-acquisition-defect-corrector.md).
This is a local training result; full recovery has not been rerun, and the
original failed 11/12 protocol and main runtime remain unchanged.

A separate [restoration controller draft](finite-acquisition-restoration.md)
is now authored in local research. It has not been committed, frozen or
executed. Its proposed live accounting differs from the completed standalone
probe; the earlier result does not validate that policy. There is no new
software-test result, recovery score or available main command.

These separate local studies add no main runtime or workbench integration.

The [engineering model and verification plan](engineering-model.md) defines the 2.5D scope, camera-model assumptions, dimension equations and evidence needed through prototype qualification. The independent source-height check optionally compares a user-bounded measurement with a user-defined allowance; it reports within, outside or inconclusive without assigning a physical accuracy or confidence level.

Reference entry also includes an [endpoint-placement sensitivity explorer](reference-sensitivity.md). It illustrates a user-selected pixel-shift scenario without applying scale or claiming an accuracy range.

## Useful next steps

| Direction | User benefit | Evidence needed before release |
| --- | --- | --- |
| Additional measured feature checks | Compare reserved hole spacings or other dimensions beyond the current outside-height check | Unambiguous feature selection, preserved model revision, and clear separation of checks from values used to set scale |
| Manual profile correction | Repair a small tracing error without retaking the photo | Undo/redo, topology validation, accessible editing, consistent export revisions |
| Lens and perspective correction | Improve suitable off-axis captures | **Implemented for reference-sheet photos** (one radial coefficient, plane homography, top-face parallax; [method](reference-sheet.md)). Still needed: measured accuracy on reference parts and real phones, tangential/k₂ lens terms, contact/sharp-shadow handling beyond the supported soft-shadow model, a check of real cameras' tone mapping against the sRGB decoding, and a camera height for near-frontal photos of parts without round holes (qualifying off-center holes assumed round can now provide it when the search accepts an identifiable minimum; narrow walls can share a tone estimate when sufficient bands and the fit's acceptance checks support it) |
| Parametric CAD recipes | Make more of the construction editable downstream | A defined feature schema, stable regeneration, and version migration |
| Analytic line and circle fitting | Replace suitable traced approximations with editable geometric features | **Implemented for reference-sheet photos**, with residual gates, an [initial-fit support check](validation/fit-support.md), a reported and optional snap list, and polyline fallback. The [canonical-join port](curved-joins.md) keeps accepted final arcs on their fitted circles and gives targeted recovery/refusal for unavailable joins. Further work: physical forward-model adequacy after Gaussian/design reconstruction, directional partial-arc and finite-shape models, per-item snap review, fitted geometry for split output and for photos without a sheet, validated per-dimension uncertainty |
| Measured-photo benchmark | Quantify error on real parts | **The runner is implemented** (`make photo-benchmark`; [guide](photo-benchmark.md)): bounded global size correspondence, complete dimension-coverage totals, conditional per-dimension error, observed spread, and a two-term scale/edge diagnostic. Still needed: independently evaluated, calipered parts photographed with real phones under predeclared crossed conditions and reserved checks |
| Directional blur and independent simulation | Expose model mismatch before applying unsupported corrections | **Implemented:** a separate synthetic radial inverse, production inverse-domain safeguards and test-only higher-order lens stress inputs; [record](validation/radial-inverse.md). The [30-case blur qualification](validation/directional-spread-qualification.md) found missed cases for its research diagnostic; the tracer fits a uniform directional blur with orientation-support and adequacy rules ([method](reference-sheet.md)). Supported nonparallel fillets use its covariance. Unresolved fits normally retain the traced boundary; invalid corrected rings may use a frozen initial fit as a line-only polygon after validity and whole-boundary tolerance checks, with an undetermined-radius notice and refusal otherwise ([recovery limits](anisotropic-corners.md#when-the-corrected-source-ring-is-invalid)). Needed: finite-shape adequacy, general free-arc and slot-cap models beyond their existing approximations, covariance uncertainty, spatially varying blur, sharpening, contact shadows and sharp-edged shadows under a wide blur (a soft shadow is fitted round the part and taken out of the measured blur; [method](reference-sheet.md)), the fitted shadow's remaining outward bias beside the edge it shades (the second pass's start-dependence, measured on exact images, waits on it), thick parts traced under a wide or directional blur (on `main` the 4 mm 1 × 3 px plate fails to trace on six of seven seeds) and reserved real captures |
| Blur frames after thickness correction | Keep known coordinate changes consistent with blur units | **Implemented:** uniform point scales transport scalar spread, covariance, free-curve correction, cap placement and line windows ([frame and support rules](blur-frames.md)). Mixed free curves, caps and scalar corners retain warned geometry approximations; mixed supplied-covariance nonparallel corners remain withheld. Needed: adequate mixed-frame and finite-shape models, independently checked critical radii and real-capture evidence |
| Finite-material intensity fitting | Use the whole material region when an isolated arc model is inadequate | **Developer APIs in main:** supplied-optics inverse and immutable measured-ring preparation ([contract](finite-shape-inverse.md)); the [paired replay](validation/finite-photo-intensity-v2.md) retains three all-target passes among twelve records. The [recorded-source acquisition audit](finite-acquisition-operator.md) finds second-moment Gaussian closure insufficient; the subsequent [source-cell mean](finite-acquisition-mean.md) passes its [saved-stage comparisons](validation/finite-acquisition-mean.md), and [unrounded derivatives](finite-cell-sensitivity.md) have separate checks. The [separate local five-parameter prototype](finite-acquisition-recovery.md) still fails its complete protocol and is not integrated. Needed before adoption: adequate optics/illumination and thickness frames, independent reserved dimensions, broader latency qualification after the [fixed affine performance pass](validation/finite-affine-batch.md), preserved failures/refusals, and one accepted boundary through preview and exports |
| Measured local-model selection | Choose the smallest assistant that gives useful advice quickly | Installed artifact/license verification, repeatable latency results, and human review of fixed project-specific cases |
| Opt-in vision guidance | Give capture advice based on the actual photograph | Explicit image-sharing control, a verified local vision model, resource bounds, and evaluation against visible evidence |
| Assembly-aware splitting | Add useful joints or locating features between pieces | Measured clearance/kerf, topology checks, validated joinery, and explicit assembly assumptions |
| Native slicer qualification | Verify the existing 3MF and Bambu Studio/PrusaSlicer handoffs in installed applications | Installed-version records, imported dimensions and hole topology, actual layer previews, qualified printer/material profiles, and separate physical-print evidence |
| Multi-user hosting | Share the tool safely across users | Authentication, authorization, isolated jobs, quotas, retention, deletion, monitoring |
| Multiview reconstruction | Reconstruct more general surfaces | Capture guidance, hardware budget, scale controls, mesh validation, and a separate CAD-fitting strategy |

## Release discipline

Before expanding the scope, keep the current workflow dependable: verify supported imports, hole topology, dimensional conversion, exports, outdated-result handling, failure recovery, keyboard access, and responsive behavior. Update the user guide when behavior changes, and record failures as well as passes.

Initial circle/piece fits now have a source-support check. Benchmark correspondence and complete coverage accounting are now implemented.
Supported nonparallel corners now use the empirical directional covariance;
known uniform thickness maps also transport blur for the existing free-curve
and cap approximations ([blur frames](blur-frames.md)). Prioritize
the separate [five-parameter prototype's remaining recovery failures](validation/finite-acquisition-recovery.md),
with rank/contrast, undefined derivatives, rounding and encoding treated
explicitly before main integration, then repeatable ground-truth capture. Finite-shape interactions
and mixed-frame policies remain. The lens renderer is now separately implemented, but the shared
physical assumptions and observed higher-order mismatch remain. Keep the
directional-spread prototype out of product reporting; the tracer's own
directional fit (reference-sheet §3) needs real shaken captures next.
Native slicer qualification remains a separate handoff task. Manual profile
correction follows when undo, topology checks, and accessible editing are scoped
together. Multiview reconstruction and multi-user hosting require separate
designs and resources. These priorities carry no delivery dates or assigned
owners; proposed guards and algorithms are not current capabilities.

Do not label a release manufacturing-accurate, fully parametric, production-secure, or universally accessible without evidence supporting that specific claim.
