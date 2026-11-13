# Source-cell sensitivities: first frozen qualification

The first numerical run at `c47214d098a234f28784cb174429e687e799a2bf`
passes all 33 prescribed rows: 18 regular cells, four whole grids and 11
contact/endpoint/resource cases. The result concerns supplied synthetic geometry
and a continuously varied area model. No inverse optimizer, photograph capture
or physical measurement is part of this study.

The [method and API](../finite-cell-sensitivity.md) distinguish this area family
and its separate fixed linear acquisition operator from the preceding rounded
mean. The [prospective plan](../../studies/finite-cell-sensitivity-v1.json),
complete implementation, tests and runner were committed before execution.
A pre-execution runner import/population-binding correction produces the
recorded numerical source above; no earlier numerical attempt was made.

## Independent numerical comparisons

Regular controls cover six arc-only, six chord-only and six joint cells, with
different radii, normals and fractions. Every column is compared with independent
positive vertical-slice area differences at two fixed steps and quadrature
orders, and separately with boundary quadrature. The additional multiple-span
case uses the same comparisons. Centre/radius columns are multiplied by cell
pitch before these dimensionless comparisons.

| Saved comparison | Maximum observed value |
| --- | ---: |
| Candidate versus finite-step Richardson estimate | `4.565e-12` |
| Candidate versus independent boundary quadrature | `1.555e-15` |
| Noncancelling area-order allowance propagated through differences | `2.856e-12` |
| Difference between the two finite-step derivatives | `1.189e-7` |

The raw report retains every underlying area value, step, quadrature order,
column, threshold and flag. These observations do not certify the candidate
error estimates. The frozen thresholds are unchanged.

There are 58 returned API calls, including 25 invariant variants. Across those
calls, 7,823 cells have resolved derivatives, two retain `nondifferentiable`,
two retain `parameter_endpoint` and four retain `work_limit`. Required work is
7,831 cell units; performed work is 7,827. The deliberate unknowns pass their
refusal contracts, rather than being counted as accuracy successes. These are
repeated/transformed cells, not independent camera observations.

## Software and saved-only verification

The focused suite at that exact source passes **259 tests**, with runtime
warnings treated as errors. It includes the existing 145 area/acquisition
controls, the new area and linear-operator controls, and seven coupled tests.
All five geometry-to-intensity columns agree with independently perturbed
area means within their predeclared tolerances. Other controls cover zero
contrast, signed overshoot, asymmetric kernels, raw coefficient sums,
single-pixel dimensions, immutable snapshots, hashes, budgets and workspace.
The 3.17-second suite wall time is not a performance benchmark.

A separate saved-only mathematical audit passes **57,970 checks** in portable
source-ZIP mode. It accounts for all 33 rows, 58 API records, 95 independently
referenced columns, 25 variants and the ten governing source pins. It evaluates
no model, derivative, renderer or optimizer. Complete artifacts and tools are
listed in the [portable archive](../../studies/fixtures/finite-cell-sensitivity-v1/README.md).
A separate implementation/evidence review passes 8,471 saved/static checks,
including the 259-test census and numeric workspace liveness. Its conclusions
also retain the reference and identifiability limits below.

The portable README block is executed verbatim: all 14 artifact hashes verify,
the artifact auditor passes 315,826 checks and the mathematical auditor passes
57,970. The import guard records no scientific imports. All 97 repository
Markdown documents parse, with zero errors across 1,112 local links, 110 heading
links and 124 tables. Ruff checks and formatting pass for the seven new Python
files. All 736 inherited non-Markdown blobs/modes match the documentation base;
the ten governing numerical-source pins remain unchanged.

The raw report is 4,236,100 bytes, SHA-256
`d72bff9c6a7f8b96b540a006623a59f8dfcc9b969f69e97f885eca09bec7be59`.
The recorded source ZIP contains 41 exact source files plus its manifest.
All governing source hashes agree before and after the study. Existing runtime
modules, tests and previous scientific archives remain unchanged.

## Qualification limits retained after review

The frozen plan describes the linear controls as “exact/decimal.” That wording
is broader than the executed controls: the general independent stencil/adjoint
oracle uses binary64 arithmetic and `math.fsum`, with exact elementary dyadic
cases. No general Decimal/Fraction linear oracle was executed. The original
plan is preserved; the [scope clarification](../../studies/fixtures/finite-cell-sensitivity-v1/qualification-scope.json)
changes no code, threshold or outcome.

Complement variants retain candidate arrays and independently computed full-disk
reference scalar maxima, but omit the reference's per-cell arrays. Saved-only
review can recompute fraction/angle cancellation and inspect those scalar gates;
it cannot independently reconstruct the coverage/centre/radius reference maxima
without new reference evaluations. Whole-grid checks also target sums; they do
not independently qualify every cell's derivative.

All arithmetic error estimates remain noncertified. Five-query coupled controls
do not prove five-parameter rank after two brightness levels are profiled, and
no actual geometry-recovery result follows. Quantization, camera calibration,
projective acquisition, real-camera/caliper checks and physical acceptance remain
unqualified. No automatic trace/build, HTTP, preview or export integration is
introduced here. Full application/browser suites are not rerun for these
isolated developer modules; any later hosted CI belongs to its own source head.
