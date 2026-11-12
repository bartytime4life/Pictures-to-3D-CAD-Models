# Documentation refresh — November 11, 2026

Initial baseline: `main` at `76f03fce60c2a9193501e73f3e4d4ad85bbcf554`, after
the guided-workbench PR merged. During review, PR #37 merged; its shadow-level
correction and updated synthetic figures were incorporated from
`567b5bdd36cbc2ab6b666b9514c84e7764a07445`. Changes relative to that final
baseline are documentation only, prepared in an isolated worktree. The original
checkout and existing previews were preserved.

## Coverage

All 43 tracked Markdown documents were included in the inventory and local-link
review. Current user, architecture, engineering, AI and maintenance guides were
compared with their implementation. Historical reports and general library
material were reviewed for scope and consistency; their original observations,
dates, source snapshots and counts were retained. This is not a fresh literature
review or a retest of every historical claim.

| Documents | Review and disposition |
| --- | --- |
| Root README, design QA | Updated current navigation, tracing modes, recovery, exports, recipe versions and evidence dates |
| `docs/capture-guide.md`, `docs/troubleshooting.md` | Aligned next-step actions, correction focus, unit/reference behavior and browser recipe recovery |
| `docs/architecture.md`, `docs/development.md`, `docs/roadmap.md`, `docs/slicers.md` | Updated data flow, recipe contents, all-angle placement, test guidance, scope and handoff instructions |
| `docs/engineering-model.md`, `docs/research.md`, `docs/reference-sheet.md`, `docs/reference-sensitivity.md`, `docs/print-planning.md`, `docs/exports.md` | Clarified camera and numerical assumptions, conditional height decisions, sampling caps, geometric fit and digital evidence |
| `docs/printer-catalog.md`, `data/PRINTER_SOURCES.md` | Checked bundled counts/profile semantics; retained the pinned source and snapshot date |
| `docs/ollama.md`, `docs/ollama-models.md`, `docs/privacy-security.md` | Corrected text-only AI, stale answers, settings recovery, metadata/cleanup and browser-versus-backend data boundaries; dated older preflight claims |
| `docs/photo-benchmark.md` | Reviewed command, schema, revised upstream shadow-correction example and explicit absence of real-photo results; retained the latest upstream numbers |
| `docs/validation.md` | Added revision-bound evidence overview, linked successful PR-head CI and retained historical sections |
| Six existing `docs/validation/*.md` records | Reviewed current guide links and evidence scope; retained original runs and counts |
| `reference-library/README.md`, `reference-library/BUILD.md` | Added repository navigation; corrected generation table and explained fresh-browser-receipt requirements for verification |
| Library handbook, research notes, generated source/GitHub directories | Retained dated catalog, review depths and synthetic formulas; regenerated outputs and ran existing accuracy checks |
| Library contribution/change/verification records, OpenSCAD guide, cadkit guide, examples and four templates | Reviewed command/source relationships, evidence classes, native-build and physical-acceptance boundaries; retained release records |

Added a [documentation index](../README.md), [contributor guide](../contributing.md)
and [workbench change log](../changelog.md). Root legacy `CHANGELOG.md` and
`CONTRIBUTING.md` names are intentionally ignored by this repository, so the new
guides live under `docs/`. Ignored personal studies, local artifacts and private
reference inputs were not edited or published.

## Main corrections

- Browser **Save project** uses version 2 for polygon outlines and version 3 for
  fitted/reference profiles. It preserves optional endpoint/height inputs;
  backend `project.json` and slicer recipes omit those browser-only notes.
- Ordinary endpoint calibration remains a uniform scale. The separate sheet
  pipeline estimates camera corrections under assumptions; generated exact
  curves do not establish physical accuracy. OpenSCAD's 0.005 mm sampling target
  has a 720-segment cap, so it is not an unconditional approximation bound.
- Printer placement searches continuous in-plane rotations. Curve enclosures,
  unknown printer geometry and split proposals retain their conservative limits.
- The guide works without AI. AI is text-only; advice can become outdated during
  a request. Invalid raw fields and valid-but-oversized geometry have different
  recovery paths, and Apply/build remain explicit.
- Documentation commands now reflect source behavior and generated-file inputs.
  Historical test totals, model preflights and release records remain tied to
  their original revisions and environments.

## Validation scope

Only documentation changes relative to the final baseline are included. The
earlier guided workbench's 498 Python and 74 frontend/browser passes are in the
[guided audit](guided-workbench.md), and that exact PR head passed
[hosted CI](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43120297057).
The later shadow correction records 501 Python and 74 browser passes in the
[validation overview](../validation.md). Those suites are not new runs for this
documentation refresh. Its checks cover
local links and anchors, guide/source consistency, the existing library accuracy
tests and generated-output reproduction. External catalog availability, model
artifacts, native slicers, physical prints and assistive technologies were not
requalified.

## Completed documentation checks

- **47 Markdown documents** checked: the 43-document baseline plus this record,
  the index, contributor guide and workbench change log.
- **389 local links** and **21 fragment links** resolve. External websites and
  catalog metadata were not refreshed; their recorded dates remain intact.
- All 47 documents parse with the library's installed `marked` version;
  **67 Markdown tables** have consistent column counts.
- The library's existing `test_docs.py` suite: **19 tests passed**. It checks
  source/record counts, worked numbers, local links, figures, CLI coverage and
  PDF page count.
- `make build-library`: passed. The regenerated HTML, PDF, figures, worked
  numbers, CSV and catalog Markdown are byte-for-byte unchanged from the
  baseline. No generated file or release receipt was edited manually.
- `git diff --check`: passed. The diff from the final baseline contains documentation only;
  backend/frontend code, tests, dependencies, catalog data and release records
  are unchanged.

Local check details are retained in the documentation worktree's ignored
`.local/verification/` directory. Hosted CI for the documentation PR is separate
from the completed source run linked above.
