"""Generated-vector scratch-memory comparison; no pictures, models or downloads.

Run with OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/benchmark_photo_search.py.
NumPy allocation peaks are traced separately, excluding the common feature matrix.
This is a numerical microbenchmark, not model quality or whole-library capacity.
"""

import json
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import vision_math


def previous(matrix, count):
    total = len(matrix)
    indices = np.zeros((total, count), np.int64)
    values = np.zeros((total, count), np.float32)
    for start in range(0, total, 2048):
        stop = min(start + 2048, total)
        scores = matrix[start:stop] @ matrix.T
        scores[np.arange(stop - start), np.arange(start, stop)] = -np.inf
        part = np.argpartition(-scores, count - 1, axis=1)[:, :count]
        selected = np.take_along_axis(scores, part, axis=1)
        order = np.argsort(-selected, axis=1, kind="stable")
        indices[start:stop] = np.take_along_axis(part, order, axis=1)
        values[start:stop] = np.take_along_axis(selected, order, axis=1)
    return indices, values


def main():
    matrix = vision_math.unit(np.random.default_rng(418).normal(size=(4096, 64)))
    results, outputs = {}, {}
    for name, search in (("previous", previous), ("blocked", vision_math.neighbours)):
        tracemalloc.start()
        started = time.perf_counter()
        outputs[name] = search(matrix, 12)
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results[name] = {"seconds": round(elapsed, 4), "peak_traced_bytes": peak}
    same = np.array_equal(outputs["previous"][0], outputs["blocked"][0])
    close = np.allclose(outputs["previous"][1], outputs["blocked"][1], atol=1e-6)
    print(json.dumps({"schema": "picad-search-benchmark-v1", "input": "generated unit vectors",
                      "seed": 418, "rows": 4096, "dimensions": 64, "neighbours": 12,
                      "numpy": np.__version__, "results": results,
                      "same_neighbours": same, "scores_within_1e-6": close}, indent=2))
    return 0 if same and close else 1


if __name__ == "__main__":
    raise SystemExit(main())
