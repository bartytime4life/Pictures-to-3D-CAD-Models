# Circle-consistent arc assembly — November 12, 2026

This candidate is based on published [PR #71](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/71)
at `861de04baa0e55775e7a90faba9288ea2205abf6`, tree
`ab586e3b1df58713461b869aa86c4ed9ed7e8416`. It repairs final line/arc assembly
in production reference-sheet tracing. The primary checkout is preserved.
API fields, project formats, measured scale inputs and interface controls are
unchanged. [Project status](../project-status.md) separates this review candidate
from integrated `main`, installed services and physical qualification.

## Reproduced problem and useful positive controls

The old assembly joined a free arc to neighboring line feet, then placed its
midpoint at the stored radius. The three emitted points could define a different
circle. A valid profile and CAD solid did not detect that representation error.
An exact circular segment closed by one chord had the opposite failure: both
joins became the same foot, so supported minor, half and major circles were
rejected as analytic fits.

The new tests specify circle/chord geometry independently and exercise the
actual `fit_ring` path, radius edits, equalisation, source reversal and cyclic
starts, rigid motions and equivalent line directions/anchors. Native controls
write and re-import STEP, read actual DXF circles and parse SVG geometry. A
separate ordered-cycle example requires a root farther from the source endpoint:
choosing each nearest root independently would reverse a line.

The existing synthetic-regression census passed **199 tests** at the untouched
baseline, with all **517 tracked files** unchanged. Its **941 segment calls**
included **2,172 initial free arcs**, of which **1,975** missed at least one line.
These repeated/correlated fixtures are a development population, not independent
observations or a physical failure rate. The result establishes why final exact
joins cannot simply replace the pre-correction eligibility construction.
The complete census rows, runner and source hashes remain in the local review
receipts; the old output is not relabeled as a run of this candidate.

## Construction, fitting objective and numerical limits

For a circle `C,R` and line with unit direction `d`, let `F` be the perpendicular
foot and `h=|C-F|`. When `R>h`, its two roots are
`F ± s d`, with `s=sqrt((R-h)(R+h))`. For source endpoint `P`, the squared
endpoint-displacement objective has reduced costs `±2s d·(F-P)`; common terms
are removed before ranking. Both neighboring primitives contribute a witness.

Frozen ordered source endpoints define line traversal. An arc's signed source
sweep and transported interior witness select winding and sector. Full old-angle
containment is deliberately not required: a correct radius change at a fixed
chord can trim its angular support.

A bounded cyclic dynamic program compares additive upper/lower score guards.
A selected path must be separated from every distinct alternative. Numerically
unresolved compatibility remains in both searches; it cannot be discarded to
create a winner. A selected unresolved transition refuses construction. The
search accepts at most **1,024 primitives** and at most two roots per junction.
It checks local progress and sectors; whole-ring/profile validity remains a
separate check, rather than a claim that local DP proves global simplicity.

Near tangency, `ds/dR=R/s` becomes ill-conditioned. Free near-contact cases stay
unresolved unless the represented inputs are exactly tangent. Prescribed tangent
fillets permit roundoff-level foot normalization. One explicit design-intent
failure can also retain an already observed tangent contact when its radius
coordinate is unresolvable: both original line distances must agree with its
unchanged radius within the arithmetic guard, and its unresolved-radius note
remains. This does not impose tangency with snapping off.

The final three-point circle is checked in local coordinates against stored
`C,R`. The circumcentre routine also uses local differences, preserving its
rational-input regression while reducing cancellation from world coordinates.
These are engineering floating-point guards, not certified exact constructions,
measurement uncertainty or an endpoint-accuracy guarantee. Source partition
points can be biased by blur and segmentation; a unique objective minimum is
not a uniquely identified physical boundary. See the [research derivation](../research.md#circle-consistent-joins-and-minimum-edit-cycles).

## Initial eligibility and final recovery

Initial support tries canonical assembly first, which makes transverse chord
controls reachable. If that construction is unavailable, the historical
line-foot/midpoint proxy may still establish initial geometric eligibility.
It lets a blur-shrunken circle reach the existing correction/model-fitting
stage. The proxy does not establish canonical joins, supply root provenance or
become final export geometry. Every final analytic ring must construct separately.

A missing, ambiguous, over-budget or numerically unresolved final join retains
only the affected traced ring and explains why in saved reference notes and
main workbench warnings. Other accepted analytic rings and sheet calibration
remain. A bounded saved summary covers large groups of affected holes; the
warnings retain individual reasons. Radius/design notes and fit counts describe
accepted final geometry, and discarded fitted lines cannot determine display
alignment when no analytic lines remain.

If no valid retained profile can be formed, the request returns actionable 422
guidance. That is not classified as a missing sheet and cannot silently take
the ordinary-trace fallback. Existing project-preservation behavior remains.
Follow the [critical-curve review steps](../exports.md#verify-critical-arc-geometry)
before relying on a recovered outline for fit-sensitive geometry.

## Independent and conditional controls

The committed [plan](../../studies/canonical-arcs-v1.json),
[independent runner](../../studies/verification/canonical-arcs-oracle-v1.py) and
[complete result](../../studies/results/canonical-arcs-oracle-v1.json) retain all **132 rows** and **394 checks**. Raw-direction quadratic intersections
in Decimal80 and exhaustive small-cycle enumeration independently check 33
geometry controls. All 31 separated choices pass; two tangent ambiguities remain
unresolved. A separate 96-matrix exhaustive control checks ternary compatibility
and the distinct-path lower/upper searches.

The final three controls use independent finite Gaussian-blurred circular
segments, evaluated by vertical-slice quadrature with standard-library `erfc`.
The 24/48-point quadrature agreement is a numerical cross-check, not a certified
integration error bound. Two observations remain initial polylines; one remains
analytic. Nonzero complete-boundary discrepancies remain in the report, and the
analytic case's radius correction is only a conditional improvement. None
establishes complete finite-shape recovery or physical camera accuracy.

```bash
.venv/bin/python studies/verification/canonical-arcs-oracle-v1.py --output .local/canonical-oracle-new.json
```

Use a fresh destination. Help and destination refusals run before analysis;
injected first-row failure retains every row and still executes the later ones.
The report binds the complete plan, runner and imported implementation before
and after execution. No server, personal photo, model inference or native
application launch is needed for this oracle.

The separate [actual-fit runner](../../studies/verification/canonical-arcs-fit-v1.py)
uses six controls: exact R10 circular segments at chord positions −6, 0 and +6,
each with requested blur correction 0 or 1.5. These inputs are unblurred; the
positive sigma is a deliberately mismatched representation stress, not an
optical-recovery experiment. The [candidate result](../../studies/results/canonical-arcs-fit-v1.json)
retains **6/6 initial and final analytic boundaries, all 48 checks passing**.
The identical runner against pinned PR #71 retains
[all six baseline rows](../../studies/results/canonical-arcs-fit-baseline-v1.json):
**0/6 analytic boundaries**, 36 failed target checks and **zero execution errors**.
Its exit status 1 records those expected target failures. No failed rows are
removed. Both reports bind the imported backend and runner before/after execution.

```bash
.venv/bin/python studies/verification/canonical-arcs-fit-v1.py --output .local/canonical-fit-new.json
.venv/bin/python studies/verification/canonical-arcs-fit-v1.py --source-root /path/to/pinned-baseline --output .local/canonical-baseline-new.json
```

Nine early help/destination controls and an injected first-call error check
fresh-path refusal and complete six-row failure retention. These controls do
not start a server or export CAD; native-export coverage is in the regression
tests described below.

## Source and artifact binding

The regression freezes **327 product files** (source, configuration, tests and
assets), excluding Markdown and studies. Freeze v2 has SHA-256
`ae8823a8b5c21f25f8bc46333595fc419cad752de73e2410b9f8ef23f0547c75`;
its only change from the first freeze is the legacy recovery-contract test.
The three production files are identical across both complete runs and the
candidate scientific reports; the baseline comparison separately pins older code. The reviewed baseline tree is unchanged by its
later merge at `cecb8b6`; publication can use that parent without changing bytes.

| Changed implementation/test file | SHA-256 |
| --- | --- |
| [backend/circular_joins.py](../../backend/circular_joins.py) | `1647721fe8763c61ae3c3fe2eb51201fc1d3cf5866c27a49caa74e66e682bde7` |
| [backend/fitting.py](../../backend/fitting.py) | `99b9232624eef3bc8106c5d82277f47817cd5d0c62eb6d6d27fd2ac34c958489` |
| [backend/reference.py](../../backend/reference.py) | `245976b83a41ed8c8aa3f29154653ba17f1d6c35ed47dd6a266acfde42e9df31` |
| [tests/test_arc_joins.py](../../tests/test_arc_joins.py) | `737bc0571ecb9573d50d6938941c9c96561f68af4e19c5c7a6fd24a3d2b270d9` |
| [tests/test_arc_join_recovery.py](../../tests/test_arc_join_recovery.py) | `ee45abf7b9540201a2fc231493e22c4366a2ef88803460c9e003fa7205501a18` |
| [tests/test_sheet_reference.py](../../tests/test_sheet_reference.py) | `ccf47a25b61fb3e36a554e7c8fd585ebd869595cb48415cdcc2afacbcd9fba65` |

The archived scientific reports contain complete imported-backend and
runner/plan hashes, row settings and before/after checks. Their exact file hashes
are:

| Complete result | SHA-256 |
| --- | --- |
| [canonical-arcs-oracle-v1.json](../../studies/results/canonical-arcs-oracle-v1.json) | `91f45793cea7142adbb62eeafcc9f8bf4619d764321a438a2029f68f17e4c6ae` |
| [canonical-arcs-fit-v1.json](../../studies/results/canonical-arcs-fit-v1.json) | `3cb0bb2d2a87a8088e9f5cd2228ee0cf0917725a2957b9401c8d9792dd5f08cc` |
| [canonical-arcs-fit-baseline-v1.json](../../studies/results/canonical-arcs-fit-baseline-v1.json) | `b024c29a66124b3dcf7ff77144fd18bef0364a50dd5d12084181c5f70267877f` |

## Regression and review evidence

The first frozen-source full run completed with **1,605 passes and four failures
out of 1,609 tests**, with no errors or skips. All four failures came from the
older R30/stub fixture calling final low-level assembly directly on genuinely
disjoint line/circle candidates. Their radius/distance gaps were 0.00133–0.00594 px,
well beyond arithmetic guards. Production recovery correctly keeps those source
outlines. The test now exercises that actual recovery path, retaining every
original initial-fit/count, candidate-radius, corner and **0.03 % area bound**.
It additionally requires four named recovery cases, explicit notices and two-way
continuous source-tube coverage at the standard **0.25 px** simplification setting;
the other eight modes must remain analytic with independently checked circles.
Maximum recovered area error is **0.0249943 %**, inside the unchanged bound.
The radius assertion describes the discarded candidate on recovered rows.
No circle/line was moved or tolerance relaxed to pass the tests.

The **59 focused tests** pass: 35 canonical-construction/export cases, 18 recovery
cases and six original parameterized stub fixtures (12 internal fit modes).
The second freeze changes only that legacy test relative to the first freeze;
all production files are identical.

The final frozen-source run passes **all 1,609 Python tests**, with **zero errors,
failures or skips**, in 331.00 seconds (331.98 seconds supervisor elapsed).
All 327 frozen files match before/after. Its JUnit SHA-256 is
`1a2075e69fc95025ad58e19b72a555342dcdc478c387fa28f4847d0bdbea467d`.
The frontend build, Python lint, formatting of the five new Python files and
existing frontend/browser-source formatting checks pass. Existing legacy Python
files retain their prior formatting; no repository-wide Python reformat is
claimed.

The first browser run completed on a fresh candidate server at port 8000 with
**72 passes and two failures out of 74**, zero skips and zero flaky results, in
474.96 seconds (475.57 seconds supervisor elapsed). Both slicer cases received
the intentional build-busy 429 response; the first page's initial build had
already returned 200 before its later request was rejected. Its trace contains
no overlapping build from that page. The competing lock holder is unobserved;
this does not establish a leak from the completed build or a canonical-join
failure. The complete JSON, failed traces/screenshots and source/bundle checks
are preserved separately. The first browser JSON SHA-256 is
`a5f5521333146851746f078fefce302fd3ff0d64573583a7e260f93a79008cc8`.

A single full comparison then ran the same source, built bundle, 74 tests and
original timeouts on an exclusively owned server at loopback port 55991, with
fresh job/handoff directories. `PICAD_TEST_URL` selected that verified process;
no retry or application change was added. It passes **all 74 browser scenarios**,
with **zero skips, failures or flaky results**, in 400.68 seconds (401.60 seconds
supervisor elapsed). The access log records 117 successful builds,
one expected invalid-build 422 and no build-busy 429 responses. All 327 frozen
files and the complete built bundle match before/after. The owned server was
stopped after completion. The comparison JSON SHA-256 is
`bce57877ac5cfc2d60250a0deaa1cdfb5c4711ba78c7dc0795a8e33b421382b1`.

This establishes the isolated run; it does not identify the earlier competing
requester or establish a concurrency fix. The original failures retain their own
terminal status and artifacts. Follow the [browser isolation instructions](../development.md#validate-changes)
for repeatable source-bound checks.

The earlier incomplete development run exited with SIGTERM and produced no
complete JUnit result; it is retained separately. Completion is established only
by the final frozen-source receipts. Successful digital checks do not qualify
real-photo accuracy, native slicer acceptance, material strength or physical fit.
Full forward-model adequacy and jointly inferred optics/response/geometry remain
separate scientific work.

## Documentation coverage

The preceding [95-document review](documentation-pr70.md#coverage-inventory)
retains its original source binding. This record adds the current geometry
construction and recovery guide; current task navigation and affected
engineering/export guides are aligned with it. Historical reports and generated
companion-library artifacts keep their original results and dates.

All **96 Markdown documents** are reviewed against the preceding source-bound
inventory. **21 affected documents** are updated; the other **75** match PR #71
byte for byte, including all 39 earlier validation records and the companion
library's 16 Markdown files. The older records retain their original limitations,
review states and test counts. Current status records the observed individual
PR merges separately from integration into `main`.

| Documentation group | Files | Updated |
| --- | --- | --- |
| Workbench guides, root and source-data notes | 40 | 20 |
| Dated validation records, including this new record | 40 | 1 |
| Companion-library guides and worksheets | 16 | 0 |

The complete per-file inventory/hashes and structure-check receipt are retained
in local review evidence. Local links, heading fragments, code fences and table
structures pass with zero errors. The additional HTML image link resolves.
The companion library's **19 existing documentation tests** pass; generated
library inputs and release artifacts are unchanged, so no library rebuild or
new release is claimed.

All **41 argparse command-help paths**, root `make help` and **26 API/signature/
example contracts** pass. Both documented endpoint maps match all **11 OpenAPI
operations**. Current response examples execute to fresh local destinations;
overwrite refusal preserves original reports. All **431 frozen non-Markdown
files**, including source and archived studies/results, match before/after the
contract checks. These checks start no server or model inference.

The final navigation audit checks **1,619 local Markdown references**, **119
fragment references** and **159 tables**, plus the separate local HTML image,
with zero structural/navigation errors. The audit hashes every document before
and after its check. Independent code, mathematical and documentation reviews
found no remaining blocker after the recorded wording corrections.
