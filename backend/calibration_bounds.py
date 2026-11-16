"""Corner-placement sensitivity for the sheet's inferred physical axis order.

Intervals enclose a declared numerical scenario, not camera uncertainty. Lens
correction and the centred, square-pixel camera model remain fixed. Outward
rounding retains floating-point arithmetic error; repeated interval variables
can widen the result and conservatively leave an identifiable view unresolved.
"""

from __future__ import annotations

import math

import numpy as np


class _Unresolved(ValueError):
    pass


class _Interval:
    __slots__ = ("hi", "lo")

    def __init__(self, lo, hi=None):
        self.lo = float(lo)
        self.hi = self.lo if hi is None else float(hi)
        if not math.isfinite(self.lo) or not math.isfinite(self.hi) or self.lo > self.hi:
            raise _Unresolved("nonfinite interval")

    @staticmethod
    def coerce(other):
        return other if isinstance(other, _Interval) else _Interval(other)

    @classmethod
    def rounded(cls, lo, hi):
        return cls(math.nextafter(lo, -math.inf), math.nextafter(hi, math.inf))

    def __add__(self, other):
        other = self.coerce(other)
        return self.rounded(self.lo + other.lo, self.hi + other.hi)

    def __neg__(self):
        return _Interval(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + -self.coerce(other)

    def __mul__(self, other):
        other = self.coerce(other)
        terms = (self.lo * other.lo, self.lo * other.hi,
                 self.hi * other.lo, self.hi * other.hi)
        return self.rounded(min(terms), max(terms))

    def __truediv__(self, other):
        other = self.coerce(other)
        if other.lo <= 0 <= other.hi:
            raise _Unresolved("interval denominator includes zero")
        return self * self.rounded(1 / other.hi, 1 / other.lo)

    def square(self):
        lo = 0.0 if self.lo <= 0 <= self.hi else min(self.lo * self.lo, self.hi * self.hi)
        hi = max(self.lo * self.lo, self.hi * self.hi)
        return self.rounded(lo, hi)


def _homography_columns(corners, size, radius):
    """Centred unit-square homography columns over an eight-coordinate box."""
    corners = np.asarray(corners, dtype=float)
    if (corners.shape != (4, 2) or not np.isfinite(corners).all()
            or not math.isfinite(radius) or radius < 0):
        raise _Unresolved("invalid corner scenario")
    # Interval subtraction includes rounding when centring the coordinates.
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = [
        [_Interval.rounded(p[k] - radius, p[k] + radius) - size[k] / 2 for k in range(2)]
        for p in corners
    ]
    dx1, dx2, dx3 = x1 - x2, x3 - x2, x0 - x1 + x2 - x3
    dy1, dy2, dy3 = y1 - y2, y3 - y2, y0 - y1 + y2 - y3
    determinant = dx1 * dy2 - dx2 * dy1
    g = (dx3 * dy2 - dx2 * dy3) / determinant
    h = (dx1 * dy3 - dx3 * dy1) / determinant
    # The denominator is affine over the unit square; positive values at its
    # four vertices keep the entire sheet in one finite projective chart.
    one = _Interval(1.0)
    if any(den.lo <= 0 for den in (one + g, one + h, one + g + h)):
        raise _Unresolved("corner scenario crosses the projective horizon")
    return (x1 - x0 + g * x1, y1 - y0 + g * y1, g), (
        x3 - x0 + h * x3, y3 - y0 + h * y3, h
    )


def inferred_axis_order(corners, size):
    """Return long-x True/False only if inferred ordering survives the corner box.

    Each undistorted corner coordinate varies independently by +/-0.25 pixels
    per 3000-pixel image diagonal. This is a resize-consistent support policy,
    not a measurement-error bound. None means this evidence cannot decide.
    """
    diagonal = math.hypot(*size)
    radius = 0.25 * diagonal / 3000
    try:
        u, v = _homography_columns(corners, size, radius)
        p1 = u[0].square() + u[1].square()
        p2 = v[0].square() + v[1].square()
        z1, z2 = u[2].square(), v[2].square()
        cross = u[0] * v[0] + u[1] * v[1]
        zcross = u[2] * v[2]
        focal2 = -cross / zcross
        # Preserve the existing orthogonality-focal plausibility envelope for
        # the whole scenario, not just its central fitted homography.
        if focal2.lo < (0.3 * diagonal) ** 2 or focal2.hi > (5 * diagonal) ** 2:
            return None
        # Eliminate f²=-cross/zcross from the metric squared-length difference.
        # Avoid treating a derived focal interval as independent of its columns.
        difference = (cross * (z1 - z2) - (p1 - p2) * zcross) / cross
        if difference.lo > 0:
            return True
        if difference.hi < 0:
            return False
    except _Unresolved:
        pass
    return None
