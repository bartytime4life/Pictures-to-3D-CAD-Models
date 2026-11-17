"""Numerical steps of the photo library's vision features. NumPy only.

This module is imported by the workbench (``backend.vision``, ``backend.library``) and by
the separate model process (``backend/vision_worker.py``), which runs under another
Python with PyTorch. It must therefore import nothing but NumPy and the standard
library.

Subject finding
    A DINOv3 Vision Transformer turns a picture into one feature vector per 16 x 16 pixel
    patch. On a plain or evenly textured surface those vectors change only slowly with
    position, while the vectors on an object differ from the surface around it. The
    surface is therefore modelled as a *plane in feature space*, f(x, y) = a + b x + c y,
    fitted robustly so that the object does not pull it:

    1. Iteratively reweighted least squares. Each patch's residual length r is compared
       with the residuals' median and scaled median absolute deviation (1.4826 MAD, a
       robust standard deviation); patches beyond median + 2 of those lose weight
       linearly, reaching none at 6. Patches on the
       picture's border count three times, because a part rarely covers the border.
       (Residual *lengths* of well-fitted patches cluster round a positive value in a
       space of several hundred dimensions, so they are judged against their own
       median, not against zero.)
    2. Otsu's threshold on the standardized residual gives a first, generous region.
    3. The half of that region that stands out most supplies a subject direction. A
       patch is kept when it is closer (by cosine) to that direction than to the fitted
       surface at its own position. This removes the ring of surface patches round the
       object whose features the object has coloured.
    4. The largest 4-connected region is the subject.

    The result is a patch-resolution region, never an outline: with 448-pixel inputs a
    patch is one twenty-eighth of the picture's width. Earlier rendered experiments
    informed this method; current validation scope and reproduction commands are in
    docs/validation/photo-library.md.

Matching
    A picture's *subject vector* is the mean of the patch vectors inside that region,
    scaled to unit length; its *whole-picture vector* is the model's class token. Two
    pictures are compared by the cosine of the angle between such vectors.
"""

from __future__ import annotations

import math

import numpy as np

BORDER_WEIGHT = 3.0
IRLS_STEPS = 8
SOFT_START, SOFT_END = 2.0, 6.0  # In MADs above the median residual.
MIN_SUBJECT_PATCHES = 3


def unit(vectors: np.ndarray) -> np.ndarray:
    """Scale the last axis to unit length; a zero vector stays zero."""
    v = np.asarray(vectors, dtype=np.float32)
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(norm, 1e-12)


def otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    """Otsu's threshold of a 1-D sample: the cut that maximizes between-class variance.

    Every cut inside an empty gap between two clusters separates them equally well; the
    middle of such a run of equal maxima is returned, not its first bin.
    """
    v = np.asarray(values, dtype=np.float64).ravel()
    low, high = float(v.min()), float(v.max())
    if not np.isfinite(low) or not np.isfinite(high) or high - low < 1e-12:
        return high
    hist, edges = np.histogram(v, bins=bins, range=(low, high))
    weight = np.cumsum(hist)
    centres = (edges[:-1] + edges[1:]) / 2
    mass = np.cumsum(hist * centres)
    total, total_mass = weight[-1], mass[-1]
    below, above = weight[:-1], total - weight[:-1]
    valid = (below > 0) & (above > 0)
    mean_below = np.divide(mass[:-1], below, out=np.zeros(bins - 1), where=valid)
    mean_above = np.divide(total_mass - mass[:-1], above, out=np.zeros(bins - 1), where=valid)
    between = np.where(valid, below * above * (mean_below - mean_above) ** 2, -1.0)
    best = float(between.max())
    ties = np.flatnonzero(between >= best - 1e-9 * max(abs(best), 1.0))
    return float(edges[int(ties[len(ties) // 2]) + 1])


def largest_region(mask: np.ndarray) -> np.ndarray:
    """The largest 4-connected region of a small boolean grid (flood fill)."""
    grid = np.asarray(mask, dtype=bool)
    height, width = grid.shape
    seen = np.zeros_like(grid)
    best: list[tuple[int, int]] = []
    for start_y, start_x in zip(*np.nonzero(grid), strict=True):
        if seen[start_y, start_x]:
            continue
        stack, region = [(int(start_y), int(start_x))], []
        seen[start_y, start_x] = True
        while stack:
            y, x = stack.pop()
            region.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < height and 0 <= nx < width and grid[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(region) > len(best):
            best = region
    out = np.zeros_like(grid)
    if best:
        ys, xs = zip(*best, strict=True)
        out[list(ys), list(xs)] = True
    return out


def _plane_design(grid: int) -> tuple[np.ndarray, np.ndarray]:
    yy, xx = np.mgrid[0:grid, 0:grid]
    scale = max(grid - 1, 1)
    x = (xx.ravel() / scale - 0.5) * 2
    y = (yy.ravel() / scale - 0.5) * 2
    design = np.stack([np.ones_like(x), x, y], axis=1).astype(np.float32)
    border = ((xx == 0) | (yy == 0) | (xx == grid - 1) | (yy == grid - 1)).ravel()
    return design, border


def subject_regions(patches: np.ndarray) -> np.ndarray:
    """Find each picture's subject. ``patches`` is B x (g*g) x C; returns B x g x g bool.

    A picture whose features show no separable region (a blank page, a texture that
    fills the frame) returns an empty region.
    """
    tokens = np.asarray(patches, dtype=np.float32)
    if tokens.ndim != 3:
        raise ValueError("Patch features must be batch x patches x channels.")
    batch, count, _ = tokens.shape
    grid = math.isqrt(count)
    if grid * grid != count or grid < 3:
        raise ValueError("Patch features must form a square grid of at least 3 x 3.")
    features = unit(tokens)
    design, border = _plane_design(grid)
    prior = np.where(border, BORDER_WEIGHT, 1.0).astype(np.float32)
    weight = np.tile(prior, (batch, 1))
    ridge = 1e-6 * np.eye(3, dtype=np.float32)
    for _ in range(IRLS_STEPS):
        # Contiguous operands keep every product in BLAS; a transposed view would not.
        weighted = np.ascontiguousarray((design[None] * weight[..., None]).transpose(0, 2, 1))  # B x 3 x T
        normal = np.matmul(weighted, design) + ridge  # B x 3 x 3
        moment = np.matmul(weighted, features)  # B x 3 x C
        coefficient = np.linalg.solve(normal, moment)  # The fitted surface is design @ coefficient.
        # Residual lengths without forming the surface: with unit features f and surface
        # s = A c, |f - s|^2 = 1 - 2 f.s + |s|^2, where f.s = sum_i A_i (f . c_i) and
        # |s|^2 = A (c c^T) A^T. Only B x T x 3 products are needed.
        along = np.matmul(features, np.ascontiguousarray(coefficient.transpose(0, 2, 1)))  # B x T x 3: f . c_i
        dot = np.einsum("ti,bti->bt", design, along)  # f . s
        gram = np.matmul(coefficient, coefficient.transpose(0, 2, 1))  # B x 3 x 3
        surface_square = np.einsum("ti,bij,tj->bt", design, gram, design)  # |s|^2
        residual = np.sqrt(np.maximum(1 - 2 * dot + surface_square, 0))
        median = np.median(residual, axis=1, keepdims=True)
        mad = 1.4826 * np.median(np.abs(residual - median), axis=1, keepdims=True) + 1e-9
        z = (residual - median) / mad
        weight = (np.clip(1 - (z - SOFT_START) / (SOFT_END - SOFT_START), 0, 1) * prior).astype(np.float32)
    # Cosine of each patch to the fitted surface at its own position: f . s / |s|.
    to_surface = dot / np.sqrt(np.maximum(surface_square, 1e-12))
    regions = np.zeros((batch, grid, grid), dtype=bool)
    for b in range(batch):
        clipped = np.clip(z[b], 0, np.percentile(z[b], 99.5))
        first = clipped > otsu_threshold(clipped)
        if first.sum() < MIN_SUBJECT_PATCHES or first.all():
            continue
        core = first & (clipped >= np.median(clipped[first]))
        direction = features[b][core].mean(axis=0)
        direction /= max(float(np.linalg.norm(direction)), 1e-12)
        closer = features[b] @ direction - to_surface[b]
        region = largest_region((closer > 0).reshape(grid, grid))
        if MIN_SUBJECT_PATCHES <= region.sum() < count:
            regions[b] = region
    return regions


def subject_vectors(patches: np.ndarray, regions: np.ndarray) -> np.ndarray:
    """Unit mean patch vector inside each region; the whole picture when a region is empty."""
    tokens = np.asarray(patches, dtype=np.float32)
    inside = np.asarray(regions, dtype=np.float32).reshape(tokens.shape[0], -1)
    empty = inside.sum(axis=1) == 0
    inside[empty] = 1.0
    pooled = np.einsum("btc,bt->bc", tokens, inside) / inside.sum(axis=1, keepdims=True)
    return unit(pooled)


def region_box(region: np.ndarray) -> tuple[float, float, float, float] | None:
    """Bounding box of a region as fractions of the picture (x0, y0, x1, y1), or None."""
    grid = np.asarray(region, dtype=bool)
    ys, xs = np.nonzero(grid)
    if not ys.size:
        return None
    height, width = grid.shape
    return (
        float(xs.min() / width),
        float(ys.min() / height),
        float((xs.max() + 1) / width),
        float((ys.max() + 1) / height),
    )


def top_matches(matrix: np.ndarray, query: np.ndarray, count: int) -> tuple[np.ndarray, np.ndarray]:
    """Rows of a unit-vector ``matrix`` most similar to ``query`` (cosine), best first."""
    scores = np.asarray(matrix, dtype=np.float32) @ np.asarray(query, dtype=np.float32)
    count = min(count, scores.size)
    if count <= 0:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.float32)
    chosen = np.argpartition(-scores, count - 1)[:count]
    chosen = chosen[np.argsort(-scores[chosen], kind="stable")]
    return chosen, scores[chosen]


def neighbours(matrix: np.ndarray, count: int, chunk: int = 2048, progress=None) -> tuple[np.ndarray, np.ndarray]:
    """Each row's ``count`` most similar other rows. Returns (indices, cosines), N x count.

    Computed in blocks of ``chunk`` rows, so memory stays at chunk x N values however
    large the library is. ``progress(done, total)`` is called after each block.
    """
    vectors = np.ascontiguousarray(matrix, dtype=np.float32)
    total = vectors.shape[0]
    count = max(0, min(count, total - 1))
    indices = np.zeros((total, count), dtype=np.int64)
    cosines = np.zeros((total, count), dtype=np.float32)
    if count == 0:
        return indices, cosines
    for start in range(0, total, chunk):
        stop = min(start + chunk, total)
        scores = vectors[start:stop] @ vectors.T
        scores[np.arange(stop - start), np.arange(start, stop)] = -np.inf  # Not its own neighbour.
        part = np.argpartition(-scores, count - 1, axis=1)[:, :count]
        part_scores = np.take_along_axis(scores, part, axis=1)
        order = np.argsort(-part_scores, axis=1, kind="stable")
        indices[start:stop] = np.take_along_axis(part, order, axis=1)
        cosines[start:stop] = np.take_along_axis(part_scores, order, axis=1)
        if progress:
            progress(stop, total)
    return indices, cosines


def linked_groups(indices: np.ndarray, cosines: np.ndarray, threshold: float) -> np.ndarray:
    """Group rows joined by *mutual* neighbour links at or above ``threshold``.

    A link i-j counts only when j is among i's listed neighbours, i is among j's, and
    their cosine reaches the threshold. Groups are the connected components of those
    links (union-find). Requiring the link from both sides stops one picture that
    resembles many others from chaining unrelated groups together. Returns one label
    per row; rows with no link get a label of their own.
    """
    total = indices.shape[0]
    parent = np.arange(total)

    def find(node):
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != root:
            parent[node], node = root, parent[node]
        return root

    listed = [set(row.tolist()) for row in indices]
    for i in range(total):
        for j, cosine in zip(indices[i].tolist(), cosines[i].tolist(), strict=True):
            if j > i and cosine >= threshold and i in listed[j]:
                a, b = find(i), find(j)
                if a != b:
                    parent[max(a, b)] = min(a, b)
    return np.array([find(i) for i in range(total)], dtype=np.int64)


SPLIT_LIMIT = 400


def split_chained(vectors: np.ndarray, labels: np.ndarray, threshold: float, limit: int = SPLIT_LIMIT) -> np.ndarray:
    """Break up groups that hold together only through a chain of links.

    Mutual links join A to B and B to C even when A and C look nothing alike, so a few
    in-between pictures can string several subjects into one group. Each group of three
    or more is therefore re-clustered on its own by average linkage: start with every
    picture alone, repeatedly merge the two clusters whose members are most alike on
    average, and stop when that average cosine falls below ``threshold``. A chain
    breaks where its two sides are, on average, not alike.

    Groups larger than ``limit`` are left whole: the method costs the cube of the group
    size. Returns new labels (the lowest row index of each resulting group).
    """
    unit_vectors = np.asarray(vectors, dtype=np.float32)
    out = np.asarray(labels).copy()
    for group in np.unique(out):
        members = np.flatnonzero(out == group)
        if members.size < 3 or members.size > limit:
            continue
        average = (unit_vectors[members] @ unit_vectors[members].T).astype(np.float64)
        np.fill_diagonal(average, -np.inf)
        size = np.ones(members.size)
        alive = np.ones(members.size, bool)
        clusters = [[index] for index in range(members.size)]
        while True:
            masked = np.where(alive[:, None] & alive[None, :], average, -np.inf)
            i, j = np.unravel_index(int(np.argmax(masked)), masked.shape)
            if not np.isfinite(masked[i, j]) or masked[i, j] < threshold:
                break
            merged = (average[i] * size[i] + average[j] * size[j]) / (size[i] + size[j])
            average[i], average[:, i] = merged, merged
            average[i, i] = -np.inf
            size[i] += size[j]
            alive[j] = False
            clusters[i] += clusters[j]
        for cluster in np.flatnonzero(alive):
            out[members[clusters[cluster]]] = members[min(clusters[cluster])]
    return out
