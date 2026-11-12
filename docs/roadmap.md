# Scope and roadmap

## Current product boundary

The workflow is a single-user photo-to-profile workbench for one connected, constant-thickness source part. It provides visible outline review, scale from the complete outside width, two points on a known feature or a reference sheet, a separate thickness input, an optional independent source-height comparison, explicit design scales, relative-detail choices, approximate color/material preview, editable printer-volume planning, and optional straight-cut parts. Browser-saved recipes use version 2 for polygon profiles and version 3 for fitted/reference-sheet profiles, preserving design choices and optional reference/check inputs. Versions 1, 2 and 3 remain importable. Server handoff recipes do not carry the browser-only measurement notes; see [exports](exports.md).

Known-feature endpoints can be selected on the working-image preview or entered numerically. Their measured length defines one uniform scale, and the outside-height comparison does not adjust geometry. This endpoint method does not correct camera distortion. The separate [reference-sheet pipeline](reference-sheet.md) estimates perspective, one radial lens term and thickness parallax under stated assumptions; neither method quantifies general physical accuracy or certifies fabrication suitability. See the [capture guide](capture-guide.md) for the coordinate frame, assumptions, and held-out checks.

The deterministic **Next step** guide, workflow navigation and footer distinguish
missing measurements, invalid settings, processing, stale geometry and current
CAD without an AI service. Preview updates, direct correction paths and grouped
export choices keep the existing engineering tools available. The [guided audit](validation/guided-workbench.md)
records their tested behavior; the [documentation index](README.md) maps the guides.

An optional local Ollama assistant provides text guidance and reviewable trace/design/print-setting proposals. Its integration is separate from geometric conversion; model downloads and live quality comparisons are still subject to the [recorded verification status](ollama.md).

The current implementation and [validation results](validation.md) are the source of truth for what works. Items below are future work, not hidden capabilities or delivery promises.
The dated [project-status snapshot](project-status.md) identifies the integrated
baseline and open algorithm reviews; this guide can describe changes present in
its branch before they reach `main`.

The [engineering model and verification plan](engineering-model.md) defines the 2.5D scope, camera-model assumptions, dimension equations and evidence needed through prototype qualification. The independent source-height check optionally compares a user-bounded measurement with a user-defined allowance; it reports within, outside or inconclusive without assigning a physical accuracy or confidence level.

Reference entry also includes an [endpoint-placement sensitivity explorer](reference-sensitivity.md). It illustrates a user-selected pixel-shift scenario without applying scale or claiming an accuracy range.

## Useful next steps

| Direction | User benefit | Evidence needed before release |
| --- | --- | --- |
| Additional measured feature checks | Compare reserved hole spacings or other dimensions beyond the current outside-height check | Unambiguous feature selection, preserved model revision, and clear separation of checks from values used to set scale |
| Manual profile correction | Repair a small tracing error without retaking the photo | Undo/redo, topology validation, accessible editing, consistent export revisions |
| Lens and perspective correction | Improve suitable off-axis captures | **Implemented for reference-sheet photos** (one radial coefficient, plane homography, top-face parallax; [method](reference-sheet.md)). Still needed: measured accuracy on reference parts and real phones, tangential/k₂ lens terms, edge levels for shadows that are not linear near an edge (linear paper slopes are now followed), a check of real cameras' tone mapping against the sRGB decoding, and a camera height for near-frontal photos of parts without round holes (qualifying off-center holes assumed round can now provide it when the search accepts an identifiable minimum; narrow walls can share a tone estimate when sufficient bands and the fit's acceptance checks support it) |
| Parametric CAD recipes | Make more of the construction editable downstream | A defined feature schema, stable regeneration, and version migration |
| Analytic line and circle fitting | Replace suitable traced approximations with editable geometric features | **Implemented for reference-sheet photos**, with residual gates, an [initial-fit support check](validation/fit-support.md), [conditional corner-resolution estimates](validation/sharp-corner-resolution.md), a reported and optional snap list, and polyline fallback. Further work: forward-model adequacy after Gaussian/design reconstruction, per-item snap review, fitted geometry for split output and for photos without a sheet, validated per-dimension uncertainty |
| Measured-photo benchmark | Quantify error on real parts | **The runner is implemented** (`make photo-benchmark`; [guide](photo-benchmark.md)): bounded global size correspondence, complete dimension-coverage totals, conditional per-dimension error, observed spread, and a two-term scale/edge diagnostic. Still needed: independently evaluated, calipered parts photographed with real phones under predeclared crossed conditions and reserved checks |
| Directional blur and independent simulation | Expose model mismatch before applying unsupported corrections | **Implemented:** a separate synthetic radial inverse, production inverse-domain safeguards and test-only higher-order lens stress inputs; [record](validation/radial-inverse.md). The [30-case blur qualification](validation/directional-spread-qualification.md) found missed directional cases and unknown outcomes, so no production warning or anisotropic correction is justified. Needed: balanced valid orientation support, forward-model adequacy checks, independently specified new evaluations and reserved real captures |
| Measured local-model selection | Choose the smallest assistant that gives useful advice quickly | Installed artifact/license verification, repeatable latency results, and human review of fixed project-specific cases |
| Opt-in vision guidance | Give capture advice based on the actual photograph | Explicit image-sharing control, a verified local vision model, resource bounds, and evaluation against visible evidence |
| Assembly-aware splitting | Add useful joints or locating features between pieces | Measured clearance/kerf, topology checks, validated joinery, and explicit assembly assumptions |
| Native slicer qualification | Verify the existing 3MF and Bambu Studio/PrusaSlicer handoffs in installed applications | Installed-version records, imported dimensions and hole topology, actual layer previews, qualified printer/material profiles, and separate physical-print evidence |
| Multi-user hosting | Share the tool safely across users | Authentication, authorization, isolated jobs, quotas, retention, deletion, monitoring |
| Multiview reconstruction | Reconstruct more general surfaces | Capture guidance, hardware budget, scale controls, mesh validation, and a separate CAD-fitting strategy |

## Release discipline

Before expanding the scope, keep the current workflow dependable: verify supported imports, hole topology, dimensional conversion, exports, outdated-result handling, failure recovery, keyboard access, and responsive behavior. Update the user guide when behavior changes, and record failures as well as passes.

Initial circle/piece fits now have a source-support check. Benchmark correspondence and complete coverage accounting are now implemented.
Prioritize final forward-model adequacy, then
independently specified model-mismatch experiments and repeatable ground-truth
capture. The lens renderer is now separately implemented, but the shared
physical assumptions and observed higher-order mismatch remain. Keep the
directional-spread prototype out of product reporting until fresh evidence
supports its decisions.
Native slicer qualification remains a separate handoff task. Manual profile
correction follows when undo, topology checks, and accessible editing are scoped
together. Multiview reconstruction and multi-user hosting require separate
designs and resources. These priorities carry no delivery dates or assigned
owners; proposed guards and algorithms are not current capabilities.

Do not label a release manufacturing-accurate, fully parametric, production-secure, or universally accessible without evidence supporting that specific claim.
