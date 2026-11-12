# Source scope and verification status

This candidate builds on [PR #83](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/83),
head `48e4bb5b329a900b41c0f2baca3ec7e769a48682`, integrates main at
`cad695f4a298a5530f92515d5a738decd1152721`, and transports the measured
blur into uniformly scaled free-curve and slot-cap coordinates. Mixed scalar
corners retain the legacy geometry approximation with unresolved radius
uncertainty; mixed supplied-covariance corners retain their existing refusal
and outline-recovery policy. See the [blur-frame guide](blur-frames.md) and its
[separate evidence record](validation/curve-blur-frames.md).

The preceding corner candidate builds on documentation [PR #81](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/81),
head `60732a71b52b8d48241d6f2aa7780d5a7f790107`, which preserves executable source
from the then-draft [PR #78](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/78)
at `185d682197437581083a8ecd46de6357d7adb846`, based on main `f1679bb`.
It adds [covariance-aware nonparallel corners](anisotropic-corners.md), supported
thickness-frame transport and explicit outline recovery when a radius remains
unresolved. A self-crossing corrected trace can use a line-only initial geometric
approximation only after separate validity and whole-boundary distance checks. The
[source-bound evidence](validation/anisotropic-corners.md) distinguishes the new
numerical controls from historical tests and physical qualification.

| Source lane | What it contains | Evidence boundary |
| --- | --- | --- |
| Current frame-transport candidate based on PR #83 | Point-bound scale transport for free curves, caps and line windows; explicit mixed-frame approximation policy | [Independent and regression record](validation/curve-blur-frames.md); stored-geometry equivariance, not physical-model adequacy |
| Preceding corner candidate, PR #83, based on PR #81 | Full-covariance nonparallel fillets, uniform-scale transport and bounded per-ring outline recovery | [Independent and regression record](validation/anisotropic-corners.md); exact supplied mathematical inputs, no camera qualification |
| Main at `cad695f` | PRs #76/#77, merged rank repair #78 with documentation #81, and PR #82's 45-minute CI budget | Existing revision-bound records; no general real-camera qualification |
| Rank-repair evidence source `185d682`, PR #78 | Numerical rank rejection in the directional covariance fit, now also on main | [633 local Python tests](validation/directional-blur-rank.md), build and focused rank controls at that evidence source; no new browser run in that record |
| [PR #79](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/79), merged into `codex/source-observation-context` at `98862f8` | Source-space Gaussian width/covariance research including documentation #80; source based on `0c35777` | A separate lineage and its own conditional studies; those developer APIs are absent from this checkout |

The fresh November 12, 2026 repository readback (**20:36 UTC**) shows PRs #78,
#79, #80, #81, #82 and #83 merged into their respective bases. PR #83 landed
on `codex/documentation-main77-state` at `6316df8` after that branch's PR #81
had already closed; its corner implementation is absent from main `cad695f`.
This candidate carries the reviewed corner implementation and frame follow-up
onto that main baseline while preserving the upstream CI change. A merge into
one branch does not establish inclusion in another. The preceding
[timestamped review](validation/documentation-main77-state.md) retains its
original open-draft and hosted-run snapshot.

Local tests, hosted CI, branch inclusion, installation, deployment and physical
acceptance remain separate evidence. The larger research suite is not the main
branch's test result.

## Available here

The single-user workbench traces a planar boundary, uses supplied scale and
thickness, constructs CAD and exports geometry. Sheet tracing adds a homography,
one radial lens term, subpixel edge measurements, optional design-intent fitting
and the entered-thickness correction under the [documented model](reference-sheet.md).
The optional Ollama assistant receives text context and proposes explicit
settings changes; it receives no photograph or CAD geometry.

Directional covariance is estimated from rise widths in the **rectified
measurement image**, after resampling and smoothing. It supplies normal-specific
edge/wall widths and an approximate scalar for other stages. It is not a
separately calibrated sensor PSF. Supported nonparallel corners use its full
covariance; general free curves and slot caps keep their separate approximations.
See the [stage-by-stage limits](reference-sheet.md#3-segmentation-and-sub-pixel-edges).

Source-context capture, raw-source inverse fitting, finite-shape integration,
response calibration and set-inversion APIs on other branches must not be
assumed to exist here. This checkout's runnable entry points are listed in
[developer tools](developer-tools.md); use `/docs` on its own running backend
for its HTTP contract.

## Read evidence in its own scope

Use the [validation overview](validation.md) for revision-bound results.
Dated records retain their original source, counts, failures, assumptions and
browser transport. The preceding [documentation review](validation/documentation-main77-state.md)
and [corner validation](validation/anisotropic-corners.md) retain their own checks;
the [frame-transport validation](validation/curve-blur-frames.md) records the
current implementation's evidence. No real-phone/caliper benchmark,
native slicer acceptance or physical print qualification is established by
the synthetic geometry and rendered-image checks.
