# Reference-sheet weak-edge recovery

Initial local check recorded November 12, 2026, from `main` at
`d6a657f93f13b818a8e44e2ace219b2d4598b4ef`. This focused error-recovery change
does not alter scientific fitting or benchmark behavior. It does not establish
a published release or real-photo accuracy.

## Reproduction and cause

The actual `tests.synthetic.colour_photo` renderer produces an A4 capture with
table `(185, 185, 185)`, paper `(220, 220, 220)`, part `(200, 200, 200)`,
`ppm=3.0` and `blur=4.0`. Its PNG SHA-256 is
`c947cb587aa2fe57e765de36b2bd44ea99fe4334796c30fe7a7e279874c59fbc`.
The sheet contrasts with the table and part segmentation succeeds, but the first
sub-pixel edge pass retains fewer than eight outer-boundary measurements.

Previously `backend.edges.subpixel_rings` assumed that an outer boundary had
survived and raised `StopIteration`. Direct `trace_on_sheet` exposed that
exception. The regular upload path caught it and returned HTTP 422 with generic
advice to show the whole sheet. No HTTP 500 was reproduced.

The change explicitly checks for a retained outer boundary before estimating
blur and raises `EdgeError` when it is absent. The existing reference and API
handlers preserve this actionable message:

> The part's outline is not clear enough to measure. Retake the photo in focus
> with stronger contrast between the part and the sheet.

The first-pass minimum contrast of 12 saved levels and minimum of eight retained
points are unchanged. So are the second pass, hole handling, blur estimation,
`sigma=0` median-level fallback and automatic fallback policy. No renderer or
existing accuracy-test tolerances were changed.

## Regression evidence

All four cases in `tests/test_contrast_recovery.py` failed against the unchanged
base for the intended missing error type or guidance, before the production fix:

- The actual rendered capture must raise `ReferenceError_` caused by `EdgeError`,
  with focus and contrast guidance, through direct `trace_on_sheet`.
- A separately constructed annular image has a faint outer edge and a clear hole.
  A retained hole must not substitute for a missing outer boundary.
- A real in-process FastAPI request must return 422 with the same guidance, then
  accept a clearer capture on the same `TestClient`. The independent rendered
  geometry is a 60 mm disc with a 16 mm hole; both recovered diameters must be
  within 0.03 mm.
- The same API recovery is required for a lower-contrast but sharper capture that
  has no measured blur (`edge_blur_mm == 0`). This protects successful median-level
  tracing rather than rejecting every unavailable blur estimate.

The API cases use the real decoder, sheet finder, segmentation, edge measurement,
fitting, error handlers and request lock. Only the temporary job directory is
redirected. They request `reference=a4` with `fallback` left at its default
`false`; the initial-upload automatic fallback policy is unchanged. They do not
mock trace outcomes or run a listening server.

After the fix at `5d1d6febeb1f37338e2c557f4d2361cf6b702a2f`, the focused run of
`tests/test_contrast_recovery.py`,
`tests/test_fidelity_math.py` and `tests/test_sheet_reference.py` passed
**154 tests in 100.55 seconds**. This includes the existing edge, blur, camera,
fitted-export and synthetic accuracy regressions. Full
`ruff check backend scripts tests` and `git diff --check` passed. Python 3.12.3 reused an existing
environment only after its `uv.lock` and `pyproject.toml` hashes matched the
candidate checkout. No dependency installation was needed.

## Integration with main — November 12, 2026

The preserved candidate `5d1d6febeb1f37338e2c557f4d2361cf6b702a2f` was normally
merged with `main` at `03f71e0e4095ee873051b71264b45fde83f84891`, which includes
PR #44. The edge-pass tuple now carries retained points, the complete classified
support contour and retained indices. Conflict resolution kept all four fields
and adapted the guarded outer extraction to that tuple. Duplicate troubleshooting
guidance was combined, and both change-log histories were retained. The four new
contrast regressions are unchanged from the earlier candidate.

After integration, the **complete workbench Python suite passed 583 tests in
169.01 seconds, with no skips**, using the same Python 3.12.3 environment and
matching lockfiles. The command was `python -m pytest -q` from the candidate
checkout, using that environment's interpreter. This fresh run includes the
contrast regressions, initial-fit support and support-transport tests, alongside
the existing workbench tests; it is separate from the earlier 154-test result.

Full `ruff check backend scripts tests` and whitespace checks passed. Local
documentation checks validated 458 relative file targets and 31 Markdown heading
anchors across 52 tracked Markdown files. Inline and fenced code examples were
excluded; external URLs and HTML anchors were not checked. No browser, frontend
build, companion-library suite, hosted CI, installed-tool or physical-validation
claim is added by this integration.

## Scope and limits

This guard supplies useful recovery advice; it does not accept the rejected photo,
lower measurement thresholds, recover missing image detail or qualify the camera.
The synthetic renderer and production tracer share tone and sheet-model
assumptions, so these cases establish error handling and bounded digital geometry
regression behavior. They do not establish real-capture metrology, native CAD or
slicer acceptance, browser behavior, or physical print performance.

See [troubleshooting](../troubleshooting.md#image-and-tracing-problems) for the
user action and [reference-sheet tracing](../reference-sheet.md) for the model's
broader assumptions and evidence limits.
