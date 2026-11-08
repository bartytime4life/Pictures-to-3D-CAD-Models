# Scope and roadmap

## Current product boundary

The first workflow is a single-user photo-to-profile workbench for one connected, constant-thickness part. It provides visible outline review, user-entered width and thickness, an interactive preview, and CAD/mesh/profile exports with a reproducible recipe.

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
| Multi-user hosting | Share the tool safely across users | Authentication, authorization, isolated jobs, quotas, retention, deletion, monitoring |
| Multiview reconstruction | Reconstruct more general surfaces | Capture guidance, hardware budget, scale controls, mesh validation, and a separate CAD-fitting strategy |

## Release discipline

Before expanding the scope, keep the current workflow dependable: verify supported imports, hole topology, dimensional conversion, exports, outdated-result handling, failure recovery, keyboard access, and responsive behavior. Update the user guide when behavior changes, and record failures as well as passes.

Do not label a release manufacturing-accurate, fully parametric, production-secure, or universally accessible without evidence supporting that specific claim.
