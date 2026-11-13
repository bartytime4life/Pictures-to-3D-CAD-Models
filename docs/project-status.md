# Source scope and verification status

This subsequent research candidate adds the
[experimental finite-chord normal derivative](finite-normal-derivative.md)
over documentation PR #96. The [new qualification](validation/finite-normal-derivative.md)
retains the original exit 1, one work-limited query and a resolved compressed-map
error-estimation limitation. The new module is separate from automatic tracing,
HTTP and the existing four-parameter inverse. Its source and numerical evidence
are bound independently; the historical publication snapshot below predates it.

This documentation follows published draft
[PR #95](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/95),
head `1f51bae35eb862dca4a259016cc31bf1504207f9`, tree
`1a20178c6c0154cd848937ccac138e0e34696212`. It adds the frozen
residual-information diagnostic, complete failed outcome and independent
saved-data tools over PR #94's documentation and PR #93's affine candidate.
The [current documentation review](validation/documentation-pr95-state.md)
covers the workbench, research contracts and companion reference library.
The primary `codex/slicer-integration` checkout is preserved separately.

The affine candidate's software was committed at `f3bcd98`, with integration
checkpoint `faf9b5a600ed64a226307da93615b086a6c38669`. Its
[source-bound qualification](validation/finite-affine-batch.md) retains the
943-test interval, frozen comparison and failed continuation comparator.
The [residual-study record](validation/finite-residual-information.md) binds
the subsequent research without replacing earlier evidence. Documentation-only
checks do not rerun or extend that software qualification.

## Repository and CI snapshot — November 13, 2026, 02:05 UTC

This is November 12 in the project's America/Chicago timezone. These are
readback states, not live release indicators.

| Source lane | State at this readback | Evidence boundary |
| --- | --- | --- |
| Main, `1d32c432da633df6bb47db2df7b0e9c23de11c81`, tree `d75d6c76cd5d0529c75e792da7d0fe384d47635c` | Includes merged documentation PR #92 and prior PRs #84, #85, #90 and #91 | Does not include PRs #93–#95 at this snapshot |
| Affine PR #93, head `f7d116e74b028beffe2dee797518767d0e5b7222` | Open draft against main; unmerged | [943 local Python tests, build and lint](validation/finite-affine-batch.md#software-regression); fixed-workload comparison; no new installed-machine or physical result |
| Documentation PR #94, head `2f9abf2a4d2e1b809d2f3115f04fc04470682c4f` | Open draft based on PR #93 | [Documentation-only checks](validation/documentation-pr93-state.md); inherited non-Markdown blobs preserved |
| Residual study PR #95, head `1f51bae35eb862dca4a259016cc31bf1504207f9` | Open draft based on PR #94 | [Complete failed replay](validation/finite-residual-information.md), 12 retained rows and 9,683 saved-data audit checks; no automatic correction |
| Finite-chord normal derivative | Analytic derivation; numerical implementation and qualification pending | [Derived proposal](finite-residual-information.md#finite-chord-shape-derivative-a-derived-proposal); no published callable operator or new numerical result |
| Earlier finite-material, corner, frame and join sources | Inherited implementation; original records retained | [Validation overview](validation.md) binds each result to its tested revision |
| Source-space research PR #79, merged into `codex/source-observation-context` at `98862f8` | Separate lineage | Source-observation/PSF/response-calibration APIs from that branch are absent here |

PR #93's own
[Validate workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43338583640)
completed with **success**. PR #94's final-head
[run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43343651239)
also completed with **success**, bound to `2f9abf2`. PR #95's
[run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43347556524)
is **in progress**, with no conclusion, bound to `1f51bae`. Later commits need
their own CI. Hosted CI success is separate from the residual experiment's
retained scientific failure and does not establish merge, installation,
deployment or physical qualification.

The [preceding PR #93 documentation review](validation/documentation-pr93-state.md),
[PR #91 review](validation/documentation-pr91-state.md) and
[earlier status snapshot](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/blob/1f51bae35eb862dca4a259016cc31bf1504207f9/docs/project-status.md)
preserve their original branch and CI states. Local checks, hosted CI, branch
inclusion, installation, deployment and physical acceptance remain distinct.

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

The [residual-information diagnostic](validation/finite-residual-information.md)
separates fixed-normal covariance sensitivity from brightness and geometry, while
retaining unknown normal sensitivities and an overall failed protocol. A
post-hoc rotation identity and the derived finite-chord formula motivate a new
prospective derivative test; they do not qualify a numerical implementation.
Locally distinguishable covariance changes can absorb sampling/resampling
mismatch rather than identify a physical camera PSF.

Automatic adoption also needs supported acquisition and thickness models,
independent recovery checks and one chosen boundary preserved through preview,
native CAD and exports. No real-phone/caliper benchmark, native slicer acceptance
or physical print qualification follows from the synthetic studies.
