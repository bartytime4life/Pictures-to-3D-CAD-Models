# Joint wall and lighting experiment — November 12, 2026

The [method](../wall-gradients.md) adds bounded source lighting and examines
wall/edge ambiguity. This candidate is based on published source
`37eb4d2086c61dda983fe4e39391d9693dc82331` ([PR #56](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/56)).
The new solver is a developer experiment. Production changes clarify comments
and docstrings; their executable ASTs match that baseline after removing
docstrings. No tracing correction, UI, API, dependency or acceptance rule changes.

## Executed population and artifacts

The plan was frozen before inspecting the full study outputs. It is not an
external preregistration or held-out qualification population. Python **3.12.3**,
NumPy **2.5.4** and OpenCV **4.14.0** executed it in the existing local environment.

| Lane | Worlds | Crossed treatments | Rows | Failed execution rows |
| --- | --- | --- | --- | --- |
| Direct continuum samples | 60 | 7 supplied offsets × 2 light models | 840 | 0 |
| Rendered images | 144 | 2 stages × 2 wall-tone treatments | 576 | 0 |

Direct worlds cross two optical widths, five wall widths, three lighting
conditions and two contrast polarities. Image worlds cross two optical widths,
three wall widths, three lighting conditions, two polarities, two directions
and two phases. Repeated treatments share worlds; they are not independent
scene replication. Node levels are fixed while the tail is `12σ`, so physical
slopes in levels/pixel also depend on the supplied optical width.

The two image stages are centre samples and uniform unit-square means. Both
retain actual production Keys profile sampling and supplied optical `σ`.
They do not estimate pre-aperture blur. The aperture order-6/order-12 comparison
changed a value by at most **2.22e-10** linear-light levels over all 144 scenes,
below the predeclared `1e-6` numerical check. This is agreement of floating
calculations, not an interval bound or a real sensor calibration.

The complete publication artifacts are:

- [Executed plan](../../studies/results/wall-gradients-v1/plan.json) and
  [results with all 36 image groups](../../studies/results/wall-gradients-v1/results.json).
- [840 geometry fits](../../studies/results/wall-gradients-v1/geometry-fits.csv) and
  [576 image fits](../../studies/results/wall-gradients-v1/image-fits.csv).
- [Complete CSV audit](../../studies/results/wall-gradients-v1/audit.json),
  independently recomputing 36 image summaries and six midpoint-witness summaries.
- [Separate source-integral checks](../../studies/results/wall-gradient-source-oracle.json)
  and [basis/box-fit review](../../studies/results/wall-gradient-node-review.json).

The audit finds complete unique Cartesian keys, physical fitted source nodes
and finite successful outcomes. It checks every CSV row and relevant summary;
it does not independently execute the production renderer or certify optimization.

## Constructive findings

With fixed wall width `w`, `(e, B=C)` and `(e+w, B=A)` have identical flat source
fields. The example's silhouette separation is 1.5 pixels; the independently
evaluated floating responses differ by at most `8.53e-14` levels. The exact
identity follows from the piecewise source definition, rather than that small
numerical residual. Any forced common single position has at least 0.75 pixels
of error for one of the two model interpretations. This is a local scalar-model
result, not a pair of demonstrated complete physical camera scenes.

The finite-grid midpoint witnesses are:

| Illustrative absolute level budget | Flat-tone witnesses / 360 alternative fits | Joint-gradient witnesses / 360 alternative fits | Largest joint-model edge separation, px |
| --- | --- | --- | --- |
| ±0.025 | 4 | 12 | 0.165 |
| ±0.25 | 12 | 48 | 0.4125 |
| ±1 | 24 | 132 | 0.825 |

Every pair constructs its own midpoint observation. Its budget applies to
that midpoint, not to the original truth-sampled observation at half the
discrepancy. The CSV retains both `maximum_difference` against original samples
and `midpoint_error_bound`. These are supplied level-budget scenarios, not
measured camera noise, exhaustive geometric enclosures or confidence levels.

Maximum absolute image-fit errors over the crossed cases are:

| Supplied wall tone | Light condition | Point-stage error, px | Pixel-mean-stage error, px |
| --- | --- | --- | --- |
| True value fixed | Flat | 0.00343 | 0.0117 |
| True value fixed | Top gradient | 0.0466 | 0.0489 |
| True value fixed | Top and paper gradients | 0.0975 | 0.1001 |
| Fitted freely | Flat | 0.2999 | 0.1970 |
| Fitted freely | Top gradient | 0.2029 | 0.2265 |
| Fitted freely | Top and paper gradients | 0.0705 | 0.0895 |

Gradients do not uniformly worsen every fitted outcome; free wall tone can
absorb different combinations of gradients and sampling error. Its larger
flat-control errors matter too. A better residual or one successful ablation
does not establish the correct physical geometry. No original results were
discarded to obtain this table.

## Independent mathematical checks

The source-integral oracle integrates the explicit linear source segments with
Gaussian density quadrature and `erfc` constant tails, separately from the
runner's analytic basis. Ten development witnesses include 10,001-point dense
checks. Its maximum analytic/integral and order-8/order-16 differences are both
`1.14e-13` levels.

A separate review checks the runner's basis on **24 geometries**, including
zero-width bands and shifted edges: maximum basis/integral difference
`5.56e-16`, quadrature change `3.34e-16`. It also checks **50** box fits, including
duplicate and absent columns, using convex first-order optimality conditions;
all are feasible and the largest absolute KKT violation is `6.57e-12`.
A boundary-active case uses all 243 faces and reaches wall level 255. These
floating checks support the implementation within their scope; they do not
certify all ill-conditioned fits or establish physical priors.

## Regression and source binding

The full Python suite passed **1,131 tests in 198.64 seconds**, including 20 new
study tests. Ruff and whitespace checks passed. After the backend's
documentation-only clarification, executable AST equality was verified,
23 relevant tests passed in 1.70 seconds, and the complete study was rerun.
Both CSVs and every numerical summary were identical to the earlier run.
There was no frontend change requiring new browser-behavior evidence.
The documentation audit parsed all **73 Markdown documents**, checked **744
local links**, **54 heading fragments** and **121 tables**, with no errors.

| Executed source | SHA-256 |
| --- | --- |
| `scripts/wall_gradient_study.py` | `046a8202224b7066046974a2496f2f1839b2116703c9d0c3ca75cc0b097b5172` |
| `studies/wall-gradients-v1.json` | `920214ef96ba56fcf220efaaddb95944ba10e03126b25a0a34cf75d2bfb92b1f` |
| `backend/edges.py` | `d70fc6bae46c86015315cbf110a7c441d8ba04d8ebd6c4d732a52aa5099fa87e` |
| `backend/sheet.py` | `a086d7216256726a0e392bd98cbdb1274f5cb5eb096802c17c805349a7747e31` |
| `backend/tone.py` | `88a9d8937c27c0793d650e1c8762c0acb24c17de710a6c6b20992929360f50ee` |

Geometry CSV SHA-256:
`ef44b7c97ad8e1a4069ab97a0df91ef8b4de255b1a5b27aa86703e35f9be65f0`.
Image CSV SHA-256:
`6234b1040b9b72b8cffb1395adba5970b5cd30e89d22e335dc67e81c023db52c`.
The summary records a dirty candidate based on PR #56; exact executed hashes
identify its sources independently of the parent revision.

## Reproduce

```bash
make wall-gradient-study OUTPUT=.local/wall-gradients-new
.venv/bin/python studies/verification/wall-gradient-audit.py --run .local/wall-gradients-new --output .local/wall-gradients-audit-new.json
.venv/bin/python studies/verification/wall-light-identifiability-oracle-v1.py --output .local/wall-source-oracle-new.json
.venv/bin/python studies/verification/wall-light-node-review-v1.py --output .local/wall-node-review-new.json
.venv/bin/pytest -q tests/test_wall_gradient_study.py
```

Use new result paths; existing outputs are refused. The optional
[figure source](../../studies/verification/plot-wall-gradients.py) needs
Matplotlib (3.11.2 used locally) and accepts `--run`, `--output NEW_SVG` and an
optional `--preview NEW_PNG`. The figure was visually inspected for labels,
values and clipping. No new production dependency was added.

Remaining work includes constraints supported by independent measurements,
wrong-seed and whole-ring behavior, pooled-tone model adequacy, unknown/correlated
PSFs, actual camera tone/response, full geometry/capture consistency and reserved
real measurements. The study supplies neither an automatic correction nor
physical qualification.
