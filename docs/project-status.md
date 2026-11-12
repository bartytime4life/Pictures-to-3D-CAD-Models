# Source scope and verification status

This candidate builds on documentation [PR #81](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/81),
head `60732a71b52b8d48241d6f2aa7780d5a7f790107`, which preserves executable source
from draft [PR #78](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/78)
at `185d682197437581083a8ecd46de6357d7adb846`, based on main `f1679bb`.
It adds [covariance-aware nonparallel corners](anisotropic-corners.md), supported
thickness-frame transport and explicit outline recovery when a radius remains
unresolved. A self-crossing corrected trace can use a line-only initial geometric
approximation only after separate validity and whole-boundary distance checks. The
[source-bound evidence](validation/anisotropic-corners.md) distinguishes the new
numerical controls from historical tests and physical qualification.

| Source lane | What it contains | Evidence boundary |
| --- | --- | --- |
| Current corner candidate based on PR #81 | Full-covariance nonparallel fillets, uniform-scale transport and bounded per-ring outline recovery | [Independent and regression record](validation/anisotropic-corners.md); exact supplied mathematical inputs, no camera qualification |
| Main at `f1679bb` | Merged PR #76 slot-end placement and PR #77 directional blur | Existing rendered-photo and geometry records; no general real-camera qualification |
| Reviewed source `185d682`, draft PR #78 | Main plus numerical rank rejection in the directional covariance fit | [633 local Python tests](validation/directional-blur-rank.md), build and focused rank controls; no new browser run |
| [Draft PR #79](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/79), head `32d29f4b4884e6bdc3caf9d4415e48ec00d57562` | Source-space Gaussian width/covariance research, based on `codex/source-observation-context` at `0c35777` | A separate lineage and its own conditional studies; those developer APIs are absent from this checkout |

At the November 12, 2026 source snapshot (**19:16:12 UTC**) both PRs were open
drafts. PR #78's hosted workbench run was still in progress; see the
[timestamped review record](validation/documentation-main77-state.md).
Neither a draft PR
nor a local test result establishes merge, installation, deployment or physical
acceptance. The larger research suite is not the main branch's test result.

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
records its own unchanged-source checks; the new [corner validation](validation/anisotropic-corners.md)
records this implementation's evidence. No real-phone/caliper benchmark,
native slicer acceptance or physical print qualification is established by
the synthetic geometry and rendered-image checks.
