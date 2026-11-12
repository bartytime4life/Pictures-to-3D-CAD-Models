# Source scope and verification status

This research candidate adds a [finite-material intensity inverse](finite-shape-inverse.md)
and a separate [moment experiment](validation/finite-moment-photo.md), building
on documentation [PR #87](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/87)
at `d5d24e5123dcd118416569dd34d947723343d297`. Its developer functions do not
change the automatic workbench tracing path. Conditional supplied-optics
recovery and observed-image moment proposals retain separate evidence.

The underlying workbench follows [PR #86](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/86),
head `dcb14e5c62ed6f4b3de4426e863aa48b007eb819`, stacked on
[PR #84](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/84),
head `123160ef9909b53ab4fc5186e867b520ac5eefb1`. PR #86 adapts the separately
reviewed [circle-consistent join construction](curved-joins.md) to this
main-based lineage while preserving covariance corners, thickness frames and
bounded outline recovery. Its [current evidence record](validation/directional-free-arcs.md)
separates actual final-geometry checks from conditional free-arc forward-model
research. The latter is study-only; it adds no automatic disk inference or HTTP
mode.

The preceding frame candidate builds on [PR #83](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/83),
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
| Finite-material research candidate based on PR #87 | Unknown-centre intensity inverse and separate observed-field moment proposals | [Current numerical record](validation/finite-free-centre.md); conditional model recovery and retained failures, no automatic trace integration |
| Preceding workbench join candidate, PR #86 (`dcb14e5`), based on PR #84 | Canonical fitted-circle joins, per-boundary recovery and separately retained directional model comparison | [Workbench integration and science record](validation/directional-free-arcs.md); selected circle representation and conditional model comparisons, not physical accuracy |
| Preceding frame-transport candidate, PR #84, based on PR #83 | Point-bound scale transport for free curves, caps and line windows; explicit mixed-frame approximation policy | [Independent and regression record](validation/curve-blur-frames.md); stored-geometry equivariance, not physical-model adequacy |
| Preceding corner candidate, PR #83, based on PR #81 | Full-covariance nonparallel fillets, uniform-scale transport and bounded per-ring outline recovery | [Independent and regression record](validation/anisotropic-corners.md); exact supplied mathematical inputs, no camera qualification |
| Main at `cad695f` | PRs #76/#77, merged rank repair #78 with documentation #81, and PR #82's 45-minute CI budget | Existing revision-bound records; no general real-camera qualification |
| Rank-repair evidence source `185d682`, PR #78 | Numerical rank rejection in the directional covariance fit, now also on main | [633 local Python tests](validation/directional-blur-rank.md), build and focused rank controls at that evidence source; no new browser run in that record |
| [PR #79](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/79), merged into `codex/source-observation-context` at `98862f8` | Source-space Gaussian width/covariance research including documentation #80; source based on `0c35777` | A separate lineage and its own conditional studies; those developer APIs are absent from this checkout |

The November 12, 2026 repository readback at **21:41 UTC** showed PRs #78,
#79, #80, #81, #82 and #83 merged into their respective bases. PR #83 landed
on `codex/documentation-main77-state` at `6316df8` after that branch's PR #81
had already closed; its corner implementation is absent from main `cad695f`.
A fresh readback at **22:02 UTC** confirms PR #86 open, draft and unmerged at
`dcb14e5`, with PR #84 as its base. PR #84 remains open, draft and unmerged at
`123160e`; main remains `cad695f`. This join candidate is stacked on that
reviewed frame branch. The frame branch
carries the reviewed corner implementation and frame follow-up onto that main
baseline while preserving the upstream CI change. A merge into
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

Source-context capture, raw-source inverse fitting,
response calibration and set-inversion APIs on other branches must not be
assumed to exist here. `backend.finite_shape` and `backend.finite_centre_fit`
now expose the conditional finite-material developer operators documented in the
[new model guide](finite-shape-inverse.md). The older frozen kernel under
`studies/verification/` still serves its original level-set comparison; the new
parameterized path shares its evaluator and adds local analytic curves.
Neither study is an automatically selected photograph correction. This checkout's runnable entry points are listed in
[developer tools](developer-tools.md); use `/docs` on its own running backend
for its HTTP contract.

## Remaining integration work

The centre/radius/chord inverse is conditioned on a supplied normal, homography
and covariance. Its independent study and focused controls assess numerical
behavior under those hypotheses. They do not establish an adequate covariance
for an arbitrary photograph, a global optimum or a physical error bound.
The moment experiment retains background-sensitive results and incompatible
covariance proposals. Trace/export integration remains further work; the
existing 16-case directional study does not qualify the new algorithm.

## Read evidence in its own scope

Use the [validation overview](validation.md) for revision-bound results.
Dated records retain their original source, counts, failures, assumptions and
browser transport. The preceding [documentation review](validation/documentation-main77-state.md)
and [corner validation](validation/anisotropic-corners.md) retain their own checks;
the [frame-transport validation](validation/curve-blur-frames.md) retains that
implementation's evidence. The [join/model record](validation/directional-free-arcs.md)
binds the preceding workbench source; the [finite-material inverse record](validation/finite-free-centre.md)
binds the new research candidate. No real-phone/caliper benchmark,
native slicer acceptance or physical print qualification is established by
the synthetic geometry and rendered-image checks.
