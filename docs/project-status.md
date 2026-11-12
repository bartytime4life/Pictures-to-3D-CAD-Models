# Source scope and verification status

This documentation describes main at
`ec41b0ce34746c8fffd17fd7beec2b7cba33413c`, tree
`ac139d3622784bf43f20355056ea2cf530ba04fd`, after PRs #90 and #91 merged.
The documentation follow-up preserves all of that revision's executable, test,
study, fixture and generated-library bytes. See the
[complete documentation review](validation/documentation-pr91-state.md).

The merged [PR #91](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/91)
at `65399053b45f3c38a9d6d2084bc2315aac9bd87e` adds an
[immutable measured-ring observation bridge](finite-shape-inverse.md#prepare-a-measured-ring-observation-set)
and a [paired saved-field replay](validation/finite-photo-intensity-v2.md).
It was based on [PR #90](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/90)
at `bfc53880f0e13caa8e8be5c14d3c9e9e78097d6a`. That original integration tree is exactly
documentation [PR #89](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/89)
at `8cd6e93875ffbc02f81587e0d3aac908f9affab1`, with main at `82017b9` as an
additional parent. That history integration changes no inherited file content.
PR #91 then merged into PR #90's branch at `bf592fa7d1f55eb3a3b8c2490446f65f9ba04aed`,
and PR #90 merged into main at `ec41b0c`.

## Repository and CI snapshot — November 12, 2026, 23:45 UTC

| Source lane | State at this readback | Evidence boundary |
| --- | --- | --- |
| Main, `ec41b0c` | Includes PRs #84, #85, #90 and #91 | Combined workbench source; the preceding 899-test and shadow-branch runs are not a new full-suite result for this merge |
| PR #91, `6539905`, based on PR #90 `bfc5388` | Merged into PR #90 at `bf592fa` and included in main | [899 local Python tests, build and lint](validation/finite-photo-intensity-v2.md#software-regression) at the PR #91 source; developer preparation and conditional recovery, no automatic trace integration |
| PR #90, final head `bf592fa` | Merged into main at `ec41b0c` | Original head `bfc5388` carried reviewed PR #89 tree `c34ea15099480335cdf9263a1e6e5e48068a465e`; final head additionally contains PR #91 |
| Shadow-harmonic PR #85 | Merged into main at `c166e15`, before PR #90 | [Separate shadow study and 629-test/74-scenario record](validation.md#a-shadows-push-on-a-holes-centre--november-12-2026); inherited branch evidence, not a combined-source retest |
| Finite-material PR #88, `ed39d2c`, and documentation PR #89, `8cd6e93` | Merged into their dependency bases | [Earlier inverse evidence](validation/finite-free-centre.md), [documentation review](validation/documentation-pr88-state.md); merging a dependency branch does not establish main inclusion |
| Join PR #86, `dcb14e5`, based on frame PR #84 | Reviewed predecessor of this source | [Circle-consistent final assembly and separate directional study](validation/directional-free-arcs.md) |
| Frame PR #84, `123160e`, based on corner PR #83 | Reviewed predecessor; frame upgrade also on main | [Frame transport and mixed-support evidence](validation/curve-blur-frames.md) |
| Corner PR #83, `48e4bb5`, and rank-repair source `185d682` | Earlier implementation/evidence sources | [Covariance corners](validation/anisotropic-corners.md), [rank rejection](validation/directional-blur-rank.md); counts belong to their own revisions |
| Source-space research PR #79, merged into `codex/source-observation-context` at `98862f8` | Separate lineage | Source-observation/PSF/response research APIs from that branch are absent here |

At this readback, integrated main's
[Validate workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43330831086)
and PR #91's earlier
[Validate workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43328477717)
are **in progress**, with no conclusion. The completed local 899-test result at
`6539905` predates main's combined source. Main's additional shadow-harmonic
change modifies `backend/sheet.py` and two test modules relative to that
candidate; the new combined source needs its own completed regression result.

These are timestamped states, not live indicators. The earlier
[PR #91 source snapshot](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/blob/65399053b45f3c38a9d6d2084bc2315aac9bd87e/docs/project-status.md)
and other open/draft and CI
snapshots remain in the [PR #88 documentation record](validation/documentation-pr88-state.md),
[preceding review](validation/documentation-main77-state.md) and source-bound
validation reports. Local tests, hosted CI, branch inclusion, installation,
deployment and physical acceptance remain separate evidence.

## Available here

The single-user workbench traces one planar, constant-thickness part, uses
supplied scale and thickness, constructs CAD and exports geometry. Reference
sheet tracing adds a homography, one radial lens term, subpixel edge
measurements, optional design-intent fitting and entered-thickness correction
under the [documented model](reference-sheet.md). The optional Ollama assistant
receives text context and proposes explicit settings changes; it receives no
photograph or CAD geometry.

Directional covariance is estimated from rise widths in the **rectified
measurement image**, after resampling and smoothing. It supplies normal-specific
edge/wall widths and an approximate scalar for other stages. It is not a
separately calibrated sensor PSF. Supported nonparallel corners use its full
covariance. Known uniform thickness scales transport blur into supported curve
frames; mixed frames retain their documented approximation/refusal policies.
Final accepted arcs use circle-consistent joins, with bounded recovery or
refusal when a join is unavailable. See [stage limits](reference-sheet.md#3-segmentation-and-sub-pixel-edges),
[blur frames](blur-frames.md) and [curved joins](curved-joins.md).

`backend.finite_shape` and `backend.finite_centre_fit` expose the conditional
[finite-material developer operators](finite-shape-inverse.md).
`backend.finite_observations` prepares an immutable measured-ring crop and fixed
samples in explicit global/crop frames. None is called by automatic trace/build
or exposed through an HTTP mode. The older frozen kernel under
`studies/verification/` serves its own level-set comparison.

Source-context capture, raw-source fitting, response calibration and set-inversion
APIs from the other research branch must not be assumed available. Unfinished
local performance experiments are outside this documented source and its test
claims. Use [developer tools](developer-tools.md) for runnable entry points and
`/docs` on this checkout's running backend for its HTTP contract.

## Remaining integration work

The centre/radius/chord inverse is conditioned on a supplied normal, homography
and covariance. Its studies assess numerical behavior under those hypotheses;
they do not establish adequate optics for an arbitrary photograph, a global
optimum or a physical error bound. The moment experiment retains
background-sensitive results and incompatible covariance proposals.

The measured-ring bridge fixes the known whole-sheet initialization problem.
The paired replay completes all ten available fits, but only three of twelve
declared records meet every target; two original upstream refusals remain.
Held-out samples are excluded from fitting cost but influence initialization
and moments, so they are conditional residual checks rather than independent
prediction. Individual fits take about 8–19 seconds on the recorded machine;
interactive latency remains unqualified.

Automatic adoption still needs adequate acquisition and thickness models,
independent recovery checks, bounded-work performance evidence, and one chosen
boundary preserved through preview, native CAD and exports. The existing
16-case directional study does not qualify this new algorithm.

Use the [validation overview](validation.md) for source-bound results. No
real-phone/caliper benchmark, native slicer acceptance or physical print
qualification is established by the synthetic studies. The primary local
`codex/slicer-integration` checkout is a separate preserved worktree; this
documentation update does not install or replace it.
