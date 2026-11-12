# Common-response calibration: exact controls and limits

This developer candidate is based on published documentation PR #65 at
`8b9c6a803b89d05daee38b7f48c079f70c76de3a`. It adds exact conditional response
consistency, a strict decimal-string CLI, a finite synthetic edge/calibration study
and independent graph/certificate verification. Production tracing, API, UI,
geometry, dependencies and prior study artifacts retain their baseline bytes.
The Makefile adds only a developer study target. The primary checkout is preserved.

The [guide](../response-calibration.md) defines exact inputs, common slopes,
tight marginal bands, shared witnesses, contradictions and refusals. The
[raw-source fitter](../raw-source-fit.md) is a separate conditional objective;
this work neither inverts a response nor reuses a noise model after a nonlinear
transformation.

## What is mathematically established

Sorted exact knot constraints and common lower/upper secant bounds form a chain
of convex interval constraints. Duplicate abscissae refer to the same function
value. Forward/backward rational reachability gives tight knot marginals and
between-knot slope-cone envelopes. One piecewise-linear witness verifies common
existence on the declared domain. An indexed strict inequality verifies
incompatibility. Invalid types, unsupported magnitudes and finite resource limits
refuse a request without asserting mathematical incompatibility.

The independent oracle uses exact all-pairs difference-constraint closure on the
**original observation variables**, including equality edges for duplicate inputs.
It does not import production numeric parsing or chain recurrences. The
[oracle source](../../studies/verification/response-calibration-oracle-v1.py) and
[canonical graph receipt](../../studies/results/response-calibration-oracle-v1.json)
retain all checks. All **343
mathematical cases** and **20 schema/resource controls** pass, with zero failures:
151 mathematical cases are compatible and 192 are incompatible. The population
retains 13 named, 13 paired, 256 seeded, three edge-gauge, 29 permutation and 29
duplicate variants. Compatible witnesses, exact tight knot/query intervals and
contradiction source provenance are checked separately. These are declared
development controls, not unseen camera evaluation.

## Complete finite edge/calibration comparison

The [plan](../../studies/response-calibration-v1.json) declares 25 source positions,
65 candidate offsets from −0.5 to +0.5 true sigma in steps of 1/64, six supplied
calibration regimes and three deterministic observation halfwidths. Every one of
**1,170 whole-profile candidates** is retained in
[the result](../../studies/results/response-calibration-v1.json). Each candidate
uses one common response; compatibility is not assembled from independent
pointwise response choices. The 18 comparisons reuse one 25-point truth profile;
these are 1,170 candidate hypotheses, not independent scenes or camera captures. Every compatible candidate keeps an exact common
witness; every incompatible candidate keeps its indexed contradiction.

The true normalized response is `h(u) = u + 0.15*u*(1-u)`. Its derivative on
`[0,1]` lies in `[0.85,1.15]`; those slope bounds are supplied only in the named
regimes. Endpoint anchors select normalized coordinates. The five-patch regimes
also supply knots at 0.25, 0.5 and 0.75, with exact values or halfwidth 1/128.
Gaussian CDF evaluations use float64 `erfc` and are then **frozen as exact binary
rationals** for this declared experiment. They are not certified optical
probabilities. The truth and candidates share this finite CDF generator; matched
truth retention is not independent validation of a physical Gaussian model.

| Supplied calibration | Compatible / 65 at output halfwidth 0 | At 1/1024 | At 1/128 |
| --- | --- | --- | --- |
| Normalized endpoints only, nondecreasing | 65 | 65 | 65 |
| Five exact patches, nondecreasing | 9 | 9 | 9 |
| Five bounded patches, nondecreasing | 9 | 9 | 9 |
| Five bounded patches and slopes 0.85–1.15 | 2 | 2 | 5 |
| Five exact patches and slopes 0.85–1.15 | 1 | 1 | 3 |
| Incorrect identity patches and slopes 0.85–1.15 | 0 | 0 | 3 |

All 15 correctly specified comparisons retain the zero offset. Under bounded
patches/slopes and the two smaller output bands, the represented alternatives
are `[-1/64,0]`; the asymmetry is retained. With exact patches/slopes and zero
output width, only zero is represented as compatible. **One compatible grid
point is not a continuous uniqueness certificate.** An empty compatible grid
is not proof that the entire continuous offset domain is infeasible.

The wrong identity calibration excludes truth in all three comparisons. At the
loosest band it retains the shifted offsets `[-7/64,-3/32,-5/64]`. Tight-looking
results can therefore reflect incorrect supplied calibration. These bands are
deterministic experimental assumptions, not camera-noise estimates or confidence
levels. All 266 compatible witnesses and 904 contradictions remain visible.
The [replayable independent certificate audit](../../studies/verification/response-calibration-study-audit-v1.py)
checks all original intervals and all pairwise slope bounds for each witness,
reconstructs every contradiction from its source indices, and verifies the full
population and named controls. Its [canonical receipt](../../studies/results/response-calibration-study-audit-v1.json)
passes **1,319 checks**, with zero failures and all 1,170 candidate rows retained.
It uses only archived inputs, exact arithmetic and independent formulas; it calls
no production calibration function. Injected bad-witness checks retain the failed
row and continue. Duplicate JSON keys are refused rather than silently hiding
overwritten observations. The earlier pre-hardening audit is preserved locally;
this stricter parsing does not change any canonical numerical outcome.

A separate linear-response fit of this nonlinear source profiles two brightness
levels and moves the edge by about **−0.08928 sigma**. It uses an identity source
projection, supplied unit deviations and a four-raw-pixel Gaussian sigma. It is a
model-mismatch control with a different conditional objective, not a performance
ranking against exact interval feasibility or measured-photo accuracy. Its flat,
plateau, tie, endpoint, rank, work and arithmetic problem flags are all clear;
that numerical result still does not identify a correct physical response.

## Ambiguities and stage counterexamples

For an affine Gaussian profile `h(Phi((x-e)/sigma))`, define

```text
h_prime(u) = h(Phi((sigma_prime/sigma)*Phi_inverse(u) + (e_prime-e)/sigma))
```

Substitution preserves the entire profile. The inner Gaussian reparameterization
extends to fix 0 and 1; defining `h_prime(0)=h(0)` and `h_prime(1)=h(1)` preserves
normalized anchors without requiring endpoint continuity of a generic `h`.
With a strictly increasing `h` and positive spreads the alternative is
also strictly increasing; nonidentification is not caused only by flat responses.
Nine finite offset/spread controls retain exact declared-input witnesses. Their
floating evaluation of the analytic identity agrees to about 1.81e-14; that is
not a certified optical error bound. Any fixed later digital operator preserves
identical source fields. This gauge is restricted to the affine straight-profile
model and is not asserted for arbitrary projective two-dimensional geometry.

Named controls additionally retain:

- Marginal versus common response: `.4→.8` and `.6→.2` each fit a separate query
  band, yet together contradict one nondecreasing function.
- Spatial response: two individually valid curves disagree at the same input;
  a common scalar response fails. The failure does not diagnose its physical cause.
- Uncertain input: replacing an allowed `[0,2]` input by its midpoint rejects a
  configuration with a valid assignment at 2. No uncertain-input solver or
  guarantee for every allowed assignment is implemented.
- Exact scalar 8-bit quantization: the saved point at input 1/2 conflicts with
  its known response value, while its half-step closed bin cover retains it.
  The cover is conservative at ties-to-even endpoints; it is not always the exact
  quantizer preimage and is not a model of phone sRGB processing.
- Actual Keys sampling: response before sampling gives 0.5, while applying the
  square afterward gives 0.25. A signed Keys sample can be −0.0625, outside a
  `[0,1]` source-response domain.
- Actual channel/mix path: equal original linear channel mixtures of 127.5 become
  127.5 versus about 63.79036 after per-channel square response, 8-bit sRGB storage,
  decoding and fixed mixing. One scalar post-mix response cannot explain both.

These controls do not justify inverse correction, clipping signed samples or
reusing pre-inversion independent Gaussian deviations. Calibration uncertainty
is shared across observations. Unknown exposure/levels, channel or spatial tone
mapping, input uncertainty, PSF, geometry and real noise remain external work.

## Reproduce

```bash
make response-calibration-study OUTPUT=.local/response-study-new.json
.venv/bin/python studies/verification/response-calibration-oracle-v1.py --output .local/response-oracle-new.json
.venv/bin/python studies/verification/response-calibration-study-audit-v1.py --run studies/results/response-calibration-v1.json --output .local/response-study-audit-new.json
.venv/bin/python -m pytest -q tests/test_response_calibration.py tests/test_response_calibration_cli.py
```

The CLI example is in the [guide](../response-calibration.md#run-an-exact-example).
All result destinations must be new. These commands need the root environment
but no running server, photograph, native application or model download.
The study retains its plan, exact finite inputs, every candidate, source hashes,
Git dirty-file context, units and runtime versions. Runtime is recorded for that
small experiment and does not establish whole-photo capacity.

## Source binding and regression

The source/plan hashes are checked before and after each canonical execution.
The recorded Git revision is the published parent above, with dirty/untracked
implementation context. It does not assert the new implementation already exists
in that parent commit. Source hashes bind the actual tested implementation.

| File | SHA-256 |
| --- | --- |
| [backend/response_calibration.py](../../backend/response_calibration.py) | `b8a1c4acf8b5d70db3c3de10c9c2e1972af3bbff7f82193bb1f2e9fdc9a56aa4` |
| [backend/raw_source_fit.py](../../backend/raw_source_fit.py) | `6a877bc15759076adf95dbbb521c04d110b20e8ed397637148c2e87b3ba8b6af` |
| [backend/profile_observations.py](../../backend/profile_observations.py) | `7eee8b71fc9024cb5c8453ec67aab75f2c21c8c77e975c1fba41b1e3be9f873b` |
| [backend/sheet.py](../../backend/sheet.py) | `a086d7216256726a0e392bd98cbdb1274f5cb5eb096802c17c805349a7747e31` |
| [backend/tone.py](../../backend/tone.py) | `88a9d8937c27c0793d650e1c8762c0acb24c17de710a6c6b20992929360f50ee` |
| [scripts/response_calibration.py](../../scripts/response_calibration.py) | `cd21ba5da2b4604f72aaf8204f373337411373798dc071aa0e11d4f68a2c7412` |
| [scripts/response_calibration_study.py](../../scripts/response_calibration_study.py) | `0afed240a3cddc2f6400e35d77b9700313c1a6ecb5f18bd9984496376392a926` |
| [studies/response-calibration-v1.json](../../studies/response-calibration-v1.json) | `7671ac6777d7e698ac478a873ce4da9bffdcdc0718382a98f7f87c12f77243bf` |

The full Python suite passes **1,324 tests** with zero failures, errors or skips
in 226.63 seconds. The [regression receipt](../../studies/results/response-calibration-regression-v1.json)
binds **152 frozen source/plan files**, verified unchanged after execution.
The 51 new focused cases include exact independent extrema/graph checks, parsing,
provenance, bounded resources, CLI output/refusal and existing-file preservation.
All 139 pre-existing backend/frontend/script/test files retain their baseline
bytes; the new modules are not imported by production. The separate replayable
study audit is bound independently of this full-suite snapshot. Its final source
SHA-256 is `39f7baf5387c414a6f87d9e06adbe13711ade1c310844b30d4c3b54bff626ff2`.
Fresh frontend typecheck/build and Ruff pass. No fresh browser run or physical
qualification is claimed; exact-head hosted results are recorded separately in
[project status](../project-status.md#evidence-by-scope).

## Documentation coverage

The repository-wide audit covers the earlier [86-document inventory](documentation-latest.md#coverage-inventory)
plus the new [response guide](../response-calibration.md) and this validation
record. Historical receipts retain their dates and source bindings; library
generated-reader inputs and outputs are unchanged. All **88 Markdown documents**,
**1,234 local links**, **79 fragments** and
**142 tables** pass the repository-wide check. The existing companion-library
suite passes **19 documentation tests**, separately from product regressions.
No generated library build, archive or release metadata is refreshed.
