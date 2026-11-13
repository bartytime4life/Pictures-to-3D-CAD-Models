# Source scope and verification status

This checkout layers the affine finite-material candidate over main at
`1d32c432da633df6bb47db2df7b0e9c23de11c81`, after documentation PR #92.
The candidate's code was committed at `f3bcd98`; its integration checkpoint is
`faf9b5a600ed64a226307da93615b086a6c38669`. The
[source-bound qualification record](validation/finite-affine-batch.md) identifies
its exact software, frozen plan, runner and preserved original comparator.
The [documentation review](validation/documentation-affine-state.md) covers
current guides and the companion library. This checkout is separate from the
preserved primary `codex/slicer-integration` worktree.

The merged [PR #91](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/91)
at `65399053b45f3c38a9d6d2084bc2315aac9bd87e` added the
[immutable measured-ring observation bridge](finite-shape-inverse.md#prepare-a-measured-ring-observation-set).
It merged through PR #90 into main at
`ec41b0ce34746c8fffd17fd7beec2b7cba33413c`, which also includes PR #85's
shadow-harmonic change. PR #92 changes only documentation relative to that
main. Its [dated review](validation/documentation-pr91-state.md) retains its
original source, counts and CI snapshot.

## Repository and CI snapshot — November 13, 2026, 00:23 UTC

This is November 12 in the project's America/Chicago timezone.

| Source lane | State at this readback | Evidence boundary |
| --- | --- | --- |
| Main, `1d32c43`, tree `d75d6c76cd5d0529c75e792da7d0fe384d47635c` | Includes merged documentation PR #92 and prior PRs #84, #85, #90 and #91 | Main does not yet include this affine candidate at this snapshot |
| Affine candidate, integration checkpoint `faf9b5a` | Code `f3bcd98` integrated with both main revisions | [943 local Python tests, build and lint](validation/finite-affine-batch.md#software-regression); source-bound fixed performance comparison; no new browser or installed-machine result |
| PR #92, head `c69d37f` | Merged at 23:58 UTC on November 12 | [Documentation-only review](validation/documentation-pr91-state.md); every inherited non-Markdown byte preserved |
| PR #91, `6539905`, through PR #90's final `bf592fa` | Included in main at `ec41b0c` | [899 local Python tests](validation/finite-photo-intensity-v2.md#software-regression) belong to the original PR #91 software interval |
| Shadow-harmonic PR #85, merged at `c166e15` | Included in main before PR #90 | [629-test/74-scenario branch record](validation.md#a-shadows-push-on-a-holes-centre--november-12-2026) remains historical |
| Earlier finite-material, corner, frame and join sources | Inherited implementation; original records retained | [Validation overview](validation.md) binds each result to its tested revision |
| Source-space research PR #79, merged into `codex/source-observation-context` at `98862f8` | Separate lineage | Source-observation/PSF/response-calibration APIs from that branch are absent here |

Integrated main `ec41b0c`'s
[Validate workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43330831086)
completed with **success** at 00:05 UTC on November 13. PR #91's earlier
[Validate workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43328477717)
also completed with **success**. These hosted results are separate from the
candidate's new 943-test local interval and restricted timing experiment.
They do not establish CI for an unpublished later candidate commit.

These are timestamped states, not live indicators. The [PR #91 review](validation/documentation-pr91-state.md),
[PR #88 review](validation/documentation-pr88-state.md) and other dated records
preserve their original open/draft and CI snapshots. Local checks, hosted CI,
branch inclusion, installation, deployment and physical acceptance are distinct.

## Available here

The single-user workbench traces one planar, constant-thickness part, uses
supplied scale and thickness, constructs CAD and exports geometry. Reference
sheet tracing adds a homography, one radial lens term, subpixel edge
measurements, optional design-intent fitting and entered-thickness correction
under the [documented model](reference-sheet.md). The optional Ollama assistant
receives text context and proposes explicit settings changes; it receives no
photograph or CAD geometry.

Directional covariance is estimated from rise widths in the rectified
measurement image. It supplies normal-specific edge/wall widths and an
approximate scalar for other stages; it is not a calibrated sensor PSF.
Supported nonparallel corners use its full covariance. Uniform thickness scales
transport blur into supported curve frames. Mixed frames retain their
approximation/refusal policies. Final accepted arcs use circle-consistent joins,
with bounded recovery or refusal. See [stage limits](reference-sheet.md#3-segmentation-and-sub-pixel-edges),
[blur frames](blur-frames.md) and [curved joins](curved-joins.md).

`backend.finite_shape` and `backend.finite_centre_fit` expose the conditional
[finite-material developer operators](finite-shape-inverse.md).
`backend.finite_observations` prepares immutable measured-ring observations.
`backend.finite_affine` adds shared-panel evaluation for exactly affine maps;
the circular-segment mean API dispatches to it while preserving its result
schema. Projective maps retain the scalar path. See the
[derivation and work/memory contracts](finite-affine-evaluation.md).
None is called by automatic trace/build or exposed through an HTTP mode.

Source-context capture, raw-source fitting, response calibration and set-inversion
APIs from the separate research branch must not be assumed available.
[Developer tools](developer-tools.md) lists runnable entry points and their
side effects; `/docs` on this checkout's running backend describes its HTTP API.

## Remaining integration work

The centre/radius/chord inverse still requires a supplied normal, homography and
covariance. Its studies do not establish adequate optics for arbitrary photos,
a global optimum or a physical error bound. The moment experiment retains
background-sensitive and incompatible covariance proposals.

The measured-ring bridge fixes a known whole-sheet initialization problem.
Its original paired replay completes all ten eligible fits, but only three of
twelve records meet every target; two upstream refusals remain. Held-out samples
are excluded from fitting cost but influence initialization and moments, so
they are conditional residual checks rather than independent predictions.

That replay's original 8–19-second fits remain historical evidence. The
[affine comparison](validation/finite-affine-batch.md) records **3.84× faster
complete fits** across three predeclared datasets, with 2.75–3.91-second medians.
All 36 archived rows retain their prior completion flags and target passes.
These fixed-workload results leave interactive latency, broader workloads and
optical-model adequacy unqualified.

Automatic adoption also needs supported acquisition and thickness models,
independent recovery checks and one chosen boundary preserved through preview,
native CAD and exports. No real-phone/caliper benchmark, native slicer acceptance
or physical print qualification follows from the synthetic studies.
