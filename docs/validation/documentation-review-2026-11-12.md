# Documentation review — November 12, 2026

Reviewed the repository documentation against `main` at
`eec45d04cf767f2a55e8581a009b8052fe349180`, including merged narrow-wall and
camera-height changes, then integrated the merged benchmark repair at
`d6a657f93f13b818a8e44e2ace219b2d4598b4ef` and the
[initial-fit support candidate](fit-support.md).
Work used an isolated checkout; the original `codex/slicer-integration` checkout
and existing worktrees were preserved. This review accompanies the source-support
change; documentation and runtime checks are recorded separately below.

The model-checks follow-up later on this page covers the expanded documentation
and normal integration of `main` at `5c07d0f`. Earlier inventories and test totals
remain records of their original reviewed revisions.

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
  guidance at this review's baseline. The later [weak-edge recovery repair](contrast-recovery.md)
  adds actionable focus/contrast guidance without changing the measurement gates.
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

## Model checks follow-up

After PR #44 merged at `03f71e0e4095ee873051b71264b45fde83f84891`, reviewed
the current guides again for the [radial-domain repair and independent renderer](radial-inverse.md).
The earlier review, library checks and test counts above retain their original
inputs. This follow-up uses an isolated candidate on that integrated baseline;
the separate contrast-recovery and fillet-sector PRs are excluded from its
source and test totals.

- Replaced the incorrect whole-frame inverse claim with the central-branch
  domain, reference-observation feasibility bound and near-fold sensitivity.
  Added the numerical figure, Decimal checks and six higher-order lens mismatch
  results. Production still fits one radial coefficient.
- Updated research, engineering limits, roadmap, architecture, README,
  benchmark pointers and navigation for the separately implemented renderer.
  Historical reports now point to later work without rewriting original
  findings as successful tests of later code.
- Added the [frozen 30-case directional-spread record](directional-spread-qualification.md),
  including orientation-imbalanced misses, negative/unknown results, all planned
  outcomes and local artifact hashes. The warning and anisotropic correction
  remain research only; unflagged does not mean accurate.
- Documented each test checkout's root `.venv` requirement. The first browser
  invocation had **72 passes and 2 failures**: both export inspectors could not
  start `.venv/bin/python` (`ENOENT`). Its logs, reports and traces were preserved
  before creating this checkout's frozen Python environment. No product code,
  assertions or timeout settings were changed to address that setup failure.

The candidate passed **609 Python tests** in 141.30 s, including 30 new lens
checks, with no skips; the [radial record](radial-inverse.md#completed-checks)
also preserves the failing original controls. Ruff and the production frontend
build passed. With its own frozen Python environment, the complete browser
invocation passed **74 scenarios in 5.5 minutes**, with no failures or skips,
against this checkout's CAD service on loopback port 18018. The service was
stopped after the run. This completed invocation is separate from the preserved
environment-failure run above.

All **53 Markdown documents** parse; **490 local links**, including **36 fragment
links**, resolve, and **79 tables** have consistent columns. The companion
library's source and generated outputs are unchanged by this follow-up. Its
earlier generated-output and 19-test documentation results remain those of the
original review, not a new full library release.

Local proof, hosted CI, merge, installed state and physical qualification remain
separate. The earlier PR #44 [workbench run 104](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43167726360)
and [library run 37](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43167726440)
completed successfully; they do not validate this later radial candidate.

### Integration with the merged recovery and fillet repairs

PRs #45 and #46 then merged externally into `main` at
`5c07d0f70d7df0200bc24227c8ac7e9b630f7f09`. The candidate normally integrated
that revision, preserving both earlier change-log histories. The 609-test and
74-scenario results above retain their pre-integration source binding; the
six-case lens probe and pinned directional experiment were not silently rerun
or relabeled as new evaluation data.

The integrated complete Python invocation passed **623 tests in 142.24 s**, with
no skips. Its fresh complete browser invocation passed **74 scenarios in 5.4
minutes**, with no failures or skips, against this checkout's CAD service on
loopback port 18018. The service was stopped after verification.
Production frontend build, full `make lint` and whitespace checks
passed. All **55 Markdown documents** parse, **503 local links**, including
**37 fragment links**, resolve, and **79 tables** have consistent columns.
The companion-library documentation invocation was freshly repeated against
this checkout's unchanged library sources: **19 tests passed**. Its generated
HTML, PDF, archive, catalogs and source files remain byte-identical to the
integrated baseline. This documentation-only library check does not establish
a new library release or native-tool qualification.

### Corner-resolution follow-up

The next candidate, based on PR #47 head `ba94ef8`, adds the
[search guard and conditional-resolution record](sharp-corner-resolution.md).
Current method, engineering, research, change-log and CLI guidance replace
physical upper-radius claims with conditional blur-model estimates. Historical
tables retain their original fixtures and have a later-interpretation pointer.
The new record preserves a direct-helper search failure, an independently
constructed rounded-corner counterexample, excluded invalid development
geometry and the primary-source requirements for future feasible-set inference.

The complete candidate passed **630 Python tests**, **74 browser scenarios**,
the four-case corner sweep, production build and full lint checks. All **56
Markdown documents** parse; the local-link, fragment and table checks are
recorded with the candidate's final source receipt. Companion-library sources
and generated outputs are unchanged; no new library release or physical
qualification is claimed.
