# Source scope and verification status

## Current source snapshot — November 14, 2026 UTC

The verified publication base is main
`9d15a1eec33b660455b05d7fedaea50faebc35fd`, tree
`1958ef5891f2f96e18eae252ed5fcf775df44a25`. It includes the source-cell mean
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
merged at 19:25:32 UTC and added the local recovery snapshot. Documentation
[PR #112](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/112)
merged at 20:23:44 UTC and added the then-unexecuted coupled proposal; its tree
was the preceding main revision. Documentation
[PR #113](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/113)
merged at 20:54:25 UTC and recorded the executed coupled/source-event studies
and corrected saved-only audit. The edge-blur correction in
[PR #114](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/114)
merged at 21:33:06 UTC. Documentation
[PR #115](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/115)
merged at 21:48:51 UTC. Documentation
[PR #116](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/116)
merged at 22:25:09 UTC. Documentation
[PR #117](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/117)
merged at 23:14:25 UTC and recorded the failed physical-corner census.
[PR #118](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/118)
merged at 23:24:40 UTC. It changes the synthetic renderer's colour-channel
noise, associated regressions and recorded reference-sheet results. Documentation
[PR #119](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/119)
merged at 23:40:24 UTC. It records contact-shadow observability studies and
capture guidance, without adopting a tracer change. Documentation
[PR #120](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/120)
merged at 23:54:08 UTC and records the saved inward construction.
Documentation [PR #121](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/121)
is also merged; its tree is the publication base above. It records the
completed negative literal probe. This refresh preserves those records and
adds the separately frozen observed-defect correction's first result. The
workbench runtime still matches PR #114: that correction removes fitted
paper-light variation before remeasuring supported edge widths on traces with
zero entered thickness. Positive-thickness traces retain the preceding width
path. See [eligibility, regressions and limits](reference-sheet.md#3-segmentation-and-sub-pixel-edges).
PR #106 merged into its research
base after PR #105 closed; its documentation reached main through PR #108.

| Capability in this source | Scope and evidence |
| --- | --- |
| Photo tracing, measurement, CAD and export | User workflow; two-direction parts can use measured widths per edge without an identified covariance. Their corners and curves retain the scalar model. [Tracing method](reference-sheet.md#3-segmentation-and-sub-pixel-edges) |
| Gaussian finite-material inverse | Developer Python API; four geometry parameters with supplied chord normal and optics. [Contract](finite-shape-inverse.md) |
| Source-cell area and staged acquisition mean | Developer Python APIs with supplied geometry, levels, kernels and affine sampling; [128 saved-stage comparisons](validation/finite-acquisition-mean.md) |
| Five unrounded area sensitivities and signed linear propagation | Developer Python APIs; [259 focused tests and 33 study rows](validation/finite-cell-sensitivity.md), without an inverse-recovery result |
| Five-geometry-parameter acquisition-aware recovery with unknown brightness | Absent from this main-based runtime. A [separate local candidate](finite-acquisition-recovery.md) has five completed, failed recovery protocols; it is not an HTTP mode or automatic correction |

Hosted checks are tied to their published heads:

| Published source | Workbench | Reference library |
| --- | --- | --- |
| PR #108, `f54e47a443015c2e4701a143c4ac1c469595b731` | [43475029242](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43475029242): completed, success | [43475029376](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43475029376): completed, success |
| PR #109, `88a6d78f2807ae3eef3f6bf4bc229849321717ce` | [43478504807](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43478504807): completed, success | [43478504825](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43478504825): completed, success |
| PR #110, `8c72d873ae7871584f5c2ca9d12ac5d4bbdfab96` | [43484991562](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43484991562): completed, success | [43484991878](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43484991878): completed, success |
| PR #111, `b6ba24992260d49fd0a88a53057799c4f7c85e67` | [43491926326](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43491926326): completed, success | [43491926158](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43491926158): completed, success |
| PR #112, `42f78743d4abeb84d96e100a2aa0849a11e470f6` | [43497998820](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43497998820): completed, success | [43497998949](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43497998949): completed, success |
| PR #113, `6b6683e7bbcb733c3c7d147b3508d4f08d86efe8` | [43505482613](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43505482613): completed, success | [43505482801](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43505482801): completed, success |
| PR #114, `918410db522c35c3582391a1ad8035195db46f34` | [43510351302](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43510351302): completed, success | No PR-triggered reference-library run listed at readback |
| PR #115, `897fd0cc6539e17a82344cf216e5a4565462f238` | [43512700142](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43512700142): completed, success | [43512700089](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43512700089): completed, success |
| PR #116, `f3bbc2bbdd5ae958be33050bf393c32557bc4085` | [43517704845](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43517704845): completed, success | [43517704839](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43517704839): completed, success |
| PR #117, `740e9483a619346010c3b99bc2ffeb63a5fa3b48` | [43524563678](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43524563678): completed, success | [43524563696](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43524563696): completed, success |

PR #120's workbench [43530191760](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43530191760)
and reference-library [43530191830](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43530191830)
checks both completed successfully at `12448a56b8bd306028f9f0556d2742de8801955b`.
Its merged tree matches that head. Automated code review did not complete
because of the reported usage limit; it is separate from those successful
workflow checks. These readbacks do not extend a run to this later
documentation change. No PR #118 or #119 hosted-check result is asserted here.
At the November 14, 2026 readback, PR #121's head
`4479152286e8eb435d4527f2cc9a6feba4c54e71` has a successful reference-library
[run 43534952226](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43534952226).
Its workbench [run 43534952161](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43534952161)
also completed successfully on the final readback. No result at its merge
commit is asserted; its merged tree matches that head. Later checks for
this refresh have separate status.
Merge, hosted checks, installed runtime, real-camera
accuracy and physical acceptance remain separate.

The [documentation review](validation/documentation-defect-corrector.md) audits this
main-based source. Use [available tools](#available-here) and [remaining integration work](#remaining-integration-work)
for current capabilities. Earlier snapshots below are historical records; their open
PR states and absent-module statements describe their own source and time.
The primary `codex/slicer-integration` checkout remains separate and unchanged.

## Separate local recovery research

The [recovery method](finite-acquisition-recovery.md) first describes local candidate
`e6e2c2881add2cc594f4a59d713edf8a9ddde665`, not the runtime above. The original
source `7ec6803` records 4/12 matched passes; the separately admitted smooth-proposal
continuation records 9/12: four smooth, four staged and one PNG. Both retain all
24 cases, including 12 adverse cases, and both protocols exit 1. The candidate's
459 focused tests pass. Three PNG cases miss the original targets in that
predictor run; the later continuations below retain their own results.

The original saved-data auditor exits 1 with 14 pre-cast reference-area delta
checks that rounded saved coverage cannot reproduce. The
[result and evidence extract](validation/finite-acquisition-recovery.md) preserves
that failure, conditional reserved-pixel use, tied PNG candidates and the lack of
independent forward/rank/physical qualification. This documentation change
includes reports and static excerpts, not the candidate runtime or full raw archive.

The later [coupled search](finite-acquisition-coupled.md) at `b9fe285` reaches
11/12 matched passes; [source events](finite-acquisition-events.md) at `cd85ef9`
stay at 11/12. Both full protocols exit 1 with all original 24 cases retained.
The first focused suites pass 548 tests/nine subtests and 653 tests/21 subtests.
Middle PNG still misses fraction and conditional reserved-residual targets.
[Full results and source bindings](validation/finite-acquisition-continuations.md)
are separate from this main runtime and application/browser evidence.

The historical paired audit records zero inconsistencies but 28 required
unknowns, exit 1. The coupled audit first fails 17 input-hash framing checks;
its separately admitted correction at `8507525` verifies all 1,191,323
implemented current checks, exit 0, with 24/24 current pre-cast comparisons
and all 28 historical unknowns retained separately. Its 54 tests/12 subtests
pass. See [audit scope and exclusions](finite-acquisition-saved-audit.md).
Neither audit covers the new event-phase ledger or establishes forward-model
accuracy. Four complete ZIPs have local member hash/size readback; candidate
runtime, auditor source, complete ZIPs and full candidate ledgers/arrays are
outside this documentation publication.

The [protected-source-bin proposal](finite-acquisition-protected.md) at
`79522b5` retains eight failed first controls and its full study remains unrun.
The [active-face follow-up](finite-acquisition-protected-active.md) preserves
its first result at `1dade8a`: 820 passes, one failed expectation and 33 passing
subtests, exit 1. The [dated first record](validation/finite-acquisition-protected-active.md)
and all 96 original input hashes stay unchanged.

The separately frozen expectation-only correction at `c1a9330` passes **821
selected tests and 33 subtests**. Its unchanged original **24-case study
completes at 11/12 matched passes, exit 1**. All 24 rows, the singular-map
exception and one adverse all-target pass remain retained. Middle PNG still
misses fraction and conditional reserved-residual targets; no protected trial
reaches literal evaluation.

The saved-only [physical-rounding diagnostic](finite-acquisition-physical-rounding.md)
at `b649ea3` passes 49 controls and independently verifies the one qualified
rational certificate. All **128 adjacent physical corners fail source
membership**, with zero arithmetic unknowns; physical bounds and arithmetic
floor pass for every corner. It makes no fitter, QP-solver, forward-model or
literal PNG call. This excludes only that adjacent box, not feasible points
elsewhere. [Complete outcomes and copied evidence](validation/finite-acquisition-physical-rounding.md)
preserve the 100-input and 104-input freezes.

The separately frozen [inward-point construction](finite-acquisition-inward-margin.md)
at `66df525dc06ad507b4c9b60c3eade969ff0ed677` preserves all 108 governing inputs.
Its 103 focused controls pass. The first saved diagnostic retains all 24 rows,
17 fits and the one qualified certificate, constructs one changed rational
point and checks all **128 new physical corners: every corner passes all five
original gates, with zero arithmetic unknowns**. The independent saved-data
audit passes **8,030 checks**. See [completed results and scope](validation/finite-acquisition-inward-margin.md).
This is represented local feasibility, not an actual PNG cost improvement.
The original 11/12 full recovery and earlier 0/128 census remain unchanged.
The separately frozen [paired literal test](finite-acquisition-inward-literal.md)
at `98fb1aeeb54bd13d3c4dd324f323736109d17d0d` adds four governing files,
preserving all 112 source bindings and 106 original artifacts. Its 162
selected controls pass, including one tiny real PNG operator control. The
actual pair exactly reproduces the incumbent on all nine baseline checks but
raises training cost **0.302031169350812 to 0.40923713513984694**. Its status is
`complete_no_improvement`, exit 1, with no protocol failure: the predetermined
candidate is rejected. Target cell 62 reaches code 92; collateral cell 33
changes 106 to 105. The independent saved mathematical audit passes 841
checks. See [the complete first output, stages and receipts](validation/finite-acquisition-inward-literal.md).

This pair adds two evaluations, 338 cell units and 10,478 stage units,
bringing the aggregate to 992 / 135,369 / 54,531,024 under unchanged caps.
It does not rerun full recovery, construct another point or integrate a fitter.
The separately frozen [observed-defect corrector](finite-acquisition-defect-corrector.md)
at `d986f1f2db12791b96aad21dcc4f1e7977029c40` preserves all preceding 112 inputs
within a 116-input closure. Its first selected suite passes **220 tests**;
the prospective total 218 was an addition error, preserved alongside the
actual result (58 new + 162 predecessor cases = 220). One equality-only
minimum-norm correction and one nearest tuple pass all five local gates.
The actual pair exactly reproduces `p0`, then lowers training cost to **0.0**
at all 135 saved queries. Only source 62 changes code, 93 to 92; source 33
stays at 106. This compares with accepted `p0`, not merely rejected `p1`.
Whole charged work is 2 / 338 / 1,942,766, including mathematical work and
the pair, giving aggregate 994 / 135,707 / 56,473,790 under unchanged caps.
See [the full first result and limits](validation/finite-acquisition-defect-corrector.md).

This local correction is implemented and tested in research. Fitter integration,
reserved checks and the complete original recovery protocol have not been
rerun for it. Zero quantized training residual does not identify unique or
true geometry. Candidate runtime,
tests, runners, original raw recovery artifacts, preceding full diagnostic
arrays and complete local ZIPs remain outside this documentation publication.

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
by construction. Rejected shadows retain the line method and a trace note. When a fitted model is accepted and removes at least 3 % of the paper light,
traces with zero entered thickness remeasure blur with its light variation
removed, then refit the shadow. Positive-thickness traces keep the previous
width path because the wall/support model has known failures with the changed
width. The [new synthetic result](validation.md#the-blur-beside-a-shadow--november-13-2026)
retains small-hole and sharp-corner regressions and extra trace time. The
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
mechanisms, but its five failed protocols leave recovery and adoption unresolved.
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
