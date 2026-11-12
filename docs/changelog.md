# Workbench change log

This is a source-change summary, not a list of published releases. The companion
library maintains its own [revision history](../reference-library/CHANGELOG.md).

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
