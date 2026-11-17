# Bounded photo-library similarity search

**Decision:** Accepted for this implementation, November 17, 2026.

## Source and fit

Intelligent-DVR-Tool's [bounded scheduler](https://github.com/bartytime4life/Intelligent-DVR-Tool/blob/9dfba23cf954f60531a7b541e5b482ee01d96c5c/edge/scheduler.py)
limits both work admission and buffered bytes, and separates partial work from
completed results. The reviewed DVR main revision was `9dfba23cf954f60531a7b541e5b482ee01d96c5c`;
the scheduler Git blob was `d1cc3ec83dccab2d7872e5b830c5dc9880e6397d`.
This change applies that resource-budget principle to this app's existing NumPy
image-feature search. It does not import cameras, tracking, detector weights or DVR services.

## Problem and decision

The old nearest-neighbour search compared 2,048 query rows against *all* N photos
at once. At the configured 250,000-photo ceiling, its float32 score matrix alone
would occupy 2,048,000,000 bytes, before partition indices and other temporaries.
Cancellation during organization was also ignored until regrouping had finished.

Block both query rows (256) and candidates (2,048), retaining only each row's best
k between candidate blocks. The default score matrix is now at most 2 MiB;
partition/merge scratch is also block bounded. The input feature matrix, output
N-by-k arrays and other library stages still consume memory. This does not certify
250,000-photo capacity: exact matching still performs quadratic comparisons.

The search preserves exact top-k selection over its computed float32 scores.
Equal scores use ascending source-row order, including ties at the selection
boundary. Floating-point scores extremely close to each other can differ with
BLAS blocking; the numerical tests separate exact binary ties from score tolerances.
Inputs with non-finite features or invalid block sizes are refused.

Cancellation is checked during feature validation and before each candidate
block. A cancelled search publishes no partial row. The library also checks
before writing groups, during writes and before commit; cancellation rolls the
whole regrouping transaction back, retaining the previously saved organization.
The existing bounded group-splitting calculation is not interrupted inside an
individual group, so cancellation latency is not a real-time guarantee.

Approximate-neighbour indexes were considered but would change matching recall,
introduce another dependency and require model-specific quality calibration.
The selected approach retains the current exact matching and grouping contracts.

## Reproduce

```sh
.venv/bin/pytest -q tests/test_bounded_search.py tests/test_vision.py tests/test_library.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/benchmark_photo_search.py
```

The [generated-vector receipt](validation/bounded-photo-search.json) compares the
previous implementation with the blocked search for 4,096 vectors of 64 components,
12 neighbours, seed 418. NumPy-traced scratch peaks exclude the common input matrix;
they are not process RSS or a whole-application memory measurement. Both searches
returned identical neighbours and scores within 1e-6. Timings are one local
microbenchmark, not a claim that the new search is always faster. No user pictures,
model inference, downloads or physical-object accuracy checks are involved.

Final targeted validation: **79 passed, 1 skipped** in 12.24 s for the command
above, plus Ruff and whitespace checks. The skip is the optional real vision-model
check. HTTP checks were run outside the restricted execution sandbox after its
in-process HTTP tests stalled; the ordinary local runtime completed them.
