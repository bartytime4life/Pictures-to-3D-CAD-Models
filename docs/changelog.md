# Workbench change log

## Contact shadows beside an edge — November 13, 2026

- Documents why a shadow deepest at the part's edge moves edges outward under a
  wide blur. The paper beyond the fit's start cannot show the shadow within about
  1.5–2.5 blur widths of the edge, and the edge profile's shape tells it apart only
  with the blur's width known to well under 1 %. The capture guide now says to
  focus sharply and to light from well above
  ([reference-sheet tracing](reference-sheet.md), §3).

## Completed active-face study and rounding diagnosis documented — November 13, 2026

- Preserve the first expectation failure and record the separately frozen
  corrected selected result: 821 tests and 33 subtests pass at `c1a9330`.
- Record the complete original 24-case recovery study: 11/12 matched passes,
  exit 1, with the middle-PNG miss, exception and adverse pass retained.
- Explain the independently verified rational optimum and the saved-only
  physical census at `b649ea3`: 49 controls pass; all 128 adjacent candidates
  fail source-membership gates, with no arithmetic unknowns. Inward-point work
  remains prospective. [Results and evidence](validation/finite-acquisition-physical-rounding.md).
- Refresh active guidance and source/CI status after PR #116 merged; complete
  the beginner startup path and clarify report-output behavior. Preserve all
  runtime and dated evidence. [Documentation review](validation/documentation-physical-rounding.md).

## Independent colour noise in the test renderer — November 13, 2026

- The test renderer drew one noise image for all three colour channels, which kept
  them in exact proportion; JPEG's colour conversion then rounded their small
  differences alike at every edge and shifted rendered edges 0.02–0.03 px towards
  the paper under a 3.9 px blur. Each channel now has its own noise, a one-level
  dither and rounding. That had partly hidden the tracer's own start bias: summed
  over the documented tables the errors rise from 1480 to 1851 µm, mostly on
  noise-free wide blurs, while shadowed photos improve (the 47 % shadow 25 → 15 µm).
  Three regression limits were re-set between their new and planted-fault figures
  ([reference-sheet tracing](reference-sheet.md), §3).

## Exact active-face first controls documented — November 13, 2026

- Record the additive local implementation at `1dade8a`: 820 passes, one failed
  test expectation and 33 passing subtests, exit 1; full recovery study unrun.
- Explain exact local-QP certificates, represented feasibility and literal-cost
  acceptance separately. Preserve the test's 15-versus-16-row discrepancy and
  the unadmitted correction, without claiming a passing rerun.
- Add six verbatim first-execution records and update active navigation and
  source/CI status after PR #115 merged. Preserve runtime, historical records,
  prior targets and all 96 frozen inputs. [Review scope](validation/documentation-protected-active.md).

## First protected-source-bin controls documented — November 13, 2026

- Record eight failed first software controls, 752 passes and 33 passing
  subtests at frozen source `79522b5`; the protected full recovery study is unrun.
- Add the local projection design, failure record and six verbatim evidence
  copies, preserving all preceding cases, targets, failures and input hashes.
- Refresh active workbench/library navigation and main/CI status after PRs #113
  and #114 merged; document shadow-free blur eligibility and its thickness limit. [Review scope](validation/documentation-protected-controls.md).

## The blur beside a soft shadow — November 13, 2026

- A soft shadow beside a part no longer reads as edge blur. Its light still rises
  where each profile's width is read, so a 3 px blur measured 4.17 px beside the
  test photos' 25 % shadow. Where the fitted shadow takes at least 3 % of the
  light, its own light is now taken out of every profile before the width is read
  (3.90 px; 3.88 px without the shadow). Over six noise seeds the 1 × 3 px photo's
  summed error fell from 73 to 45 µm and the two-light photo's from 118 to 66 µm;
  shadow-free and thick-plate photos are unchanged. A sharp 120 × 70 rectangle
  under a shadow got worse (to 0.09 mm), a corner arc too short to measure
  standing proud ([reference-sheet tracing](reference-sheet.md), §3).
- Re-centring the second edge pass was measured and not adopted: on exact images
  it removes a start bias of up to 0.05 px, but on rendered photos that bias was
  offsetting JPEG's shift of the edge and the shadow model's remaining push.

## Completed local recovery research documentation — November 13, 2026

- Record coupled 11/12 and source-event 11/12 results, both complete protocols
  failed, with all original cases, thresholds and first outcomes retained.
- Document source-code event scoring, actual-cost acceptance, work accounting
  and the unresolved middle-PNG case.
- Record the historical paired audit's 28 unknowns, the coupled audit's first
  17 framing failures and its separately frozen saved-only correction.
- Refresh main/CI status after PR #112 merged and connect current guidance
  across workbench, developer and companion-library documentation.
  [Review scope](validation/documentation-executed-recovery.md).

## Documentation of unexecuted coupled research — November 13, 2026

- Refresh main/CI status after PR #111 merged; retain its results on their own head.
- Document source-stage encoding, seven simultaneous geometry/brightness
  proposals, strict literal-cost acceptance and shared resource caps.
- Distinguish verified local archive packaging from an unexecuted paired audit,
  including the expected missing-precision records and explicit exclusions.
- Add authoring/admission hashes and navigation across workbench and library
  guides; preserve historical evidence, source, frozen studies and generated products.
  [Review scope](validation/documentation-coupled-state.md).

## Documentation of separate local recovery research — November 13, 2026

- Audit current documentation against main `e0b16e0`, after PR #110 merged.
- Connect the local five-geometry/unknown-brightness research snapshot to the
  index, architecture, engineering, development and roadmap guides while keeping
  its APIs outside the merged runtime and workbench interface.
- Retain the original 4/12 and continuation 9/12 matched results, both failed
  protocols, 459 focused test passes, three remaining PNG failures and the
  first saved-data audit's 14 unreconstructible pre-cast area deltas.
- Include verbatim report/log/plan extracts and source bindings; preserve
  historical records, runtime source, frozen studies and generated library products.

## Documentation audit after the merged refresh — November 13, 2026

- Audit the full documentation inventory against main `a6990c9`, including
  merged PR #109, and update head-specific hosted-check states.
- Put available capabilities and remaining integration work before historical
  source snapshots; keep earlier results, frozen studies and library releases
  tied to their original revisions.
- Correct the handbook's diagonal-fit guidance and regenerate its reader/PDF;
  describe the corner optimizer's actual stopping and cost allowance, and make
  both local-model report overwrite paths explicit. Warn before the historical
  continuation command whose source-equality check fails on current main.
- Link the [current review](validation/documentation-main109-state.md) from the
  README, documentation index and contributor guidance.

## Documentation aligned with current main — November 13, 2026

- Put installation and the first workflow ahead of detailed research in the
  README; update the source snapshot to include merged PRs #105, #107 and #108.
- Explain per-direction edge widths without a fitted covariance throughout
  capture, architecture, corner/frame and troubleshooting guidance.
- Complete the sensitivity API signatures, array shapes and resource contract;
  add a small no-fit example and separate implemented derivatives from planned
  recovery with unknown brightness. Correct a stale prospective-check statement
  while preserving the completed failed study.
- Review workbench and companion-library documentation, fix the library's
  setup prerequisite, and preserve historical reports and generated outputs.
  [Review and verification](validation/documentation-cell-state.md).

## Unrounded source-cell sensitivities — November 13, 2026

- Add five disk/chord area derivatives with exact event predicates, bounded
  high-precision moments and explicit contact/endpoint/work unknowns.
- Add a separate fixed float64 acquisition operator for six signed fields plus
  a charged constant response, preserving raw kernel sums and border semantics.
- Freeze and retain the first 33-row study, 259 focused tests and saved-only
  audits. Preserve the plan's overbroad reference wording and missing complement
  reference-array limitation explicitly. [Method](finite-cell-sensitivity.md)
  · [qualification](validation/finite-cell-sensitivity.md). No inverse recovery
  or automatic adoption is added.

## Source-cell documentation alignment — November 13, 2026

- Align the source snapshot and navigation with draft PR #105 while preserving
  preceding status/CI snapshots and every original scientific outcome.
- Document actual API limits, exceptions, ordered results, hash inputs and
  shape-aware workspace accounting; add a small executable coordinate example.
- Distinguish ideal linear brightness algebra from rounded stages, update the
  remaining inverse requirements and restore the narrow-wall bound's stated
  wall-share condition. [Documentation checks](validation/documentation-mean-state.md)
  remain separate from software, camera and physical qualification.

## Experimental source-cell acquisition mean — November 13, 2026

- Add independent analytic disk/chord cell coverage and explicit finite-kernel,
  grayscale-encoding and signed-Keys stages. Preserve supplied coefficients,
  pixel frames, immutable outputs, work refusals and input hashes. No automatic
  tracing or inverse-fit adoption is added.
- Retain all 128 forward comparisons and their complete arrays. Maximum analytic
  query differences are `7.6294e-5` unquantized and `3.0518e-5` encoded levels.
  Keep the original failed controls, root-precision admission, arithmetic audit
  distinction and separately qualified workspace-accounting repair.
- Record 1,173 full-suite tests at numerical source and 145 focused tests after
  the metadata-only repair, with complete saved-data audits.
  [Method](finite-acquisition-mean.md) · [evidence](validation/finite-acquisition-mean.md)
  · [archive](../studies/fixtures/finite-acquisition-mean-v1/README.md).

## Two-way parts under a directional blur — November 13, 2026

- A part whose edges face two ways, such as a sharp-cornered rectangle, cannot have
  its blur fitted as a covariance; each edge is now searched with its own
  direction's measured width where the directions differ, and the soft-shadow model
  is blurred to match. Under a 3 × 1 px shaken-camera blur such rectangles read
  0.28–0.55 mm off, three of them kept as traced outlines; every rectangle case that
  changed now reads 0.002–0.020 mm. Nothing else changed
  ([reference-sheet tracing](reference-sheet.md), §3).

## Acquisition evidence and documentation refresh — November 13, 2026

- Retain 16 synthetic source scenes, 32 paired output-scale records and all 128
  forward comparisons. Second-moment Gaussian matching leaves 9 unquantized and
  16 PNG cells incompatible, with one PNG inconclusive; no geometry is fitted.
- Preserve the original bootstrap failure and continuation's 320 raw scalar
  markers. Add hash-bound saved normalization, independent audits and the full
  123-artifact package, including the 87-file recorded source snapshot.
- Publish the evidence on main `68a67e7`, preserving its newer soft-shadow
  implementation. Refresh source status, developer instructions, architecture,
  engineering limits, research, roadmap and navigation; check the complete
  documentation inventory. Dated records and generated library outputs retain
  their original scope. [Method](finite-acquisition-operator.md) ·
  [evidence](validation/finite-acquisition-operator.md) ·
  [saved review](../studies/fixtures/finite-acquisition-operator-v1/README.md).

## Experimental finite-chord normal derivative — November 12, 2026

- Add a signed source-angle sensitivity with affine/projective Gaussian first
  moments and guarded original-chord quadrature. Preserve the existing mean
  and four-column shape Jacobian schemas and automatic tracing behavior.
- Freeze and retain all 337 scenes/3,886 queries. The complete protocol exits 1
  with one panel-budget unknown; a compressed-map error-estimation limitation
  also remains. Keep all raw arrays and independent audits losslessly.
- Record 94 focused checks, the build and 1,037 Python tests separately from
  the scientific result. [Contract](finite-normal-derivative.md) ·
  [complete evidence and limits](validation/finite-normal-derivative.md).

## Documentation alignment with published PR #95 — November 12, 2026

- Refresh the source, dependency and hosted-CI snapshot after publication of
  the complete residual-information study. Preserve its failed normal control,
  unknowns, original target flags and independently audited saved results.
- Document the finite-chord normal derivative's affine/projective derivation,
  sign, units and whole-shape chart assumptions. Numerical qualification and
  integration remain pending; no available operator or accuracy result is added.
- Review the complete workbench and companion-library documentation, update
  entry points and retain historical evidence and generated-library outputs.
  [Coverage and verification](validation/documentation-pr95-state.md).

## Residual information and rotation sensitivity — November 12, 2026

- Retain the complete failed normal-angle protocol, all 12 records, unchanged
  old flags and fixed-normal conditional steps. Add guarded raw-rank/status
  handling and a portable independent saved-data auditor.
- Derive a rotation-sensitivity identity and preserve a separately labeled
  post-hoc saved-array analysis, with no new model call or normal qualification.
- Archive every array losslessly, update method/command/evidence navigation,
  and keep production tracing unchanged.
  [Complete results and limits](validation/finite-residual-information.md).

## Documentation alignment with draft PR #93 — November 12, 2026

- Identify the published affine candidate, exact tree, dependency base and
  timestamped hosted-CI state. Keep completed source-bound results separate
  from later documentation checks and unmerged publication.
- Document the proposed residual-information method, its estimated numerical
  guards and acquisition-data requirements. Explicitly distinguish the proposal
  from available commands, archived-data results and physical PSF calibration.
- Update navigation, research, roadmap and contributor guidance; check the full
  documentation inventory, examples and command help. No executable, study,
  saved result or generated-library bytes change.
  [Coverage and verification](validation/documentation-pr93-state.md).

## Affine finite-material evaluation and documentation — November 12, 2026

- Shared transformed curve panels accelerate exactly affine finite-material
  means, with the existing scalar path for perspective and unsupported batches.
  Work includes discarded evaluations; workspace has an explicit bound. The
  existing circular-segment result schema and optical model are preserved.
- The fixed comparison passes 28 numerical/resource controls, preserves all
  36 archived rows and previous target passes, and records 10.13× faster means
  and 3.84× faster complete fits. The three fit medians are 2.75–3.91 seconds;
  interactive latency and physical accuracy remain unqualified.
- The integrated candidate passes 943 local Python tests, production build
  and lint. Updated current guides, source/CI snapshots, runnable study modes,
  evidence navigation and the engineering limits. Dated reports and companion
  library generated outputs retain their original scope.
  [Algorithm](finite-affine-evaluation.md) · [complete evidence](validation/finite-affine-batch.md)
  · [documentation checks](validation/documentation-affine-state.md).

This is a source-change summary, not a list of published releases. The companion
library maintains its own [revision history](../reference-library/CHANGELOG.md).

## The paper's light as a fitted shadow — November 13, 2026

- A soft shadow is fitted once from the paper all round the part, as the footprint
  convolved with a kernel of no fixed shape (`backend/shadow.py`), and each edge's
  level follows its curve, with the per-profile line kept as a residual. Under a
  3 px blur the slot went from 0.024 to 0.006 mm; a contact shadow is corrected in
  part, and a sharp-edged shadow is left to the line. The trace says which.
- The test renderer takes other shapes of shadow (`shadow_kernel`).

## Documentation alignment with published PR #91 — November 12, 2026

- Updated current source, dependency, main and hosted-CI snapshots. The latest
  [documentation review](validation/documentation-pr91-state.md) covers all
  Markdown, with executable coordinate/preparation examples and command help.
- Linked the 899-test software record and complete paired replay without
  replacing older test totals, scientific misses or upstream refusals. Added
  an archived-data preparation example and clarified the remaining latency,
  optical-model and automatic-export requirements.
- Based the final documentation on integrated main `ec41b0c` after PRs #90
  and #91 merged, including PR #85's separate shadow-harmonic change. Every
  non-Markdown byte matches that main revision. Separate unfinished performance
  work is excluded from this documentation change.

## Measured-ring observation preparation — November 12, 2026

- Added a data-only circular-segment preparation operator using the measured
  ring, fixed padding, explicit crop/global mapping, observed-only seed and
  fixed disjoint 40/16 samples. Both supplied covariance hypotheses can use the
  same observations and bounds; no fit or CAD promotion happens in preparation.
- Preserved original crop/selected-value dtype and bytes with immutable stored
  descriptors and fresh read-only views. Added typed input, crop, contrast,
  resource and numerical refusals, with 37 focused regression cases.
- Added a prospectively frozen paired replay of the original captured fields,
  preserving all version 1 results and upstream failures. Strict JSON failures
  keep their stage and safe provenance without leaving stale pass flags.
  [Contract](finite-shape-inverse.md#prepare-a-measured-ring-observation-set)
  · [source-bound evidence](validation/finite-photo-intensity-v2.md).

## Documentation alignment with published PR #88 — November 12, 2026

- Updated current source identity, dependency and hosted-run snapshots, and
  routed the README, documentation index and validation overview to the
  [complete documentation review](validation/documentation-pr88-state.md).
- Reconciled architecture, setup, engineering and research guides with the
  finite-material Python operators while preserving their research scope.
  Documented coordinate mapping, result flags, work limits, study exit codes,
  supplemental audit and provenance-only archives.
- Clarified unknown thickness and missing covariance, and recorded requirements
  before automatic trace/export adoption. Executable code, studies, historical
  evidence and generated library outputs are unchanged.

## Finite-material intensity inverse and moment study — November 12, 2026

- Added a conditional developer inverse for unknown circular-segment centre,
  radius and chord fraction with two bounded brightness levels. A supplied
  homography, chord normal, covariance, observation set and residual metric
  retain explicit numerical and model limits; automatic tracing is unchanged.
- Boundary-shape derivatives and the complete fixed-face variable-projection
  Jacobian keep optimization separate from geometric mean-information rank.
  Direct local curves preserve requested geometry at large coordinates; rank,
  transform snapshots, numerical failures and work limits have regressions.
- The independent 24-case study retains all matched and adverse outcomes,
  including its failed planned aperture-order comparison. The separate portable
  moment study retains background sensitivity, a missed nominal target and
  incompatible covariance proposals. Added small-part reference-sheet guidance.
  [Model](finite-shape-inverse.md) · [inverse evidence](validation/finite-free-centre.md)
  · [moment evidence](validation/finite-moment-photo.md).

## Documentation publication and navigation — November 12, 2026

- Identified published draft PR #86 and its dependency on draft PR #84 in the
  source-scope guide. Linked the latest complete documentation review from the
  README, documentation index and validation overview.
- Kept the unknown-centre finite-material prototype and its unreviewed plan
  separate from available software and the completed conditional study.
  Runtime, generated library files and previous evidence remain unchanged;
  [coverage and checks](validation/documentation-pr86-state.md).

## Circle-consistent final arc joins — November 12, 2026

- Final fitted arcs now preserve their stored center and radius. Line/circle
  roots are selected as an ordered cycle with source-endpoint evidence, rather
  than joining line feet to a radius-dependent midpoint that can define another
  circle. Minor, half and major arc/chord profiles can reach analytic assembly.
- Unavailable or ambiguous joins retain only the affected traced boundary and
  explain the reason; invalid unsupported profiles remain refused. Radius,
  equalization and snapping notes describe accepted final fitted geometry.
  Initial eligibility and bounded line-only source recovery remain separate.
- Local circle reconstruction avoids squared world-coordinate cancellation;
  moved fillet/cap centers carry their angular witnesses. Direct unit-normal
  solving preserves prescribed contacts. Source-derived rigid display alignment
  remains available when a ring is retained as lines, without claiming snapping.
- Covariance-corner optimization now checks its existing unhalved projected-step
  criterion before requiring more descent, retaining the current iterate when
  resolved. A large proposal shortened by backtracking cannot establish
  convergence; non-finite and unresolved arithmetic remain refused.
- Reused the reviewed canonical geometry implementation on this main-based
  source while preserving covariance and thickness-frame behavior. Separate
  prospective directional free-arc comparisons retain conditioning, finite
  material and threshold counterexamples. No disk forward fit or new blur series
  is automatically applied to photographs.
  [Guide](curved-joins.md) · [evidence](validation/directional-free-arcs.md).

## Blur transport through known thickness scales — November 12, 2026

- Uniform top-face maps now transport standard deviations by `k` and supplied
  covariance by `k²` for free-radius corrections, scalar corners and slot caps.
  Line-refit exclusion windows use their point-bound scale context. Free arcs
  use their own inclusive support, including spans that wrap around the ring.
- Mixed free curves and caps retain an explicitly warned approximation. Mixed
  scalar corners keep the legacy geometry with infinite internal radius
  uncertainty and no sharp-corner bound or deletion; unusable zero/nonfinite
  model radii retain a positive initial geometric arc without another correction.
  Mixed supplied-covariance nonparallel corners keep their existing refusal.
- Added a predeclared independent 46-row frame experiment and retained finite
  approximation biases separately. A topology-cleanup probe passed a source
  distance check but failed the original fixture size limit and was rejected.
  No cleanup operator or acceptance-threshold change was added.
  [Mathematics](blur-frames.md) · [evidence](validation/curve-blur-frames.md).

## Covariance-aware nonparallel corners — November 12, 2026

- Supported nonparallel fillets use the empirical rectified Gaussian covariance
  directly, transforming the corner geometry during Gaussian standardization
  instead of replacing directional blur by one scalar width.
- Uniform thickness-map scales transform covariance in squared units. Mixed
  support maps or unresolved covariance fits normally retain the affected traced
  boundary, without accepting a scalar fallback. An invalid corrected ring may
  instead retain a frozen supported initial geometric fit as a line-only polygon,
  with validity, point-cap and bidirectional whole-boundary checks within the
  existing fitting tolerance. Otherwise profile refusal remains. Notices
  distinguish this nearby polygon and its undetermined radius. No generic
  topology-repair operator, component deletion or polyline-detail tolerance
  increase is introduced; intended source topology remains unqualified.
- Numerical convergence and sharp-resolution searches have explicit refusal
  paths. The common 5% blur-scale sensitivity remains a heuristic; general free
  arcs and slot end caps retain their separate approximations. The
  [model guide](anisotropic-corners.md) records the source-bound 16-case
  conditional study, including its unresolved and sharp-classified cases;
  it does not qualify physical camera accuracy.

## Main-line documentation scope — November 12, 2026

- Added a [source-scope guide](project-status.md) separating main's PRs #76/#77,
  the draft #78 rank repair and research draft #79 on another lineage.
- Clarified rectified directional widths, scalar nonparallel fillet fitting and
  conditional radius-model limits. Added the current developer-command inventory
  and output behavior, and aligned current navigation and evidence summaries.
- Reviewed the Markdown set while preserving dated evidence, library-generated
  assets and all executable bytes; [checks and scope](validation/documentation-main77-state.md).

## Directional-blur design rank — November 12, 2026

- Covariance fitting now rejects a numerical rank below three at every weighted
  least-squares solve. Opposite normals at a rounded angular-bin boundary could
  previously count as separate supported directions and produce an unidentified
  positive-definite covariance. Bin support and model-adequacy thresholds remain
  unchanged. Actual sampled Gaussian-step regressions and the bounded scope are
  recorded in [directional-blur rank validation](validation/directional-blur-rank.md).


## A shadow's push on a hole's centre — November 12, 2026

- The shadow correction's first harmonic round each ring is kept where it is
  significant, by a jackknife over eight sectors, and only the rest is smoothed.
  Smoothing had given each 6 mm hole its mean correction alone, so a soft shadow
  moved its centre: under a 3 px blur hole positions went from 0.027 to 0.009 mm,
  and under a 1 × 3 px blur with noise and JPEG from 0.021 to 0.007 mm
  ([reference-sheet tracing](reference-sheet.md), §3). The slot and outline
  under such shadows are not corrected.

## Slot end caps and directional blur — November 12, 2026

- Slot end caps are placed along the slot with their radius fixed at half the
  side spacing. A free circle fit coupled the cap's place with its radius, and
  the 24 × 8 slot read 0.018–0.022 mm long on thick-part photos at 5° and 9°.
- A blur that differs by direction is measured as a 2 × 2 covariance from the
  edges' widths, with orientation-support and per-direction adequacy rules, and
  traced by direction. Curves are corrected with det(S)^¼, from the blur's
  tangential variance given its normal part. On a 1 × 3 px render Ø6 went from
  0.067 to 0.012 mm. This supersedes the qualification record's "no production
  correction", with the evidence in [reference-sheet tracing](reference-sheet.md).
- The blur is measured in a window widened to 5 σ, and a degenerate fitted arc
  no longer stops a trace.

## Radial inverse and model-mismatch research — November 12, 2026

- Radial inversion stays on the central camera branch, refuses radii without an
  inverse and constrains sheet-fit trials to the measured reference domain.
  Near-fold sensitivity remains; [mathematics and validation](validation/radial-inverse.md).
- Synthetic lens inversion is separately implemented and Decimal-checked. An
  optional test-only higher-order radial term exposes model mismatch; it is not
  a new production correction or a physical camera qualification.
- A frozen [30-case directional-spread study](validation/directional-spread-qualification.md)
  found orientation-imbalanced missed cases and unknowns. No product warning or
  anisotropic geometry correction was added.
- Updated current guides and documentation navigation, retaining historical
  source revisions, test counts, failures and qualification limits.

## Reference-sheet weak-edge recovery — November 12, 2026

Initially based on `main` at `d6a657f93f13b818a8e44e2ace219b2d4598b4ef`, then
integrated with PR #44 at `03f71e0e4095ee873051b71264b45fde83f84891`.

- A missing outer boundary after the first sub-pixel edge pass now raises an
  explicit recoverable error with focus and part-to-sheet contrast guidance.
  Previously an internal `StopIteration` reached the generic sheet-error path;
  the API already returned 422.
- Preserved the contrast and retained-point thresholds, the zero-blur median-level
  fallback, and successful-capture measurement behavior. Added rendered-capture,
  retained-hole and same-client API recovery regressions. See the
  [bounded validation record](validation/contrast-recovery.md).

## Documentation review — November 12, 2026

Reviewed the full workbench and companion-library documentation against `main`
at `eec45d0`, then integrated PR #43 at `d6a657f` and the initial-fit support
candidate below. Updated current guides
for narrow-wall refinement, hole-derived camera height, source-support checks
and their remaining assumptions. The [review record](validation/documentation-review-2026-11-12.md)
lists coverage and completed checks. Historical validation and catalog snapshots
retain their original revisions and dates.

## Benchmark correspondence and coverage — November 12, 2026

Merged in PR #43. Matching now maximizes admitted feature count before minimizing
total size error, with deterministic traversal and explicit work bounds. Reports
account for requested, compared, unmatched and unavailable dimensions, including
failed photos. Error percentiles remain conditional on comparisons; optimal size
matching does not identify equal-size physical features. [Guide](photo-benchmark.md)
and [separate validation record](validation/benchmark-correspondence.md).

## Initial-fit support — November 11–12, 2026

- Whole-circle candidates require an enclosed center, and assembled initial
  boundaries must stay within a source-support tube with bounded curve sampling.
- Complete classified contours and retained point indices supply coverage when
  subpixel profiles are rejected. Coarse/fine displacement is measured separately
  from candidate residual; coarse points do not enter the precision fit.
- Unsupported fits retain the traced outline. Gaussian reconstruction and design
  snapping retain their separate assumptions. [Method and evidence](validation/fit-support.md).

## Constrained fillet sweeps — November 12, 2026

Moving a fitted fillet's center/radius now carries its angular witness with it,
preventing accidental quarter-circle to 270° sector changes. Genuine major arcs
remain supported. The scalar Gaussian model and radius warnings retain their
separate limits. [Reproduction and checks](validation/fillet-sweep.md).

## Camera height and narrow-wall refinement — November 11, 2026

Merged in PRs #41 and #42; these changes precede the support candidate above.

- Cubic sampling is used consistently for blur measurement and wall profiles.
  Narrow wall bands can share an estimated tone when the fit is identifiable;
  flat or boundary minima retain the earlier bound and a note.
- Suitable off-center holes assumed round can constrain camera height when a
  frontal sheet alone cannot. Wall refinement is repeated with that estimate;
  without suitable holes the assumed-lens limit remains.
- With an unmeasured blur, wall refinement leaves points as traced instead of
  dividing by zero. [Method](reference-sheet.md) and [revision-bound checks](validation.md).

## Scientific documentation follow-up — November 11, 2026

Reviewed `main` at `5588a523c70e1797341329e54d056c161d0361ad`, after PR #39.
This follow-up changes documentation only.

- Documented the median-level fallback when blur cannot be estimated. A zero
  estimate does not establish a sharp edge.
- Added a [scientific model review](validation/scientific-model-review.md) with
  reproduced whole-circle extrapolation, directional-blur model mismatch and
  benchmark correspondence/coverage limits. Proposed fixes remain future work.
- Corrected benchmark interpretation: percentiles are conditional on matches;
  failed photos omit dimension opportunities; pooled spread, the highlighting
  threshold and fitted scale/edge terms do not establish physical uncertainty.
- Updated capture, troubleshooting, engineering, research, contribution and
  roadmap guidance; retained historical results at their original revisions.

## Documentation refresh — November 11, 2026

Initially based on `main` at `76f03fce60c2a9193501e73f3e4d4ad85bbcf554`, then
integrated with PR #37 at `567b5bdd36cbc2ab6b666b9514c84e7764a07445`.

- Added a [documentation index](README.md) and [contributor guide](contributing.md).
- Aligned current guides with recipe versions, preview/export guidance,
  reference-sheet and polygon behavior, conservative printer placement, explicit
  AI actions and measurement-note persistence.
- Clarified setup, generated-library maintenance, historical validation records
  and the distinction between the two components' storage and input limits.

## Recent workbench improvements — November 11, 2026

These features are present in the documentation baseline above. See the linked
records for their checks and limitations.

- A shared next-step guide, workflow navigation and footer distinguish missing
  measurements, invalid settings, outdated geometry and current CAD. Preview
  updates stay beside the source; export choices separate common geometry from
  drawings and source files. Recipe errors focus their correction fields.
  [Interface audit](validation/guided-workbench.md).
- Feature-reference drafts retain precision across unit changes. A narrow
  numerical guard handles supported-width boundary roundoff. Advice-only AI
  replies become visibly outdated after edits; oversized designs can request
  explicitly reviewed repairs. [Guided-workbench validation](validation/guided-workbench.md).
- Independent height checks support optional entered bounds and allowances with
  within/outside/inconclusive decisions. [Engineering audit](validation/engineering-audit.md).
- Continuous-angle printer placement, bounded split suggestions and conservative
  fitted-curve enclosures keep their placement witnesses separate from exported
  orientation. [Placement](research.md), [split validation](validation/split-plans.md),
  [curved-placement validation](validation/curved-placement.md).
- Reference-sheet tracing estimates camera corrections and fits lines, arcs and
  circles where supported. Synthetic edge and fillet-fit improvements retain
  explicit limitations; a measured-photo benchmark runner is available.
  [Tracing method](reference-sheet.md), [validation history](validation.md),
  [benchmark guide](photo-benchmark.md).
- The second edge pass follows a locally linear paper-side shadow slope and
  smooths its correction around the ring. The latest upstream synthetic tables
  preserve both improvements and the near-frontal cases that got worse.
  [Method and limits](reference-sheet.md), [validation](validation.md).

These records do not establish a released package, native slicer acceptance,
live-model quality or physical fit. Earlier changes remain traceable through Git
history and the dated [validation records](validation.md).
