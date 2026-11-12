"""Circle-consistent final assembly, with an explicit minimum-edit join rule.

This is a geometric fitting rule for supplied primitives and ordered source-end
witnesses, not physical edge identification. A separated minimum under this rule
does not qualify the optics, source partition points or corrected circle. Local
cycle compatibility is separate from the caller's whole-boundary validity check.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

MAX_JOIN_PRIMITIVES = 1024
_EPS = np.finfo(float).eps
_TAU = 2 * math.pi


class JoinConstructionError(ValueError):
    """Expected unavailable/ambiguous analytic construction; retain the source."""

    def __init__(self, reason, message=None):
        self.reason = reason
        super().__init__(message or reason)


@dataclass(frozen=True)
class _Join:
    point: np.ndarray
    lower: float = 0.0
    upper: float = 0.0
    point_error: float = 0.0


def _point(value):
    result = np.asarray(value, dtype=float)
    if result.shape != (2,) or not np.isfinite(result).all():
        raise JoinConstructionError("numerical")
    return result


def _guard(*values):
    # An engineering arithmetic guard, NOT fitted-parameter or physical error.
    return 64 * _EPS * max(1.0, *(float(np.max(np.abs(v))) for v in values))


def _unit(line):
    direction = _point(line.data["d"])
    length = math.hypot(*direction)
    if not math.isfinite(length) or length == 0:
        raise JoinConstructionError("numerical")
    return direction / length


def _ends(primitive):
    if "source_ends" not in primitive.data:
        raise JoinConstructionError("source_provenance")
    try:
        source = np.asarray(primitive.data["source_ends"], dtype=float)
    except (ValueError, TypeError) as exc:
        raise JoinConstructionError("source_provenance") from exc
    if source.shape != (2, 2) or not np.isfinite(source).all():
        raise JoinConstructionError("source_provenance")
    return source[0], source[1]


def _exact_contact(line, circle):
    """Exact tangency of represented binary-rational inputs, without a square root."""
    c = [Fraction(float(v)) for v in circle.data["c"]]
    a = [Fraction(float(v)) for v in line.data["c"]]
    d = [Fraction(float(v)) for v in line.data["d"]]
    r = Fraction(float(circle.data["r"]))
    cross = d[0] * (c[1] - a[1]) - d[1] * (c[0] - a[0])
    return r * r * (d[0] * d[0] + d[1] * d[1]) == cross * cross


def _line_circle(line, circle, left, right):
    centre, anchor = _point(circle.data["c"]), _point(line.data["c"])
    radius = float(circle.data["r"])
    if not math.isfinite(radius) or radius <= 0:
        raise JoinConstructionError("numerical")
    direction = _unit(line)
    normal = np.array([-direction[1], direction[0]])
    delta = centre - anchor
    height = math.fsum((direction[0] * delta[1], -direction[1] * delta[0]))
    foot = centre - height * normal
    guard = _guard(centre, anchor, radius, delta)
    gap = radius - abs(height)
    if abs(gap) <= guard:
        # Constrained fillets prescribe a tangent join. Normalize only their
        # roundoff-level distance residual, not a genuinely incompatible fit.
        # A previously observed tangent contact can also be retained when the
        # explicit design-intent fit cannot resolve its radius coordinate. That
        # flag moves neither C nor R and is never inferred from free radius edits.
        # Other free near-tangencies stay unresolved unless exactly tangent.
        if (
            circle.data.get("fillet") is not None
            or circle.data.get("end_cap")
            or circle.data.get("tangent_contact")
            or _exact_contact(line, circle)
        ):
            return [_Join(foot, point_error=guard)]
        raise JoinConstructionError("near_contact")
    if gap < 0:
        raise JoinConstructionError("no_intersection")
    if circle.data.get("fillet") is not None or circle.data.get("end_cap"):
        raise JoinConstructionError("numerical", "a tangent constraint no longer reaches its line")
    # Product form avoids cancellation in R^2-h^2. Root displacement becomes
    # ill-conditioned at contact; propagate that sensitivity into score guards.
    reach = math.sqrt(gap * (radius + abs(height)))
    if not math.isfinite(reach) or reach <= 0:
        raise JoinConstructionError("numerical")
    source_left = _ends(left)[1]
    source_right = _ends(right)[0]
    offsets = (foot - source_left) + (foot - source_right)
    projection = math.fsum(direction[i] * offsets[i] for i in range(2))
    # Each endpoint contributes its squared displacement. Drop the common
    # candidate-independent terms: reduced costs are +/-2*reach*projection.
    score = 2 * reach * projection
    root_error = guard * (2 + (radius + abs(height)) / reach)
    projection_error = 4 * guard + 16 * _EPS * float(np.abs(offsets).sum())
    error = 2 * (
        abs(projection) * root_error + reach * projection_error + root_error * projection_error
    )
    error += 16 * _EPS * abs(score)
    if not all(math.isfinite(v) for v in (score, error)):
        raise JoinConstructionError("numerical")
    result = []
    for sign in (-1, 1):
        point = foot + sign * reach * direction
        if not np.isfinite(point).all():
            raise JoinConstructionError("numerical")
        value = sign * score
        result.append(
            _Join(
                point,
                math.nextafter(value - error, -math.inf),
                math.nextafter(value + error, math.inf),
                root_error + guard,
            )
        )
    return result


def _junction(left, right):
    if left.kind == right.kind == "line":
        a, b = _point(left.data["c"]), _point(right.data["c"])
        d, e = _unit(left), _unit(right)
        matrix = np.column_stack([d, -e])
        try:
            t = np.linalg.solve(matrix, b - a)
        except np.linalg.LinAlgError as exc:
            raise JoinConstructionError("invalid_cycle") from exc
        point = a + t[0] * d
        if not np.isfinite(point).all():
            raise JoinConstructionError("numerical")
        determinant = abs(float(np.linalg.det(matrix)))
        error = _guard(a, b, point) * (2 + 1 / max(determinant, np.finfo(float).tiny))
        if not math.isfinite(error):
            raise JoinConstructionError("numerical")
        return [_Join(point, point_error=error)]
    if {left.kind, right.kind} != {"line", "arc"}:
        raise JoinConstructionError("invalid_cycle")
    line, circle = (left, right) if left.kind == "line" else (right, left)
    return _line_circle(line, circle, left, right)


def _arc_sweep(primitive, start, end):
    centre = _point(primitive.data["c"])
    a, b = start - centre, end - centre
    witness = _point(primitive.data["mid"]) - centre
    if math.hypot(*witness) <= _guard(centre, primitive.data["r"]):
        raise JoinConstructionError("source_provenance")
    angle = math.atan2(a[1], a[0])
    ccw = (math.atan2(b[1], b[0]) - angle) % _TAU
    wm = (math.atan2(witness[1], witness[0]) - angle) % _TAU
    if "source_sweep" in primitive.data:
        source = float(primitive.data["source_sweep"])
        if not math.isfinite(source) or not 0 < abs(source) < _TAU:
            raise JoinConstructionError("source_provenance")
        sweep = ccw if source > 0 else ccw - _TAU
    else:
        # Legacy explicit tangent primitives have no frozen source. Their
        # unique joins and existing interior witness still specify a sector.
        if not (primitive.data.get("fillet") is not None or primitive.data.get("end_cap")):
            raise JoinConstructionError("source_provenance")
        sweep = ccw if wm < ccw else ccw - _TAU
    along = wm if sweep > 0 else (-wm) % _TAU
    return angle, sweep, along


def _compatible(primitive, before, after):
    """0 invalid, 1 guarded-compatible, 2 numerically unresolved (kept in DP)."""
    start, end = before.point, after.point
    if np.array_equal(start, end):
        return 0  # the represented segment/arc has coincident endpoints
    error = before.point_error + after.point_error + _guard(start, end)
    if math.dist(start, end) <= error:
        return 2
    if primitive.kind == "line":
        if "source_ends" not in primitive.data:
            return 1  # legacy explicit line/tangent constructions
        source_start, source_end = _ends(primitive)
        direction = _unit(primitive)
        observed = float((source_end - source_start) @ direction)
        built = float((end - start) @ direction)
        guard = _guard(start, end, source_start, source_end)
        if abs(observed) <= guard:
            return 2
        progress = math.copysign(1, observed) * built
        return 1 if progress > error else 0 if progress < -error else 2
    _, sweep, along = _arc_sweep(primitive, start, end)
    radius = float(primitive.data["r"])
    angle_error = 128 * _EPS + error / radius
    if (
        abs(sweep) >= _TAU - angle_error
        or min(along, _TAU - along) <= angle_error
        or abs(along - abs(sweep)) <= angle_error
    ):
        return 2
    return 1 if 0 < along < abs(sweep) else 0


def _minimum_cycle(joins, compatible, *, upper, excluded=None):
    """Minimize one additive bound; exclude one path with a 'differs' state."""
    count = len(joins)
    answer = None
    for first in range(len(joins[0])):
        differs = excluded is not None and first != excluded[0]
        bound = joins[0][first].upper if upper else joins[0][first].lower
        states = {(first, differs): bound}
        history = []
        for k in range(1, count):
            following, previous = {}, {}
            for state, cost in states.items():
                prior, different = state
                for current, join in enumerate(joins[k]):
                    if not compatible[k][prior][current]:
                        continue
                    changed = different or (excluded is not None and current != excluded[k])
                    key = (current, changed)
                    value = cost + (join.upper if upper else join.lower)
                    value = math.nextafter(value, math.inf if upper else -math.inf)
                    if not math.isfinite(value):
                        raise JoinConstructionError("numerical")
                    if key not in following or value < following[key]:
                        following[key], previous[key] = value, state
            states = following
            history.append(previous)
        for state, cost in states.items():
            last, different = state
            if not compatible[0][last][first] or (excluded is not None and not different):
                continue
            if answer is not None and cost >= answer[0]:
                continue
            path, key = [last], state
            for previous in reversed(history):
                key = previous[key]
                path.append(key[0])
            answer = cost, tuple(reversed(path))
    return answer


def assemble(primitives):
    """Ordered final segments or a typed refusal; never invent another circle.

    A unique guarded minimum is conditional on this endpoint-displacement rule.
    Score bounds are conservative floating-point engineering guards, not formal
    exact constructions, physical uncertainty or a model-adequacy certificate.
    """
    count = len(primitives)
    if count == 1 and primitives[0].kind == "circle":
        p = primitives[0]
        centre, radius = _point(p.data["c"]), float(p.data["r"])
        if not math.isfinite(radius) or radius <= 0:
            raise JoinConstructionError("numerical")
        return [("circle", centre, radius)]
    if count < 2:
        raise JoinConstructionError("invalid_cycle")
    if count > MAX_JOIN_PRIMITIVES:
        raise JoinConstructionError("work_limit")
    joins = [_junction(p, primitives[(k + 1) % count]) for k, p in enumerate(primitives)]
    compatible = [
        [[_compatible(p, a, b) for b in joins[k]] for a in joins[k - 1]]
        for k, p in enumerate(primitives)
    ]
    best = _minimum_cycle(joins, compatible, upper=True)
    if best is None:
        raise JoinConstructionError("invalid_cycle")
    alternative = _minimum_cycle(joins, compatible, upper=False, excluded=best[1])
    if alternative is not None and not best[0] < alternative[0]:
        raise JoinConstructionError("ambiguous")
    if any(compatible[k][best[1][k - 1]][best[1][k]] != 1 for k in range(count)):
        raise JoinConstructionError("numerical", "join ordering is not numerically resolved")
    points = [joins[k][choice].point for k, choice in enumerate(best[1])]
    result = []
    for k, p in enumerate(primitives):
        start, end = points[k - 1], points[k]
        if p.kind == "line":
            result.append(("line", start, end))
            continue
        angle, sweep, _ = _arc_sweep(p, start, end)
        centre, radius = _point(p.data["c"]), float(p.data["r"])
        mid = centre + radius * np.array([math.cos(angle + sweep / 2), math.sin(angle + sweep / 2)])
        # Check the actual three-point construction in local coordinates. Small
        # sectors/large translations may be unable to represent the stored circle.
        local = np.array([mid - start, end - start])
        determinant = 2 * (local[0, 0] * local[1, 1] - local[0, 1] * local[1, 0])
        if abs(determinant) < 1e-12:
            # Match the downstream three-point arc contract before sampling or
            # native export can turn an expected refusal into a request failure.
            raise JoinConstructionError("numerical", "the three-point arc is not representable")
        try:
            emitted_centre = start + np.linalg.solve(2 * local, np.sum(local * local, axis=1))
        except np.linalg.LinAlgError as exc:
            raise JoinConstructionError("numerical") from exc
        emitted_radius = math.dist(start, emitted_centre)
        guard = 8 * _guard(centre, start, mid, end, radius)
        if (
            not np.isfinite(emitted_centre).all()
            or math.dist(emitted_centre, centre) > guard
            or abs(emitted_radius - radius) > guard
        ):
            raise JoinConstructionError(
                "numerical", "the three-point arc cannot represent its fitted circle"
            )
        result.append(("arc", start, mid, end))
    return result
