# Scope and roadmap

## Current product boundary

The workflow is a single-user photo-to-profile workbench for one connected, constant-thickness source part. It provides visible outline review, scale from either the complete outside width or two points on a known feature, a separate thickness input, an optional independent source-height comparison, explicit design scales, relative-detail choices, approximate color/material preview, editable printer-volume planning, and optional straight-cut parts. CAD/mesh/profile exports preserve geometry; a version 2 recipe also preserves design choices and optional reference/check inputs. Earlier version 1 and version 2 recipes remain importable.

Known-feature endpoints can be selected on the working-image preview or entered numerically. Their measured length defines one uniform scale, and the outside-height comparison does not adjust geometry. These features help review a source photograph; they do not correct perspective or lens distortion, quantify physical accuracy, or certify fabrication suitability. See the [capture guide](capture-guide.md) for the coordinate frame, assumptions, and held-out checks.

An optional local Ollama assistant provides text guidance and reviewable trace/design/print-setting proposals. Its integration is separate from geometric conversion; model downloads and live quality comparisons are still subject to the [recorded verification status](ollama.md#current-cloud-verification-status).

The current implementation and [validation results](validation.md) are the source of truth for what works. Items below are future work, not hidden capabilities or delivery promises.

Reference entry also includes an [endpoint-placement sensitivity explorer](reference-sensitivity.md). It illustrates a user-selected pixel-shift scenario without applying scale or claiming an accuracy range.

## Useful next steps

| Direction | User benefit | Evidence needed before release |
| --- | --- | --- |
| Additional measured feature checks | Compare reserved hole spacings or other dimensions beyond the current outside-height check | Unambiguous feature selection, preserved model revision, and clear separation of checks from values used to set scale |
| Manual profile correction | Repair a small tracing error without retaking the photo | Undo/redo, topology validation, accessible editing, consistent export revisions |
| Lens and perspective correction | Improve suitable off-axis captures | Explicit calibration assumptions and measured accuracy on reference parts |
| Parametric CAD recipes | Make more of the construction editable downstream | A defined feature schema, stable regeneration, and version migration |
| Analytic line and circle fitting | Replace suitable traced approximations with editable geometric features | Explicit residual errors, user review, and preservation of intentional non-circular geometry |
| Measured-photo benchmark | Quantify error on real parts | Ground-truth dimensions, repeatable capture conditions, published uncertainty |
| Measured local-model selection | Choose the smallest assistant that gives useful advice quickly | Installed artifact/license verification, repeatable latency results, and human review of fixed project-specific cases |
| Opt-in vision guidance | Give capture advice based on the actual photograph | Explicit image-sharing control, a verified local vision model, resource bounds, and evaluation against visible evidence |
| Assembly-aware splitting | Add useful joints or locating features between pieces | Measured clearance/kerf, topology checks, validated joinery, and explicit assembly assumptions |
| Native slicer qualification | Verify the existing 3MF and Bambu Studio/PrusaSlicer handoffs in installed applications | Installed-version records, imported dimensions and hole topology, actual layer previews, qualified printer/material profiles, and separate physical-print evidence |
| Multi-user hosting | Share the tool safely across users | Authentication, authorization, isolated jobs, quotas, retention, deletion, monitoring |
| Multiview reconstruction | Reconstruct more general surfaces | Capture guidance, hardware budget, scale controls, mesh validation, and a separate CAD-fitting strategy |

## Release discipline

Before expanding the scope, keep the current workflow dependable: verify supported imports, hole topology, dimensional conversion, exports, outdated-result handling, failure recovery, keyboard access, and responsive behavior. Update the user guide when behavior changes, and record failures as well as passes.

Prioritize repeatable ground-truth capture and native slicer qualification next. Manual profile correction follows when undo, topology checks, and accessible editing are scoped together. Multiview reconstruction and multi-user hosting require separate designs and resources. These priorities carry no delivery dates or assigned owners.

Do not label a release manufacturing-accurate, fully parametric, production-secure, or universally accessible without evidence supporting that specific claim.
