# Documentation review — November 12, 2026

Reviewed the repository documentation against `main` at
`eec45d04cf767f2a55e8581a009b8052fe349180`, including merged narrow-wall and
camera-height changes, then integrated the merged benchmark repair at
`d6a657f93f13b818a8e44e2ace219b2d4598b4ef` and the
[initial-fit support candidate](fit-support.md).
Work used an isolated checkout; the original `codex/slicer-integration` checkout
and existing worktrees were preserved. This review accompanies the source-support
change; documentation and runtime checks are recorded separately below.

## Coverage

The incoming documentation inventory contained 49 Markdown files, including the
new fit-support record. The merged benchmark record and this review bring the
final inventory to **51**. Current guides were
compared with source, commands, UI labels and bundled data. Historical reports,
source snapshots and templates were reviewed for consistency and evidence scope.
Documents that remained accurate were retained without cosmetic rewrites.

| Area | Files reviewed | Disposition |
| --- | ---: | --- |
| Root README and design QA | 2 | Corrected shadow/camera limitations; retained dated screenshots and QA observations |
| Workbench guides under `docs/` | 21 | Checked capture, calibration, engineering, algorithms, API, setup, contribution, export, printing, AI, privacy, recovery, navigation, roadmap, change log and validation |
| Other `docs/validation/` records | 10 | Completed integrated support evidence and reviewed the merged benchmark record; retained earlier baselines, failures and counts; linked current findings separately |
| Printer-source attribution | 1 | Confirmed bundled counts/profile semantics; retained source snapshot and license dates |
| Companion library Markdown | 16 | Reviewed reader/build/native-tool instructions, handbook, research, source/GitHub snapshots, revision/verification records, examples, cadkit and four worksheets; corrected receipt prose and warning-schema scope |

The library's generated reader, PDF, figures, calculations and catalog outputs
were rebuilt from their sources. Original photographs, personal studies, model
weights and private native builds were not documentation inputs. External
catalog URLs, repository popularity, software releases and historical model
preflights were not refreshed; their dates remain explicit.

## Corrections and current limits

- Capture guidance now separates wall-tone eligibility from camera-height
  observability. Hole-derived height requires enough qualifying points and an
  accepted minimum, under approximate-roundness assumptions. The 0.2σ wall-bias
  figure retains its 16 % contrast assumption; a historical 0.1 mm error is not
  presented as a universal bound.
- The tracing and architecture guides describe complete contour coverage,
  accepted precision measurements, final-camera transport and source-support
  fallback separately from later Gaussian reconstruction and the API's profile
  self-consistency check. The tiny-chamfer test can retain its observed polyline.
- Privacy and API guidance include the `holes` focal source. AI remains
  text-only, explicitly applied and separately evaluated; no live model-quality
  result is inferred from integration fixtures.
- The correlation factor is correctly described as a bounded positive-lag
  heuristic. Its docstring and method guide no longer identify it as Geyer's
  different paired estimator. No calculation changed in that documentation edit.
- The library verification guide explains that a final documentation check can
  fail after writing its JSON. Its browser-file count now agrees with the
  existing dated receipt, and the cadkit guide no longer promises a `warnings`
  field on every mapping returned by its APIs.
- Troubleshooting covers weak contrast/focus even when the whole sheet is
  visible. The reproduced path returns a contained 422 response with generic
  guidance; actionable internal error handling remains further work.
- The [benchmark guide](../photo-benchmark.md) now describes the global matcher
  and complete dimension-coverage counters merged in PR #43. Original greedy
  and failed-photo-denominator findings remain explicitly historical. Size
  gates remain heuristic and repeated equal-size features remain ambiguous.
- The [directional-blur research status](../research.md#directional-blur-experiment-status--november-12-2026)
  records negative correction results and an unflagged tone-mismatch control.
  No experimental covariance correction is represented as a product feature.

## Completed checks

- All **51 Markdown documents** parse with the library's locked `marked`
  dependency. **456 local links**, including **33 fragment links**, resolve;
  **75 Markdown tables** have consistent column counts.
- `make build-library`: passed. All tracked library outputs, including the PDF,
  are byte-identical to the reviewed baseline. Release and verification receipts
  were not rewritten.
- From `reference-library/`, `.venv/bin/python -m unittest discover -s tests/python -p test_docs.py -v`:
  **19 tests passed**, covering documentation numbers, catalog counts, figures,
  command coverage, local links and PDF pages.
- The integrated support candidate passed **529 Python tests** and **74 browser
  scenarios** against the actual local CAD backend; the [support record](fit-support.md)
  specifies fixtures, boundaries and the earlier failing controls. Frontend
  production build, Ruff and source formatting checks passed.
- After integrating PR #43 at `d6a657f`, the final complete Python invocation
  passed **579 tests** in 138.39 seconds. That merge adds benchmark scripts,
  tests and documentation; its API/frontend sources are unchanged from the
  completed 74-scenario browser run. The separate three-photo CLI example was
  regenerated: all 48 requested scalars matched, and both generated tables
  exactly match the guide. Its matched-error median/p95/worst values round to
  0.004/0.014/0.015 mm, with no real-photo accuracy claim.

Local receipts live in `.local/verification/`. Documentation checks do not
refresh historical software tests, prove external-site availability, qualify
native slicers or establish measured-photo accuracy, physical fit, structural
performance or complete accessibility conformance. Hosted CI, source merge,
installed state and deployment remain separate evidence.
