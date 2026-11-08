# Scope and roadmap

## Current product boundary

The workflow is a single-user photo-to-profile workbench for one connected, constant-thickness source part. It provides visible outline review, measured width and thickness, explicit design scales, relative-detail choices, approximate color/material preview, editable printer-volume planning, and optional straight-cut parts. CAD/mesh/profile exports and a version 2 recipe preserve the generated result and design choices; version 1 recipes remain importable.

An optional local Ollama assistant provides text guidance and reviewable trace/design/print-setting proposals. Its integration is separate from geometric conversion; model downloads and live quality comparisons are still subject to the [recorded verification status](ollama.md#current-cloud-verification-status).

The current implementation and [validation results](validation.md) are the source of truth for what works. Items below are future work, not hidden capabilities or delivery promises.

## Useful next steps

| Direction | User benefit | Evidence needed before release |
| --- | --- | --- |
| Two-point calibration | Use a known feature instead of the whole horizontal span | Keyboard-accessible endpoint controls, correct coordinate transforms, short-reference handling |
| Additional measured cross-checks | Detect inconsistent scale or perspective sooner | Clear distinction between a warning and actual camera calibration |
| Manual profile correction | Repair a small tracing error without retaking the photo | Undo/redo, topology validation, accessible editing, consistent export revisions |
| Lens and perspective correction | Improve suitable off-axis captures | Explicit calibration assumptions and measured accuracy on reference parts |
| Parametric CAD recipes | Make more of the construction editable downstream | A defined feature schema, stable regeneration, and version migration |
| Analytic line and circle fitting | Replace suitable traced approximations with editable geometric features | Explicit residual errors, user review, and preservation of intentional non-circular geometry |
| Measured-photo benchmark | Quantify error on real parts | Ground-truth dimensions, repeatable capture conditions, published uncertainty |
| Measured local-model selection | Choose the smallest assistant that gives useful advice quickly | Installed artifact/license verification, repeatable latency results, and human review of fixed project-specific cases |
| Opt-in vision guidance | Give capture advice based on the actual photograph | Explicit image-sharing control, a verified local vision model, resource bounds, and evaluation against visible evidence |
| Assembly-aware splitting | Add useful joints or locating features between pieces | Measured clearance/kerf, topology checks, validated joinery, and explicit assembly assumptions |
| Slicer integration | Inspect supports, toolpaths, and machine-specific output | Qualified printer/material profiles, actual slicer execution, reviewable results, and machine-specific validation |
| Multi-user hosting | Share the tool safely across users | Authentication, authorization, isolated jobs, quotas, retention, deletion, monitoring |
| Multiview reconstruction | Reconstruct more general surfaces | Capture guidance, hardware budget, scale controls, mesh validation, and a separate CAD-fitting strategy |

## Release discipline

Before expanding the scope, keep the current workflow dependable: verify supported imports, hole topology, dimensional conversion, exports, outdated-result handling, failure recovery, keyboard access, and responsive behavior. Update the user guide when behavior changes, and record failures as well as passes.

Do not label a release manufacturing-accurate, fully parametric, production-secure, or universally accessible without evidence supporting that specific claim.
