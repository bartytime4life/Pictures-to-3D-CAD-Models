# Actual PNG cost after the inward construction

The first paired test at research source `98fb1ae` exactly reproduces the
saved incumbent but **rejects the predetermined inward candidate**. Actual
training cost rises from **0.302031169350812 to 0.40923713513984694**. Source
cell 62 reaches the intended code 92, while protected cell 33 changes from
106 to 105. The [complete result and evidence](validation/finite-acquisition-inward-literal.md)
retain the negative outcome, both evaluations and all original inventory rows.

This is separate local research. Main has no five-geometry-parameter
acquisition-aware recovery fitter, literal-test runner, HTTP mode or workbench
control for it. The original full recovery
study remains **11/12 matched passes, exit 1**. No camera, geometry, print-fit
or physical-accuracy qualification follows from the paired test.

## What this test adds

The earlier [inward construction](finite-acquisition-inward-margin.md) checks
one local linear model and the floating-point representation of its proposed
parameters. All 128 new corners pass its five unchanged gates. Those checks
do not evaluate the nonlinear geometry-to-image pipeline.

The separate 112-input admission fixes **corner index 0** before execution.
It compares that exact seven-parameter tuple with its saved enclosing
incumbent, using each tuple's own five geometry parameters and two brightness
levels. It does not choose another corner, refit brightness, rerank events,
solve another QP or substitute a later best-fit record for the incumbent.

The runner binds all 112 governing source files, the previous report and two
diagnostics, and all 106 original saved artifacts before importing its backend
dependencies. It checks those bindings again after execution. The inventory
retains all 24 rows and 17 fit files: 16 have no qualifying certificate and
one supplies the eligible paired context. Missing qualifications remain
explicit; they are not additional literal trials.

## Identical pipeline and training observations

Each forward evaluation calls the unchanged `segment_cell_coverage` and
`acquisition_mean` APIs with the saved geometry, source grid, optical kernel,
affine sampling, post-kernel and original ordered training queries. It uses
the literal sRGB8 encode/decode path. The result retains raw coverage and all
seven acquisition stages: coverage, source linear, optical linear, encoded,
decoded linear, rectified and final. It also retains the training prediction,
raw residual, weighted residual, cost and work metadata.

The replayed incumbent must reproduce the archived input binding, prediction,
raw and weighted residuals, cost, and optical/encoded/decoded stage snapshots
exactly. All nine qualification checks pass in the first pair. This verifies
replay consistency with the saved experiment; it is not independent
qualification of that experiment's forward model.

## Actual training cost decides acceptance

For the original ordered training target `y`, prediction `v` and supplied
residual multipliers `w`, the operational calculation is

```text
raw_i = y_i - v_i
r_i   = w_i * raw_i
n     = math.hypot(*r)
C     = n * n
accept only if C_candidate < C_replayed_incumbent
```

The weights multiply residuals directly; the runner does not replace them
with square roots or infer a noise model. Inputs and intermediate values
must be finite, weights positive, and the cost calculation must pass its
overflow and nonzero-underflow guards. A tie is not an improvement. No
reference geometry, reserved residual or source-code pattern selects or
vetoes a strict cost improvement. Code changes are retained as diagnostics.

The actual first pair is complete and qualified, with no protocol error,
but the candidate has higher cost. Its status is `complete_no_improvement`,
exit 1. This is a completed negative scientific result, not a missing run or
an incomplete baseline replay.

## Reserve both evaluations before the first call

The runner holds and charges the entire pair before its first forward call.
It retains both attempts and gives no work refund for a failed phase. For
this 13 by 13 source and output, the pair adds **2 evaluations, 338 cell
units and 10,478 stage units**. The aggregate is **992 / 135,369 / 54,531,024**,
below the unchanged caps **2,048 / 1,000,000 / 100,000,000**.

These units describe the declared shared-work ledger, not elapsed time or
total process memory. The aperture API does not report its own cell counter;
the caller charges 169 cells per attempt. Each successful acquisition call
reports 5,239 stage units. The first pair completes two aperture and two
acquisition calls, with no opaque failed work. This is standalone probe
accounting; it does not integrate the proposal into the original fitter.

## Why local feasibility did not transfer

The independent saved-data audit compares retained local optical predictions
with retained actual optical stages. Source indices are zero-based row-major
indices in the 13 by 13 source grid.

| Source cell | Saved local prediction | Actual optical value | Actual minus local | Code outcome |
| --- | --- | --- | --- | --- |
| 33 | 36.38638305664528 | 36.38624954223633 | -0.00013351440895092992 | Protected 106 becomes 105 |
| 62 | 27.446351528163046 | 27.447145462036133 | +0.000793933873087127 | Selected 93 becomes target 92 |

Both local predictions are only about `4.6e-12` inside their respective
declared band boundaries. All 169 saved local predictions pass those bands;
167 actual optical values pass. Cell 62 misses the deliberately narrowed
**central-half proposal slice**, while still encoding to its intended full
code 92. Cell 33 genuinely crosses the protected code boundary. The maximum
absolute actual-minus-local difference is `0.0033637480281960563` at cell 80;
that cell still remains inside its band.

The discrepancy may contain geometry-linearization remainder, mixed
geometry/brightness terms and staged floating-point error. This comparison
does not isolate their contributions or provide a global remainder bound. A stronger
rational representation proof alone does not cover this observed mismatch.
The 108-input construction and its 128 passing corners remain valid within
their original local-model scope.

## Remaining engineering work

A model reanchored through the rejected trial's actual optical observation is
an unimplemented proposal. It has no admitted candidate, new solve, actual
cost result or convergence guarantee. Any future correction needs a separate
reviewed admission and source freeze before execution, the original bounds,
training-only selection and shared caps, explicit nonlinear validation, and
strict actual-cost acceptance. The rejected trial cannot become the accepted
incumbent by relabeling it.

Runtime integration would then require another complete original 24-case
protocol under the original targets. The paired test neither retests that
protocol nor changes its failed 11/12 result. Installed runtime, deployment,
native slicer behavior and physical CAD/print acceptance remain unverified
by this research.
