# Source scope and verification status

This candidate builds on published documentation draft
[PR #101](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/101),
head `9db5f3f506020d8673ffa78fb55b7a1b8ee5dbb5`, tree
`84c9f0fb3930b76fb96d33424cb5fde56a01f9b2`.
The [preceding documentation review](validation/documentation-pr100-state.md)
covers its PR #100 base. This candidate adds the separately frozen
[analytic-normal experiment](validation/finite-analytic-normal-information.md),
which passes all 578 derivative comparisons and ten bounded joint-trial checks.
It retains residual/geometry counterexamples and adds no automatic tracing or
inverse-fitter integration. Its source freeze and full evidence are bound in
that record; the repository snapshot below retains its earlier timestamp.

At the separate **November 13, 2026, 05:18 UTC** readback, PR #101 remained
open, draft and unmerged at the head above. Its
[workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43367933355)
and [reference-library run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43367933387)
both completed successfully. Main still had the head listed below. These runs
qualify the published documentation base, not this subsequent analytic-normal
candidate.

## Repository and CI snapshot — November 13, 2026, 04:40 UTC

This is November 12 in America/Chicago. Main remains
`1d32c432da633df6bb47db2df7b0e9c23de11c81`, tree
`d75d6c76cd5d0529c75e792da7d0fe384d47635c`, including documentation PR #92.
All eight PRs below are **open, draft and unmerged**. The table follows their
dependency order; none is included in main at this readback.

| PR and source lane | Published head | Base branch | Workbench CI at this head |
| --- | --- | --- | --- |
| [#93: affine evaluation](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/93) | `f7d116e74b028beffe2dee797518767d0e5b7222` | `main` | [Success](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43338583640) |
| [#94: documentation](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/94) | `2f9abf2a4d2e1b809d2f3115f04fc04470682c4f` | `codex/finite-affine-batch` | [Success](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43343651239) |
| [#95: residual diagnostic](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/95) | `1f51bae35eb862dca4a259016cc31bf1504207f9` | `codex/documentation-pr93-state` | [Success](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43347556524) |
| [#96: documentation](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/96) | `6c6edf5d304be38fba64b7081d3c112ea31373f6` | `codex/finite-residual-information-published` | [Success](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43350007631) |
| [#97: normal derivative V1](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/97) | `d40502fed3de93989c73d4c8cf614f6f6b6d7e45` | `codex/documentation-pr95-state` | [Success](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43353895468) |
| [#98: documentation](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/98) | `d496a2b03e8bca02b813b7082b44ac1205b6b8ae` | `codex/finite-normal-derivative` | [Success](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43355697191) |
| [#99: normal error control V2](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/99) | `5b6ca989cb9a414655e35b4f2e3d4c7fd5b4b769` | `codex/documentation-pr97-state` | [Success](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43360856992) |
| [#100: reference-node diagnostic](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/100) | `f1f0bba313f68d5dc48fdb6e329b0e0535b1903e` | `codex/finite-normal-error-control` | [Success](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43363843583) |

PR #96 also has a successful
[reference-library run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43350007619)
at its listed head. Library CI uses path filters; a workbench success is not a
later library run. These conclusions belong to the listed source heads, not
this subsequent documentation change. Local checks, hosted CI, merge,
installation, deployment and physical acceptance are separate observations.

Earlier timestamped states remain in the
[preceding source-status page](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/blob/f1f0bba313f68d5dc48fdb6e329b0e0535b1903e/docs/project-status.md)
and dated [documentation reviews](validation.md). The primary
`codex/slicer-integration` checkout remains separate at
`d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`.

## Available in this reviewed source

| Component | Available behavior | Scope and evidence |
| --- | --- | --- |
| Workbench | Trace one planar, constant-thickness part; set measured scale and thickness; review, build and export CAD | [User workflow](../README.md#try-the-complete-workflow), [engineering model](engineering-model.md) |
| Reference-sheet tracing | Sheet-plane homography, one radial lens term, subpixel edges, optional design-intent fitting and entered-thickness correction | [Method and assumptions](reference-sheet.md) |
| Directional blur and fitted geometry | Empirical rectified-image covariance for supported nonparallel corners; uniform blur-frame transport; circle-consistent final joins and bounded recovery/refusal | [Corner model](anisotropic-corners.md), [frames](blur-frames.md), [joins](curved-joins.md) |
| Optional Ollama assistant | Text context and settings proposals requiring explicit Apply | [Setup and limits](ollama.md); no photograph, outline vertices or mesh sent to the model |
| Finite-material developer APIs | Circular-segment means, four-column shape Jacobian, supplied-normal centre/radius/chord inverse, immutable measured-ring preparation and shared-panel affine evaluation | [Python contracts](finite-shape-inverse.md), [affine evaluation](finite-affine-evaluation.md) |
| Normal-angle developer API | Signed probability derivative per source-plane radian, estimated errors, retained statuses and bounded work | [API](finite-normal-derivative.md), [V2 correction](finite-normal-error-control.md) |
| Reference-node study | Standalone arithmetic diagnostic and saved-data auditor for a restricted 26-control family | [Method](finite-normal-oracle-conditioning.md), [archive](../studies/fixtures/finite-normal-oracle-conditioning-v1/README.md) |
| Companion library | Offline handbook, calculators, local Photos workspace, OpenSCAD examples and independent mesh checks | [Library guide](../reference-library/README.md), [separate verification](../reference-library/VERIFICATION.md) |

The finite-material and normal-angle operators have no HTTP mode and are not
called by automatic trace/build. The normal derivative does not add a fifth
column to the existing Jacobian or fit an angle. Source-observation, raw-source
fitting, response-calibration and set-inversion APIs from the separate research
lineage are absent here. [Developer tools](developer-tools.md) lists runnable
commands and side effects; `/docs` on this checkout's running backend describes
its HTTP API.

## Numerical evidence and unresolved limits

| Study | Retained outcome | What remains unresolved |
| --- | --- | --- |
| [Measured-ring intensity replay](validation/finite-photo-intensity-v2.md) | Ten eligible fits complete; three of twelve records meet every target; two upstream refusals retained | Supplied optics and illumination; held-out samples influence preprocessing and remain conditional checks |
| [Affine evaluation](validation/finite-affine-batch.md) | 3.84× faster complete fits on three fixed datasets; all 36 prior rows and flags retained; 943 local Python tests | Broader workloads, interactive latency, physical adequacy; failed continuation comparator retained |
| [Residual-information V1](validation/finite-residual-information.md) | Overall protocol failed; ten normal columns unknown; ten fixed-normal bounded steps retained | Normal-aware residual qualification and physical interpretation of covariance changes |
| [Normal derivative V1](validation/finite-normal-derivative.md) | Original exit 1, one panel-budget unknown and a resolved compressed-map error miss retained | Historical result; later code does not rewrite it |
| [Normal error control V2](validation/finite-normal-error-control.md) | 417 scenes, 4,832 queries and 72 area checks pass frozen criteria; both original candidate controls pass separate high-precision checks; 1,081 final-source Python tests | General reference-oracle error allowance, certified numerical bounds and model adequacy |
| [Reference-node arithmetic](validation/finite-normal-oracle-conditioning.md) | All 26 controls pass; exact endpoint construction with binary64 interpolation reduces the largest observed reference error from `4.09099e-6` to `7.94156e-10` | Restricted family and represented quadrature rules; neither a general oracle replacement nor universal `1e-10` accuracy |
| [Analytic-normal residual diagnostic](validation/finite-analytic-normal-information.md) | All 578 comparisons, five normal controls, ten algebra controls and ten single joint trials pass; all original rows/flags retained | Three covariance directions persist; only 3/10 trials beat saved BGS held-out RMS; three worsen all synthetic geometry errors relative to archived baseline fits |

The larger software test count does not replace a scientific failure. None of
these conditional Gaussian studies identifies a physical camera PSF. Covariance
changes can absorb sampling or resampling mismatch. The inverse still requires
a supplied normal, homography and covariance; the moment study retains
background-sensitive and incompatible proposals.

## Remaining integration work

The separate normal-aware residual diagnostic is now complete. It preserves
the original finite-difference failure and qualifies its new analytic normal
column independently. General projective reference error accounting remains
open. A qualified normal-aware inverse and acquisition/model adequacy are still
research dependencies; the one-step diagnostic is not an automatic feature.

Automatic adoption needs supported acquisition and thickness models,
independent recovery checks, bounded latency and one chosen boundary preserved
through preview, native CAD and every export. The saved fields do not completely
reconstruct the acquisition chain. No real-phone/caliper benchmark, native
slicer acceptance or physical-print qualification follows from these synthetic
studies. See the [roadmap](roadmap.md) and [independent checks](engineering-model.md).
