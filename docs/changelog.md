# Workbench change log

This is a source-change summary, not a list of published releases. The companion
library maintains its own [revision history](../reference-library/CHANGELOG.md).


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
