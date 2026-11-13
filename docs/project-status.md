# Source scope and verification status

## Current source snapshot — November 13, 2026, 19:59 UTC

Main is `6bb959c70b60ee8bbd15c4599249b21dbe25e077`, tree
`104e1b1bce8bb84dc3b3df5e7c737cc9f03cca32`. It includes the source-cell mean
from [PR #105](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/105),
the two-direction edge-width repair from
[PR #107](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/107),
and the area-sensitivity/linear-acquisition operators from
[PR #108](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/108).
Those three PRs and documentation
[PR #109](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/109)
are merged at this readback. PR #109 merged at 18:23 UTC and changed only
documentation. The subsequent documentation
[PR #110](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/110)
merged at 18:59 UTC. Documentation
[PR #111](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/111)
merged at 19:25:32 UTC and added the local recovery snapshot; its tree matches
this main revision. PR #106 merged into its research
base after PR #105 closed; its documentation reached main through PR #108.

| Capability in this source | Scope and evidence |
| --- | --- |
| Photo tracing, measurement, CAD and export | User workflow; two-direction parts can use measured widths per edge without an identified covariance. Their corners and curves retain the scalar model. [Tracing method](reference-sheet.md#3-segmentation-and-sub-pixel-edges) |
| Gaussian finite-material inverse | Developer Python API; four geometry parameters with supplied chord normal and optics. [Contract](finite-shape-inverse.md) |
| Source-cell area and staged acquisition mean | Developer Python APIs with supplied geometry, levels, kernels and affine sampling; [128 saved-stage comparisons](validation/finite-acquisition-mean.md) |
| Five unrounded area sensitivities and signed linear propagation | Developer Python APIs; [259 focused tests and 33 study rows](validation/finite-cell-sensitivity.md), without an inverse-recovery result |
| Five-geometry-parameter acquisition-aware recovery with unknown brightness | Absent from this main-based runtime. A [separate local candidate](finite-acquisition-recovery.md) has two completed, failed recovery protocols; it is not an HTTP mode or automatic correction |

Hosted checks are tied to their published heads:

| Published source | Workbench | Reference library |
| --- | --- | --- |
| PR #108, `f54e47a443015c2e4701a143c4ac1c469595b731` | [43475029242](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43475029242): completed, success | [43475029376](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43475029376): completed, success |
| PR #109, `88a6d78f2807ae3eef3f6bf4bc229849321717ce` | [43478504807](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43478504807): completed, success | [43478504825](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43478504825): completed, success |
| PR #110, `8c72d873ae7871584f5c2ca9d12ac5d4bbdfab96` | [43484991562](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43484991562): completed, success | [43484991878](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43484991878): completed, success |
| PR #111, `b6ba24992260d49fd0a88a53057799c4f7c85e67` | [43491926326](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43491926326): completed, success | [43491926158](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43491926158): completed, success |

These readbacks do not extend a run to the combined main commit or this later
documentation change. Merge, hosted checks, installed runtime, real-camera
accuracy and physical acceptance remain separate.

The [documentation review](validation/documentation-coupled-state.md) audits this
main-based source. Use [available tools](#available-here) and [remaining integration work](#remaining-integration-work)
for current capabilities. Earlier snapshots below are historical records; their open
PR states and absent-module statements describe their own source and time.
The primary `codex/slicer-integration` checkout remains separate and unchanged.

## Separate local recovery research

The [recovery method](finite-acquisition-recovery.md) describes local candidate
`e6e2c2881add2cc594f4a59d713edf8a9ddde665`, not the runtime above. The original
source `7ec6803` records 4/12 matched passes; the separately admitted smooth-proposal
continuation records 9/12: four smooth, four staged and one PNG. Both retain all
24 cases, including 12 adverse cases, and both protocols exit 1. The candidate's
459 focused tests pass. Three PNG cases still miss the original targets.

The original saved-data auditor exits 1 with 14 pre-cast reference-area delta
checks that rounded saved coverage cannot reproduce. The
[result and evidence extract](validation/finite-acquisition-recovery.md) preserves
that failure, conditional reserved-pixel use, tied PNG candidates and the lack of
independent forward/rank/physical qualification. This documentation change
includes reports and static excerpts, not the candidate runtime or full raw archive.

The [coupled seven-parameter continuation](finite-acquisition-coupled.md) and
[paired-auditor design](finite-acquisition-saved-audit.md) are newer, uncommitted
authoring snapshots. No new tests, model/study execution or paired audit has
run. Both complete recovery archives now have verified local member hashes
and sizes; these ZIPs and candidate modules remain outside this publication.
All prior target failures and reference-precision limits remain in force.

## Available here

The single-user workbench traces one planar, constant-thickness part, uses
supplied scale and thickness, constructs CAD and exports geometry. Reference
sheet tracing adds a homography, one radial lens term, subpixel edge
measurements, optional design-intent fitting and entered-thickness correction
under the [documented model](reference-sheet.md). The optional Ollama assistant
receives text context and proposes explicit settings changes; it receives no
photograph or CAD geometry.

Current main also fits a nonnegative soft-shadow kernel from paper around the
part and uses a normalized excess-error diagnostic before applying its modelled
edge level. The near band also selects smoothness, so this is not untouched
validation. When prior selection lacks enough data, that diagnostic is zero
by construction. Rejected shadows retain the line method and a trace note. The
[paper-light record](validation.md#the-papers-light-as-a-fitted-shadow--november-13-2026)
retains synthetic improvements, regressions and partial contact-shadow recovery;
this is separate from the known-map acquisition experiment.

Directional covariance is estimated from rise widths in the rectified
measurement image. It supplies normal-specific edge/wall widths and an
approximate scalar for other stages; it is not a calibrated sensor PSF.
When that covariance is unavailable, sufficiently supported directional bins
can still supply separate edge-search widths. A matching covariance used to
blur the paper-shadow model is not passed off as an identified covariance for
corner or curve correction. Those paths retain their scalar fallback.
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

`backend.finite_aperture` and `backend.finite_acquisition` supply independent
source-cell coverage and the literal rounded acquisition chain.
`backend.finite_aperture_sensitivity` supplies five unrounded area columns;
`backend.finite_acquisition_linear` propagates signed float64 fields through a
separate fixed linear model. These operators are available here, but are not
called by `fit_circular_segment`, automatic tracing or an HTTP route. Turning
off sRGB8 in the staged mean does not remove its float32 casts.

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
post-hoc rotation identity motivated the separate
[finite-chord derivative test](validation/finite-normal-derivative.md), whose
complete result retains its failed protocol and numerical limitations.
Locally distinguishable covariance changes can absorb sampling/resampling
mismatch rather than identify a physical camera PSF.

The acquisition study now supplies a controlled counterexample to second-moment
Gaussian closure. A subsequent source-cell mean now has
[independent supplied-stage qualification](validation/finite-acquisition-mean.md).
A main-branch inverse would need the separately
[checked unrounded derivatives](finite-cell-sensitivity.md), observed-only
seeds and bounds, brightness/rank diagnostics, a bounded search for undefined
derivatives or rounded stages, and prospective recovery checks. The separate
[local prototype](finite-acquisition-recovery.md) implements those research
mechanisms, but its two failed protocols leave recovery and adoption unresolved.
The current five-query coupled controls do not prove five-parameter rank after
two unknown brightness levels. Supplied source assumptions and observed camera calibration remain
distinct. Neither study automatically corrects CAD.

Automatic adoption also needs supported acquisition and thickness models,
independent recovery checks and one chosen boundary preserved through preview,
native CAD and exports. No real-phone/caliper benchmark, native slicer acceptance
or physical print qualification follows from the synthetic studies.

## Historical source and publication snapshots

The following records preserve their original branch, date and evidence scope.

## Historical cell-sensitivity publication context

This candidate follows documentation PR #106's tree
`278cb9abf663b061803e467db06c5a545fc3eb52`. At publication readback, main is
`b4a7e304e3f0211fe4f6db13834c709fc228381c`, with PR #105's tree
`68f03a8d408dd10b32f4856e5da87260e53b91ac`. PR #106 merged into the research
branch; this main-based candidate also carries its reviewed documentation.
The numerical-source bytes are unchanged by that publication alignment. It adds
[five unrounded cell-area sensitivities and a fixed linear acquisition API](finite-cell-sensitivity.md),
with no tracing, Gaussian-fitter or HTTP integration. The first numerical run
at `c47214d098a234f28784cb174429e687e799a2bf` passes 259 focused tests and all
33 prescribed study rows, retaining eight deliberately withheld cell results.
The [complete qualification](validation/finite-cell-sensitivity.md) records
independent comparisons, source pins, audit limitations and the lack of an
actual recovery or identifiability result. Earlier snapshots below retain
their original dates and source scope; no installed or physical result follows.

## Earlier source snapshot — November 13, 2026, 16:58 UTC

These are timestamped source states, not live release indicators. This
documentation update follows draft
[PR #105](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/105).
Its published head `0866578dfd139be5fd572fd93fb65fe7607de529` has tree
`68f03a8d408dd10b32f4856e5da87260e53b91ac`, identical to local documentation
base `85541544047e71e8c494bc95ba90ca8df389376a`.

| Source | State at readback | Verification boundary |
| --- | --- | --- |
| Main `f2e0fd6a68a4ab26f6eea92a95ebbda673953193` | Includes merged PR #104, tree `72862db3d2c34b758bdd2e98f1cf8e88795c3cb6` | Earlier acquisition evidence and PR #103's paper-light model; no PR #105 source-cell API yet |
| PR #105, head `0866578dfd139be5fd572fd93fb65fe7607de529` | Open draft, unmerged | Source-cell forward APIs and complete supplied-stage qualification; no geometry recovery or automatic integration |
| PR #105 hosted workbench check | [Run 43466734083](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43466734083), in progress, no conclusion | Belongs to that published head; this documentation update needs its own checks |

The [documentation review](validation/documentation-mean-state.md) records the
current text/API audit. The primary `codex/slicer-integration` checkout is
preserved separately. No installed runtime, deployment or physical acceptance
follows from these source states.

## Historical source-cell candidate context

This candidate extends the evidence package below with independent
[analytic source-cell integration and discrete acquisition means](finite-acquisition-mean.md).
Its publication base is main `f2e0fd6a68a4ab26f6eea92a95ebbda673953193`,
including merged PR #104. That base's tree exactly matches the reviewed
`72862db3d2c34b758bdd2e98f1cf8e88795c3cb6`; no production-source change arrived
between the numerical work and this base readback.
It adds no automatic tracing or inverse-fit integration. The
[complete comparison](validation/finite-acquisition-mean.md) retains all 128
saved-coverage/analytic-D/encoding comparisons across 32 original output records.
Analytic query discrepancies are at most `7.6294e-5` unquantized and `3.0518e-5`
encoded intensity levels, with no changed encoding codes.

Numerical evidence and the 1,173-test software result bind source `521c318`.
A subsequent metadata-only workspace repair passes 145 focused tests and a
22-check source-equivalence audit. The original 12 failed controls and first
mathematical audit's 32 arithmetic mismatches remain archived. Source freezes,
workspace repair, portable saved-data checks and any later hosted CI have
separate receipts. The [182-artifact archive](../studies/fixtures/finite-acquisition-mean-v1/README.md)
establishes no geometry recovery, physical-camera accuracy or automatic CAD
correction. This developer branch is not an additional main-branch capability.

## Earlier acquisition-evidence snapshot — November 13, 2026, 16:02 UTC

The publication base is main
`68a67e766956ac41a3b73ae73d4ac553ef47db26`, including merged
[PR #103](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/103)
and its fitted soft-shadow paper-light model. This candidate preserves that
production source and adds the complete
[acquisition-operator study](finite-acquisition-operator.md), saved-data tools
and documentation. The primary `codex/slicer-integration` checkout is separate
and preserved.

The new study's source freeze is
`0714aadf04f6af2130bfe5af70d9dafbbe4677a7`, not current main. Its archive binds
123 artifacts, including all 87 recorded runtime/input source files. The
[portable workflow](../studies/fixtures/finite-acquisition-operator-v1/README.md)
checks those source bytes as data, retaining every capture, failed attempt and
raw scalar marker. It makes no new model calls or current-pipeline qualification.

The 16 scenes yield 32 paired output-scale records. A moment-matched continuous
Gaussian remains incompatible with the frozen one-level criterion in 9/32
unquantized and 16/32 PNG comparisons, with one PNG inconclusive. The original
bootstrap exits 1; its explicit continuation exits 0 numerically but retains
320 raw scalar-serialization failures. Saved normalization changes no category.
See the [complete evidence and limits](validation/finite-acquisition-operator.md).

The earlier [normal derivative qualification](validation/finite-normal-derivative.md)
also retains its original exit 1, one work-limited query and compressed-map
error-estimation limitation. Later analytic-normal research is available in
[its pinned source lineage](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/blob/0f1adbd391f7fa015f458cca60dcfe2a0e2dad9e/docs/validation/finite-analytic-normal-information.md);
it must not be inferred to be integrated into this main-based source.

Documentation and saved-data checks do not rerun application/browser suites.
Hosted checks for this candidate require its own published head. No installed
runtime, deployment, camera/caliper benchmark, native slicer or print acceptance
is established by this refresh.

At this readback, PR #103's own head
`7f60d4f5f06dd7cd1542315d2c92daf86b4045f2` has a successful
[Validate workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43381432969).
That hosted result belongs to that head, not this documentation/evidence
candidate or a later main revision.
The [documentation review](validation/documentation-acquisition-state.md)
records the current refresh's local verification and coverage.

## Historical PR #95 documentation context

The preceding documentation followed published draft
[PR #95](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/95),
head `1f51bae35eb862dca4a259016cc31bf1504207f9`, tree
`1a20178c6c0154cd848937ccac138e0e34696212`. It adds the frozen
residual-information diagnostic, complete failed outcome and independent
saved-data tools over PR #94's documentation and PR #93's affine candidate.
The [PR #95 documentation review](validation/documentation-pr95-state.md)
covers the workbench, research contracts and companion reference library.
The primary `codex/slicer-integration` checkout is preserved separately.

The affine candidate's software was committed at `f3bcd98`, with integration
checkpoint `faf9b5a600ed64a226307da93615b086a6c38669`. Its
[source-bound qualification](validation/finite-affine-batch.md) retains the
943-test interval, frozen comparison and failed continuation comparator.
The [residual-study record](validation/finite-residual-information.md) binds
the subsequent research without replacing earlier evidence. Documentation-only
checks do not rerun or extend that software qualification.

## Historical repository and CI snapshot — November 13, 2026, 02:05 UTC

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
