# Nonnegative shadow solve: optimality repair

Baseline: main `40cfbe480d603976264c04c3b3031146fd1e8a01`, November 16, 2026.
The shadow model's optical assumptions and prior-selection heuristic remain
conditional. This repair addresses the minimization of its existing objective.

## Reproduced defect and independent answer

For normal matrix `M` and right-hand side `b`, the fitted objective is
`xᵀ M x / 2 - bᵀ x`. The first six coefficients describe unconstrained quadratic
paper light; subsequent kernel coefficients must be nonnegative. For SPD `M`,
the KKT conditions suffice for a global minimum: free gradients vanish,
bounded variables and their gradients are nonnegative, and their products vanish.
See [SciPy's primary NNLS documentation and Lawson–Hanson reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.nnls.html).

The old routine solved an unconstrained system, permanently removed all negative
kernel nodes, and repeated at most 60 times. It did not test the gradient at
removed nodes or release them. A feasible result can therefore be suboptimal:

```text
M = [[15, 11, -1], [11, 26, -24], [-1, -24, 35]]
b = [5, 4, -1]
old x = [1/3, 0, 0]
old gradient = [0, -1/3, 2/3]
minimum x = [86/269, 5/269, 0]
minimum gradient = [0, 0, 63/269]
```

The leading principal minors of `M` are 15, 269 and 1277, so it is SPD.
The objective decreases by exactly `5/1614` at the minimum. Increasing the old
second coefficient from zero is a descent direction. Appending six independent
unbounded coordinates embeds this example in the shadow solver's mixed bounds.

## Repair and failure behavior

`shadow._nonnegative_solve` first finds a feasible point, then permits removed
nodes with negative gradient to return. A restricted Cholesky solution that crosses
a bound is approached only as far as the first bound, then solved again. Diagonal
equilibration makes the stopping test consistent across coefficient units. The
tolerance scales with floating precision, dimension and equation magnitude.
The first six light coefficients remain unbounded.

The numerical iteration budget and stationarity checks raise `LinAlgError` when
unavailable. `fit_paper_light` then returns `used=False` with
`reason=shadow_solve_failed`, retaining the existing per-profile line path.
No unfinished kernel is presented as an adequate fitted shadow. A KKT residual
does not certify normal-equation conditioning or physical model accuracy.

## Checks and paired development scenes

Seven new test cases cover the exact counterexample; 180 seeded problems against
exhaustive enumeration of all 32 constrained faces, with 0, 2 or 6 unbounded
coefficients; units and global objective scales over twelve orders of magnitude;
iteration exhaustion; and public shadow-fit fallback. The oracle uses NumPy's
general linear solve, not the production Cholesky routine.

`scripts/shadow_solver_audit.py` substitutes only the former/new solver on six
fixed scenes, using the existing synthetic scene and edge-measurement helper.
This isolates an implementation change; it is not independent optics or a
real-camera experiment. The [saved replay](evidence/shadow-kkt-20261116/replay.json)
includes source hashes, every outcome, per-solve dual residuals, selected priors
and timings. Timings are indicative local measurements.

For the first five scenes (4 px/mm, 3 px blur), the maximum edge movement between
solvers is under 0.0002 px. Actual shadow normal systems also expose the defect:
the old maximum scaled dual violation reaches `1.85e-5`; repaired values are
at most `9.4e-12` on those five scenes. This small positional effect must not be
described as a large accuracy improvement.

The sixth, shadow-free scene at 5.4 px/mm and 4 px blur exposes prior-selection
sensitivity. The selected weight changes from 0.3 to 0.03. Its right-edge error
improves from +0.0022044 to +0.0004510 px, while its left-edge error worsens from
−0.0105937 to −0.0112423 px. Better minimization does not guarantee every
downstream feature improves.

The initial regression run failed the old `abs(model-line)<0.002` assertion on
that right edge: the correction is 0.0033639 px, towards the independently known
edge. The test now measures `abs(model)<abs(line)+0.002`: at most the original
0.002 px allowance for worsening true geometric error. This permits a helpful
correction without increasing that worsening allowance. The paired left-edge
regression is retained above, and the other shadow/contrast checks stay in place.

Reproduce from the repository root:

```bash
.venv/bin/python -m pytest -q tests/test_shadow_optimality.py -W error::RuntimeWarning
.venv/bin/python -m scripts.shadow_solver_audit /tmp/shadow-replay.json
```

This solver change does not replace the normal-line light integral with a
two-dimensional optical model, establish physical uncertainty or qualify a print.
