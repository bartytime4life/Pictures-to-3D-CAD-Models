# Workbench change log

This is a source-change summary, not a list of published releases. The companion
library maintains its own [revision history](../reference-library/CHANGELOG.md).

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
