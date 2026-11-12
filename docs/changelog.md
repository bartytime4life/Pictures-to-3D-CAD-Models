# Workbench change log

This is a source-change summary, not a list of published releases. The companion
library maintains its own [revision history](../reference-library/CHANGELOG.md).

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
