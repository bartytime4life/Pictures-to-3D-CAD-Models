"""Exact generated-vector oracles, bounded score blocks and transactional cancellation."""

import numpy as np
import pytest

from backend import vision_math


@pytest.mark.parametrize("query_block,candidate_block", [(1, 1), (7, 3), (8, 17), (100, 100)])
@pytest.mark.parametrize("count", [0, 1, 5, 40])
def test_blocked_search_equals_dense_oracle(query_block, candidate_block, count):
    rng = np.random.default_rng(13)
    # Binary-exact unit features keep the tie oracle independent of BLAS rounding.
    vectors = rng.choice(np.array([-0.25, 0.25], np.float32), (31, 16))
    # Exact duplicates and zero vectors force cutoff ties, including negative scores.
    vectors[4:8] = vectors[0]
    vectors[12:15] = 0
    scores = vectors @ vectors.T
    np.fill_diagonal(scores, -np.inf)
    expected = np.lexsort((np.broadcast_to(np.arange(31), scores.shape), -scores), axis=1)[:, :min(count, 30)]
    indices, values = vision_math.neighbours(vectors, count, query_block, candidate_chunk=candidate_block)
    assert np.array_equal(indices, expected)
    assert np.allclose(values, np.take_along_axis(scores, expected, axis=1), atol=1e-6)
    assert not np.any(indices == np.arange(31)[:, None])


def test_largest_score_allocation_has_both_dimensions_bounded(monkeypatch):
    vectors = vision_math.unit(np.random.default_rng(4).normal(size=(103, 16)))
    shapes = []
    multiply = np.matmul

    def measure(a, b):
        result = multiply(a, b)
        shapes.append(result.shape)
        return result

    monkeypatch.setattr(np, "matmul", measure)
    progress = []
    vision_math.neighbours(vectors, 4, 7, candidate_chunk=11, progress=lambda d, t: progress.append((d, t)))
    assert all(rows <= 7 and columns <= 11 for rows, columns in shapes)
    assert sum(rows * columns for rows, columns in shapes) == 103**2
    assert progress[-1] == (103, 103)


def test_cancel_between_candidate_blocks_does_not_publish_partial_rows(monkeypatch):
    vectors = np.eye(12, dtype=np.float32)
    multiply = np.matmul
    blocks = 0

    def cancel_after_block(a, b):
        nonlocal blocks
        blocks += 1
        return multiply(a, b)

    monkeypatch.setattr(np, "matmul", cancel_after_block)
    progress = []
    with pytest.raises(vision_math.SearchCancelled):
        vision_math.neighbours(vectors, 3, 4, candidate_chunk=2,
                               cancelled=lambda: blocks >= 2, progress=lambda d, t: progress.append(d))
    assert blocks == 2 and progress == []


@pytest.mark.parametrize("matrix", [np.zeros(3), [[float("nan")]], [[float("inf")]]])
def test_invalid_features_are_refused(matrix):
    with pytest.raises(ValueError, match="finite row matrix"):
        vision_math.neighbours(matrix, 2)


@pytest.mark.parametrize("chunk,candidate", [(0, 4), (2, 0), (-1, 1), (1, 1.5)])
def test_invalid_budgets_are_refused(chunk, candidate):
    with pytest.raises(ValueError, match="block sizes"):
        vision_math.neighbours(np.eye(3), 2, chunk, candidate_chunk=candidate)


def test_top_matches_breaks_ties_by_source_row():
    matrix = np.ones((50, 3), np.float32)
    indices, _ = vision_math.top_matches(matrix, matrix[0], 7)
    assert indices.tolist() == list(range(7))
