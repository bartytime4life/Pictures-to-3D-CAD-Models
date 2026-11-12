# Main-line documentation and source scope — November 12, 2026

This Markdown-only review starts at `185d682197437581083a8ecd46de6357d7adb846`,
the head of draft PR #78, based exactly on main
`f1679bb50ca39e1764897e00124eccdf41b21f59` after PRs #76/#77.
It targets that rank-repair branch; it does not reintroduce the patch into main
or import code/documentation from the separate PR #79 research lineage.
See [source scope](../project-status.md) for the branch and capability map.

## Corrections and source evidence

- Added explicit main/draft/research boundaries and command availability. The
  reviewed main-based `backend/` has no source-context or source-space Gaussian
  calibration API. PR #79 targets `codex/source-observation-context`, not main.
- Separated rectified `sigma_n` widths in `edges.subpixel_rings`,
  `sheet.half_level_search` and `reference._refine_walls` from the scalar width
  passed to nonparallel `fitting.fit_fillets`/`_exact_fillet`/`corner_level`.
  Only slot-end axial fitting also takes the covariance. This clarifies existing
  model assumptions, not a newly executed anisotropic-corner failure study.
- Clarified that profiles are in pixels while constructed CAD uses millimetres;
  documented the existing `/api/printers` route.
- Documented the actual main-line CLI set, output overwrites and commands without
  argparse help. Updated manual build-first verification guidance while preserving
  the actual test script's Python/build/browser order and the 30-minute CI budget.
- Updated current evidence/navigation that still described the earlier absence
  of a production anisotropic path. Dated scientific, library and validation
  records retain their original results and qualification limits.

## Checks performed for this text update

The existing library documentation-accuracy suite passes **19 tests**. Thirteen
read-only command checks pass: five actual Python argparse help paths, six shell
syntax checks, `make help` and the no-argument Ollama helper's usage output.
Source-AST and generated OpenAPI maps agree on
all **11 `/api/` operations**; the architecture's documented operation list
matches them too. The other three schema operations are static
reader/frontend routes. No API request, server, native application, model
inference, download, camera study or full product regression was executed.
The initial API-map harness included the static route converters; correcting
its `/api/` filter required no product-code or API change.

The local navigation check passes for **59 Markdown files, 562 local references,
43 heading fragments and 84 tables**, including one local HTML image reference.
All **269 tracked non-Markdown files** remain byte-identical to `185d682`, as do
the 16 pre-existing dated validation records and all companion-library files.
Diff whitespace checks pass. The checks cover local references, heading
fragments, fences and table structure; they do not refresh external catalog URLs
or re-review every linked paper. The library's generated HTML/PDF, catalog data
and native examples are unchanged, so this pass does not regenerate or re-release
them.

## Revision-bound checks that were not rerun here

The rank repair's **633 Python tests** and **76 focused checks** remain the
[earlier candidate run](directional-blur-rank.md), not tests of new product code
in this documentation pass. Its build/269-file freeze and historical PR #77
browser results keep their separate bindings. No PR #79 test count is attributed
to main. Synthetic results and valid digital geometry do not establish real-phone
accuracy, metrological conformance, native slicer acceptance or physical fit.

At **2026-11-12 19:16:12 UTC**, the GitHub API reports both PRs #78/#79 as open
drafts. [PR #78 workbench run 144](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43285958681)
is in progress with no conclusion; this is not a hosted pass. That timestamped
snapshot does not predict the eventual result or constitute deployment evidence.

## Complete Markdown coverage

The baseline contains 56 Markdown documents; this review adds three. Every file
is included in the navigation/source-scope inventory below. Unchanged dated
records and generated library directories retain their original bytes.

| File | Review scope |
| --- | --- |
| `README.md` | Current guide aligned with main-based source and separate research scope |
| `data/PRINTER_SOURCES.md` | Current guide/data record reviewed; no source-based correction required |
| `design-qa.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/README.md` | Current guide aligned with main-based source and separate research scope |
| `docs/architecture.md` | Current guide aligned with main-based source and separate research scope |
| `docs/capture-guide.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/changelog.md` | Current guide aligned with main-based source and separate research scope |
| `docs/contributing.md` | Current guide aligned with main-based source and separate research scope |
| `docs/developer-tools.md` | Current guide aligned with main-based source and separate research scope |
| `docs/development.md` | Current guide aligned with main-based source and separate research scope |
| `docs/engineering-model.md` | Current guide aligned with main-based source and separate research scope |
| `docs/exports.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/ollama-models.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/ollama.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/photo-benchmark.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/print-planning.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/printer-catalog.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/privacy-security.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/project-status.md` | Current guide aligned with main-based source and separate research scope |
| `docs/reference-sensitivity.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/reference-sheet.md` | Current guide aligned with main-based source and separate research scope |
| `docs/research.md` | Current guide aligned with main-based source and separate research scope |
| `docs/roadmap.md` | Current guide aligned with main-based source and separate research scope |
| `docs/slicers.md` | Current guide/data record reviewed; no source-based correction required |
| `docs/troubleshooting.md` | Current guide aligned with main-based source and separate research scope |
| `docs/validation.md` | Current guide aligned with main-based source and separate research scope |
| `docs/validation/benchmark-correspondence.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/contrast-recovery.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/curved-placement.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/directional-blur-rank.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/directional-spread-qualification.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/documentation-main77-state.md` | This review and complete coverage inventory |
| `docs/validation/documentation-refresh.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/documentation-review-2026-11-12.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/engineering-audit.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/fillet-sweep.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/fit-support.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/guided-workbench.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/project-import-recovery.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/radial-inverse.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/reference-sensitivity.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/scientific-model-review.md` | Dated source-bound record; retained without rewriting its results |
| `docs/validation/split-plans.md` | Dated source-bound record; retained without rewriting its results |
| `reference-library/BUILD.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/CHANGELOG.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/CONTRIBUTING.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/GITHUB.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/HANDBOOK.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/OPENSCAD.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/README.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/REFERENCES.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/RESEARCH-NOTES.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/VERIFICATION.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/cadkit/README.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/examples/README.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/templates/CAPTURE-CHECKLIST.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/templates/INDEPENDENT-CHECKS.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/templates/PRINT-ACCEPTANCE.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
| `reference-library/templates/PROJECT-BRIEF.md` | Companion/library or generated snapshot; source/data, navigation and existing documentation checks; unchanged |
