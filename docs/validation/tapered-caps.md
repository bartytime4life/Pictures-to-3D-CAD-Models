# Preserve tangent geometry at tapered rounded ends

This production fitting candidate is based on published draft PR #69 at
`0d8bd37633900f4f88200be13bd5309d28ca58f2`. The only existing executable source
changed is [backend/fitting.py](../../backend/fitting.py). Scale inputs, API/file
schemas, dependencies and the interface are unchanged. Independent exact
profiles and actual native exports establish a digital geometry repair; they
do not establish physical-camera accuracy or manufacturing acceptance.

## Reproduced failure

The cap branch treated oppositely directed lines within five degrees as
parallel. It projected both line anchors onto the first line's normal and used
half their apparent spacing as the cap radius. A line's anchor can move along
that line without changing its geometry. With a real taper, this projection
changes, so the radius depended on an arbitrary line representation and on the
length of the fitted straight edges.

An independent exact R10 arc with two tangent sides differing by two degrees
exposes the error with no image, noise or blur. The original fitting chain
`fit_ring → snap_axes → refit_lines → fit_fillets → correct_blur → equalise_radii`
initially fits the correct circle, then changes the final cap. Moving only the
second line's anchor by −100, 0 or +100 units along itself produces stored radii
about 9.999, 11.744 and 13.489 instead of the same R10.

The emitted arc uses two line-foot endpoints plus a radius-derived midpoint.
When those endpoints no longer lie on the stored circle, the exported three-point
arc describes a different circle. At straight-side length 200, the original
stored radius is about 11.744 while the emitted radius is about 10.125. Valid
polygon topology and a valid CAD solid do not catch this representation error.

The complete [baseline export receipt](../../studies/results/tapered-cap-exports-baseline-v1.json)
retains all eleven rows: seven tapered failures and four passing genuine-parallel
controls, with no execution errors. Every malformed tapered case still passes
actual Profile validation and valid single-solid STEP readback. The source and
runner are bound before and after execution; the baseline remains the untouched
published checkout, rather than an overwritten source file.

| Independent exact case | Baseline boundary discrepancy, coordinate units | Repaired discrepancy |
| --- | --- | --- |
| R10 cap, side length 50 | 0.436726 | 0.000998 or less |
| R10 cap, side length 100 | 0.893804 | 0.000998 or less |
| R10 cap, side length 200 | 1.863747 | 0.000998 or less |
| R10 cap, side length 400 | 4.014500 | 0.000998 or less |
| Hull of R20/R24 circles 160 units apart | 2.036697 | 0.000998 or less |

These sampled-boundary discrepancies include the declared source/validation
chord approximation. They are not physical measurement errors. Under the
runner's supplied 0.2 mm per coordinate unit, the original R10/length-200 STEP
width differs from the known width by **0.372715 mm**. That scale is a synthetic
input, not a recovered camera calibration.

## Geometric and numerical repair

For unit directions, only `abs(cross(d1,d2)) <= 64*float_epsilon` uses the
constant-width cap branch. This is an arithmetic contact guard, not a physical
angular tolerance. A distinct nonparallel pair uses the general signed tangent
constraints. Explicit axis design snapping retains its separate 0.6-degree
rule and can deliberately make close directions parallel before cap fitting.

Let the unit normals be rows of `N`, with signs `s` selecting the circle side
of each line. For the observed free-circle centre `C*` and radius `r*`, compute
the signed distances `d_i = n_i dot (C* - line_anchor_i)`, then solve

```text
shift  = solve(N, r* s - d)
v      = solve(N, s)
anchor = C* + shift
C(r)   = anchor + (r-r*) v
```

The two line distances equal the signed radius by construction. Subtracting
nearby coordinates before taking a dot product preserves line-anchor and
translation invariance much better than subtracting large projected offsets.
Anchoring near the observed circle avoids cancellation between a distant
virtual apex and `r v`. The internal constraint retains its reference radius;
subsequent radius changes relocate the centre and angular sweep witness from
that same reference. Existing constraints referenced to radius zero remain supported.

Near parallelism, a tiny radius step can still produce a large centre step.
The approximate fit therefore stops on the represented geometric increment
`abs(delta_r) * max(1,norm(v))`, including a radius update that rounds to zero.
One exact translated-circle control formerly stopped with a 0.049596-unit
centre error after a radius increment below `1e-10`; the repaired predicate
recovers the centre within its focused test tolerance of `1e-7`.

If one radius ulp times `norm(v)` exceeds the supplied fit tolerance, the
constraint is not representable finely enough in this parameterization. The
fitter retains the free arc at that stage and attaches the existing unresolved
radius warning. It does not pretend that a nonzero taper is parallel. Later
blur correction and design equalisation keep their existing behavior; this is
not a promise to freeze every later geometry stage or a physical error bound.

## Independent checks and retained controls

The new [focused tests](../../tests/test_tapered_caps.py) pass **20 cases**:
side lengths 50–400, rigid transforms, reversed winding, cyclic starts,
equivalent line anchors, non-axis-snapped near-parallel directions, genuine
parallel caps, repeated radius changes, the early-stop reproduction and an
unrepresentable-radius control. Circumcircles, analytic area and bounds are
computed independently of production arc reconstruction. The separate existing
77 corner/fillet/fidelity tests also pass during development.

The [conditioning runner](../../studies/verification/tapered-cap-conditioning-v1.py)
retains **54 exact circle/tangent cases**, each evaluated by the repaired code
and a source-bound, in-memory radius-only stopping ablation. The
[canonical receipt](../../studies/results/tapered-cap-conditioning-v1.json)
passes all **seven population checks**, with zero method execution failures.
The current method constrains 46 cases and retains eight; all remain visible.
Its largest represented centre error is about **0.0017764 coordinate units**,
versus **0.124167** for the ablation in this declared float64 census. These are
conditional numerical results, not universal error bounds or independent
camera trials. Eleven command/failure contracts pass, including first-method
failure retention for all 54 case pairs and 108 method records.

The separate [export runner](../../studies/verification/tapered-cap-exports-v1.py)
uses independently specified circle sectors and an unequal-circle capsule.
It runs actual Profile validation, CAD extrusion, STEP re-import, DXF units and
circle checks, and SVG parsing. The
[repaired receipt](../../studies/results/tapered-cap-exports-v1.json)
passes **all eleven rows and 121 checks**, retaining hashes of **44 artifacts**.
Maximum sampled-boundary discrepancy is about **0.00099765 coordinate units**;
maximum STEP dimension discrepancy is below **9.6e-13 mm** on these exact
synthetic models. CAD construction and readback use the same installed kernel;
analytic area, dimensions and independent circle calculations supply the
separate geometric references. Six command contracts pass, including refusal
before execution and first-row failure retention with the following ten rows
still executed. Native STEP/DXF/SVG artifacts remain in the ignored local
artifact directory named by the receipt; hashes alone do not embed those files.

## Reproduce

After [workbench setup](../development.md), choose fresh destinations:

```bash
.venv/bin/python -m pytest -q tests/test_tapered_caps.py tests/test_fillet_sweep.py tests/test_fidelity_math.py
.venv/bin/python studies/verification/tapered-cap-conditioning-v1.py --output .local/tapered-conditioning-new.json
.venv/bin/python studies/verification/tapered-cap-exports-v1.py --output .local/tapered-exports-new.json --artifacts .local/tapered-exports-new
```

The export runner's optional `--source-root PATH` imports the production code
from an explicitly chosen local checkout. Point it at the preserved PR #69
checkout to replay baseline failures using the same runner. Existing outputs,
artifact directories and dangling destinations are refused; no personal photos,
server, slicer launch or model inference is needed. Reports retain source roots,
filenames and synthetic geometry; review them before sharing.

## Regression scope and remaining work

The [regression receipt](../../studies/results/tapered-cap-regression-v1.json)
binds all **168 frozen source/plan files**, verified unchanged after execution.
The full Python suite passes **1,556 tests**, with zero failures, errors or skips
in **227.76 seconds** on Python **3.12.3**. The fresh frontend typecheck/build
completed before the full suite; Ruff and new-file formatting checks pass.

All **74 browser scenarios** pass, with zero failures, skips or flaky outcomes
in **333.78 seconds**. The runner started its own freshly built local service
with server reuse disabled; process identity and working directory were verified
against this checkout. Synthetic input and assistant fixtures exercise the
existing workflows without qualifying real model advice. The generated split
preview was also visually inspected: the 80 mm source measurement stays separate
from the requested 160 mm design size. Its screenshot hash is retained in the
receipt. Native artifacts and independent runners have their own source-bound
receipts outside the 168-file suite snapshot.

This repairs two reproduced geometry/iteration errors. It does not impose a
new general forward-model-adequacy gate, qualify scalar Gaussian blur, justify
camera response/noise bounds or prove physical fit. The separate free-arc path
without constrained snapping can still change a stored radius during blur
correction while its emitted three-point arc uses line-foot endpoints; that
remaining representation/model issue is not fixed by this tapered-cap change.
The active scientific work therefore remains broader than this repair.

## Documentation coverage

The current guides and source/CI snapshot now describe the cap repair. The
complete Markdown inventory extends the preceding
[93-document record](gaussian-response-domains.md#documentation-coverage) with
this validation record. Historical test counts, standalone calibration receipts
and companion-library generated/release files retain their original bindings.

All **94 Markdown documents**, **1,456 local links**, **96 fragments** and
**155 tables** pass the structural check. Both new help paths, root `make help`
and the library's existing **19 documentation tests** pass. The regression
receipt retains the complete current documentation inventory and hashes.
