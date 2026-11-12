# Workbench change log

This is a source-change summary, not a list of published releases. The companion
library maintains its own [revision history](../reference-library/CHANGELOG.md).

## Conditional common-response calibration — November 12, 2026

- Add exact rational consistency of one nondecreasing scalar function, supplied
  output/slope bounds, tight knot/query bands and a shared piecewise-linear witness.
- Preserve duplicate constraints and exact source-indexed contradictions; refuse
  invalid inputs and bounded-resource exhaustion without a mathematical verdict.
- Add a provenance-bound decimal-string CLI, independent graph oracle and complete
  [edge/calibration controls](validation/response-calibration.md). Unknown response
  can preserve edge ambiguity, and incorrect calibration can exclude truth.
- This developer work adds no automatic image correction, inverse, physical
  likelihood, workbench endpoint or accuracy status.

## Documentation review through PR #64 — November 12, 2026

- Bring setup and the sample workflow forward in the README; keep mathematical
  methods and study commands reachable through the task index.
- Update the source/review snapshot through published PR #64. Document raw-source
  API units, diagnostics and limits, including standardized residuals and the
  distinction between brightness rank and edge identifiability.
- Clarify processed-profile versus source-space fitting and known versus
  image-estimated warp parameters. Preserve dated validation and library artifacts.
- Record the [complete documentation audit](validation/documentation-latest.md)
  separately from prior software, hosted, browser and physical evidence.

## Conditional raw-source edge fitting — November 12, 2026

- Fit a declared lens-free Gaussian half-plane in fixed retained source modes,
  profiling bounded brightness levels at each finite offset candidate.
- Keep represented minima, endpoint/flat/tie/rank/work diagnostics and the raw
  residual components omitted by the chosen source projection.
- Add [repeatable controls](validation/raw-source-fit.md) for processing arithmetic,
  source rounding/quantization, wrong optics/response, noise and nonidentification.
  This developer tool changes no production trace, UI or physical accuracy status.

## Documentation alignment through PR #62 — November 12, 2026

- Update the source/review chain and exact-head hosted observations, preserving
  earlier validation counts and incomplete runs under their original bindings.
- Complete the root numerical-command table, correct benchmark coverage and
  current wall-note guidance, and explain covariance conditioning limits.
- Link the [current coverage inventory and checks](validation/documentation-alignment.md)
  from the task index, status, validation overview and contribution guide.
  Executable source, archived results and generated library outputs are unchanged.

## Hosted verification budget — November 12, 2026

- Allow 45 minutes for the complete hosted workbench job after a 30-minute run
  ended following successful Python checks and 58 of 74 serial browser scenarios.
- Retain the source, test set and per-test timeouts. The
  [runtime-budget record](validation/ci-runtime-budget.md) separates partial-run
  timing extrapolation from subsequent exact-head results in the
  [status snapshot](project-status.md#evidence-by-scope).

## Known warp chain and raw optical models — November 12, 2026

- Compose the earlier fixed Keys perspective/radial rectification with smoothing
  and final profile sampling, preserving source sharing, border order, local
  allocation caps and zero functionals.
- Add 324 complete digital readouts, measured float32 stage accounting, 18 raw
  optical fields and a separate radial-curvature quadrature control. Keep exact
  affine behavior, projective approximations and optical/digital assumptions
  distinct in the [method](warp-observations.md) and [record](validation/warp-observations.md).
- This developer extension changes no production trace, frontend or dependencies.

## Fixed observations and conditional covariance — November 12, 2026

- Add a bounded reusable Keys observation matrix, declared finite-filter
  composition with explicit borders, and SVD accounting for shared input-pixel
  noise. Retain support violations and rank/work limits.
- Add repeatable false-precision and known-postblur controls, preserving genuine
  row-space gains, truncation counterexamples, global wall aliases and float32
  model discrepancy. [Method](profile-observations.md) and
  [evidence](validation/profile-observations.md) distinguish this developer work
  from production corrections and physical noise calibration.

## Local wall localization and observation-model development — November 12, 2026

- Expand wall-edge hypotheses and update predicted width with candidate position.
  Use direct SVD refinement, bounded wall brightness, bounded allocations and
  explicit unchanged-point outcomes for unresolved numerical fits.
- Keep observations local to the seed. Preserve the earlier expanded-window
  candidate, its two camera-height failures and the ablations that isolate the
  inappropriate flat-lighting support rather than weakening existing guards.
- Add a complete paired segmentation/subpixel/wall study, versioned unknown
  outcome accounting, CSV audits and matched final-Keys developer controls.
- [Method](wall-localization.md) and [source-bound evidence](validation/wall-localization.md)
  retain adverse outcomes, sampling/lighting limits and physical qualification work.

## Complete documentation update — November 12, 2026

- Refresh the [source/review snapshot](project-status.md) through published
  PR #57 and add a [numerical-tool catalog](developer-tools.md) with versioned
  contracts, repeatable study/audit commands and output-preservation rules.
- Replace unconditional wall-identification and error-cap claims with the
  published search limits and model assumptions. Correct sharp-corner,
  short-feature and linear-channel wording without changing tracing behavior.
- Clarify benchmark report replacement and environment-dependent PDF
  reproducibility. Review the complete Markdown set, retaining historical
  evidence and generated library outputs under their original source bindings.
- The [coverage and verification record](validation/documentation-complete-2026-11-12.md)
  describes this documentation update separately from product regression tests.

## Bounded wall and lighting experiment — November 12, 2026

- Add `make wall-gradient-study OUTPUT=new-folder`, a bounded five-node source
  model, SVD-based box fitting and complete geometry/image CSVs.
- Demonstrate identical local light fields with different silhouette labels,
  finite-error alternatives and lighting bias remaining with a known wall tone.
- Retain all 840 direct fits and 576 image fits, independent source quadrature,
  box-optimality checks and the updated capture/model guidance. The full Python
  suite passed 1,131 tests. [Method](wall-gradients.md) and
  [verification](validation/wall-gradients.md) distinguish constructed midpoint
  observations from original samples, and local evidence from physical accuracy.
- Clarify conditional wall-identifiability documentation without changing
  production executable behavior. The new solver does not automatically alter
  traces, add an accuracy status or qualify physical parts.

## Nearest verified edge crossing — November 12, 2026

- Rank actual interpolated distances instead of bracket-left sample indices.
  A bounded three-crossing fixture previously selected different physical edges
  when its normal was reversed; both directions now choose the nearer crossing.
- Treat nearest unresolved level contacts and distinct equal minima as missing
  measurements. Preserve rejected points and independent resolved profiles.
- Compare competing distances using exact binary-data arithmetic, with scaled
  interpolation that retains tiny roots. This supplies no physical confidence.
- Add 36 independent regressions and a reproducible 3,888-case contact oracle.
  The full suite passed 1,111 Python tests. [Method](edge-crossings.md) and
  [verification](validation/edge-crossings.md) retain the model boundaries and
  the previous profile cohort's preservation check.

## Symmetric edge sampling and material-gradient study — November 12, 2026

- Centre local profile samples on the supplied point with paired integer steps.
  Noninteger windows previously sampled different physical positions when the
  same normal was reversed. Independent regressions reproduce that defect.
- Add `make material-gradient-study OUTPUT=new-folder`, an independent bounded
  light-field oracle, a fixed 576-scene plan and complete before/after summaries.
  All 9,216 rows per run and 768 low-contrast rejections are accounted for.
- Preserve the paper-only slope guard and document retained material-gradient
  bias, wall/edge confounding and multiple-crossing ambiguity. The two-affine
  branch remains an ablation. [Method](material-gradients.md) and
  [evidence](validation/material-gradients.md) record the model boundaries.
- The complete Python suite passed 1,075 tests; physical calibration remains open.

## Signed sampling observations — November 12, 2026

- Version 4 of the developer CLI encloses fixed signed aperture combinations
  over complete radius/blur boxes. Actual Keys examples show why composite
  endpoint values cannot bound a nonmonotone signed response.
- Preserve negative/superunit values, exact gain/L1 metadata, zero operators and
  duplicate cancellation. Raw nonzero terms determine the work cap, with six-file
  provenance and versions 1–3 retained.
- [Method](signed-stencils.md) and [evidence](validation/signed-stencils.md)
  keep calibration assumptions, model-mismatch controls and unknown results
  explicit. Production tracing/API/UI/CAD paths are unchanged.

## Known pixel-aperture observations — November 12, 2026

- Version 3 of the conditional corner CLI integrates known uniform rectangular
  apertures instead of substituting their center samples. Outward antiderivative,
  support and density bounds retain complete continuous means.
- Reused the common radius/blur classification and safe projection engine,
  preserving versions 1/2 and exact two-Dirac point calculations. Reports retain
  the exact aperture input and five implementation hashes.
- Independent pixel-area observations expose radius exclusions under the point
  model and retain matching truth with the aperture model; uncertain-blur and
  numerical limits remain unknown. [Method](pixel-apertures.md) and
  [checks](validation/pixel-apertures.md) distinguish this developer analysis
  from production tracing, camera calibration and physical qualification.

## Documentation consolidation through PR #51 — November 12, 2026

- Updated the [source/review and hosted-CI snapshot](project-status.md) through
  the shared-blur developer analysis, distinguishing open reviews from `main`
  and source-bound Python results from earlier browser/build evidence.
- Routed the task index and validation overview to the [latest documentation
  record](validation/documentation-math-state.md). Retained historical reports,
  their original counts and the companion library's release record.
- Rechecked complete Markdown navigation and consistency with the published
  CLI examples and verification receipts. This consolidation changes documentation.

## Joint corner-radius and blur domains — November 12, 2026

- Version 2 of the developer CLI treats radius and supplied Gaussian blur
  intervals as one joint domain. One blur pair must explain every observation;
  radius projections retain accepted and unknown parameter boxes.
- Rejected nuisance boxes are kept separate from radius exclusions. Added
  density/CDF mass intersections and outward Decimal exponentials to reduce
  interval dependency loss without silently clipping numerical error.
- Shared-blur contradictions and known-truth cases retain compatible,
  incompatible and unknown outcomes. [Input contract](corner-feasibility.md#joint-blur-domains-version-2)
  and [evidence](validation/corner-blur-domains.md) distinguish numerical coverage
  from physical qualification. Version 1 remains supported; tracing/UI are unchanged.

## Conditional corner-radius developer analysis — November 12, 2026

- Added explicit bounded-error radius analysis for a fixed right corner and
  independent axis-aligned Gaussian blur. Outward Decimal probability covers
  enclose whole radius intervals; budget/numerical limits retain unknown regions.
- Added a provenance-bound CLI with exact decimal input, a synthetic demo and
  exclusive output writes. It changes no production tracing or CAD behavior.
- Independent development observations retain known radii under matching models,
  reject the deliberately wrong scalar blur, and expose numerical-resolution
  limits. [Method](corner-feasibility.md) and [validation](validation/corner-feasibility.md)
  retain negative/unknown cases and separate physical qualification.

## Documentation and current-state review — November 12, 2026

- Added a revision-bound [project-status page](project-status.md), endpoint map,
  executable synthetic [API example](api-examples.md) and error-recovery guide.
  Clarified browser URLs, development startup, trace fallback and source pixels
  versus CAD millimeters.
- Restricted interpolation and phase-error claims to their tested fixtures;
  explained that nonlinear radius spread is not calibrated by a local standard
  deviation. Matching source/test docstrings changed without altering behavior.
- Added corner-note recovery, corrected historical interpretation pointers and
  fixed the library's isolated-install and interrupted-release instructions.
  [Coverage and completed checks](validation/documentation-current-state.md)
  are separate from prior full workbench and library release results.

## Corner resolution and search validity — November 12, 2026

- Radius-resolution bisection now requires a finite checked upper crossing.
  Exhausting the existing search range returns unresolved. Both fallback paths
  retain an unresolved-radius note, including the correct corner angle.
- Sharp-corner notes and corner-sweep output describe conditional blur-model
  resolution, replacing the unsupported physical upper-radius claim.
- Added independent Gaussian-wedge regressions, a rounded-corner mismatch
  counterexample and primary research on conditional feasible parameter sets.
  [Method, limits and checks](validation/sharp-corner-resolution.md).

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
