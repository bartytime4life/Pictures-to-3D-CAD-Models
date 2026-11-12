"""Bounded, explicit inputs shared by the API and isolated CAD worker."""

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from shapely.geometry import Polygon
from shapely.validation import explain_validity

# Bound each hole before its points are parsed; the 2000-point total is checked below.
HoleRing = Annotated[list[tuple[float, float]], Field(max_length=2000)]
XY = tuple[float, float]
MAX_SEGMENTS = 2000


class LineSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    kind: Literal["line"]
    start: XY
    end: XY


class ArcSegment(BaseModel):
    """A circular arc from `start` through `mid` to `end`."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    kind: Literal["arc"]
    start: XY
    mid: XY
    end: XY


class CircleSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    kind: Literal["circle"]
    center: XY
    radius: float = Field(gt=0)


Segment = Annotated[LineSegment | ArcSegment | CircleSegment, Field(discriminator="kind")]
SegmentRing = Annotated[list[Segment], Field(min_length=1, max_length=MAX_SEGMENTS)]


class Primitives(BaseModel):
    """Exact boundary description fitted to the traced rings, in the profile's frame."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    outer: SegmentRing
    holes: list[SegmentRing] = Field(default_factory=list, max_length=32)


class TraceReference(BaseModel):
    """How a reference-sheet trace was scaled and corrected (evidence, not geometry)."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    kind: Literal["a4", "letter", "custom"]
    sheet_mm: tuple[float, float]
    mm_per_px: float = Field(gt=0, le=1000)
    lens_k1: float = Field(ge=-1, le=1)
    edge_blur_mm: float = Field(ge=0, le=100)
    thickness_mm: float | None = Field(default=None, gt=0, le=500)
    camera_height_mm: float | None = Field(default=None, gt=0, le=1_000_000)
    focal_source: Literal["sheet", "exif", "holes", "assumed"] | None = None
    notes: list[Annotated[str, Field(max_length=300)]] = Field(default_factory=list, max_length=16)

    @field_validator("sheet_mm")
    @classmethod
    def bounded_sheet(cls, value):
        if not all(10 <= v <= 2000 for v in value):
            raise ValueError("Sheet sides must be between 10 and 2000 mm.")
        return value


def _close(a, b, tolerance):
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= tolerance


def ring_polygon(ring, sagitta):
    """Sample a validated segment ring as polygon vertices within `sagitta` of each arc."""
    from .fitting import arc_geometry  # light module; deferred to keep import order simple

    if ring[0].kind == "circle":
        c, r = ring[0].center, ring[0].radius
        n = max(24, min(720, math.ceil(math.pi / math.acos(max(-1.0, 1 - min(sagitta / r, 1))))))
        return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    points = []
    for segment in ring:
        if segment.kind == "line":
            points.append(segment.start)
            continue
        (ux, uy), r, a0, sweep = arc_geometry(segment.start, segment.mid, segment.end)
        step = 2 * math.acos(max(-1.0, 1 - min(sagitta / r, 1)))
        n = max(2, min(720, math.ceil(abs(sweep) / max(step, 1e-6))))
        points.extend(
            (ux + r * math.cos(a0 + sweep * k / n), uy + r * math.sin(a0 + sweep * k / n)) for k in range(n)
        )
    return points


def check_ring(ring, size):
    """Closure, shape and bounds of one segment ring; raises ValueError."""
    if any(segment.kind == "circle" for segment in ring):
        if len(ring) != 1:
            raise ValueError("A circle must describe a whole boundary by itself.")
        return
    if len(ring) < 2:
        raise ValueError("A boundary needs at least two lines or arcs.")
    tolerance = 1e-6 * size + 1e-9
    for current, following in zip(ring, ring[1:] + ring[:1]):
        if not _close(current.end, following.start, tolerance):
            raise ValueError("Boundary segments must join end to start in a closed loop.")
        if current.kind == "arc":
            from .fitting import arc_geometry

            try:
                _, radius, _, sweep = arc_geometry(current.start, current.mid, current.end)
            except ValueError:
                raise ValueError("An arc's three points must not lie on a line.") from None
            if radius > 1_000_000 or abs(sweep) < 1e-9:
                raise ValueError("An arc is too flat to describe a boundary.")


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    outer: list[tuple[float, float]] = Field(min_length=3, max_length=2000)
    holes: list[HoleRing] = Field(default_factory=list, max_length=32)
    # Optional exact description of the same rings (lines, arcs, circles); the polygon
    # rings remain the reviewed outline and the fallback geometry.
    primitives: Primitives | None = None
    reference: TraceReference | None = None

    @model_validator(mode="after")
    def validate_polygon(self):
        rings = [self.outer, *self.holes]
        if sum(map(len, rings)) > 2000:
            raise ValueError("Outline is too detailed. Reduce outline detail and try again.")
        if any(len(ring) < 3 for ring in rings):
            raise ValueError("Every outline and hole needs at least three points.")
        if any(abs(v) > 1_000_000 for ring in rings for point in ring for v in point):
            raise ValueError("Outline coordinates exceed the supported range.")
        polygon = Polygon(self.outer, self.holes)
        if not polygon.is_valid:
            raise ValueError(f"Outline cannot form a closed solid: {explain_validity(polygon)}.")
        if polygon.area <= 1e-6:
            raise ValueError("The outline has no usable area.")
        left, bottom, right, top = polygon.bounds
        if min(right - left, top - bottom) <= 1e-6:
            raise ValueError("The outline must have nonzero width and height.")
        if self.primitives is not None:
            self.check_primitives(rings, max(right - left, top - bottom))
        return self

    def check_primitives(self, rings, size):
        described = [self.primitives.outer, *self.primitives.holes]
        if len(described) != len(rings):
            raise ValueError("Fitted boundaries must match the outline and every hole.")
        if sum(map(len, described)) > MAX_SEGMENTS:
            raise ValueError("The fitted outline has too many segments.")
        coordinates = [
            v
            for ring in described
            for segment in ring
            for point in (
                [segment.center] if segment.kind == "circle"
                else [segment.start, segment.end] + ([segment.mid] if segment.kind == "arc" else [])
            )
            for v in point
        ]
        if any(abs(v) > 1_000_000 for v in coordinates):
            raise ValueError("Fitted outline coordinates exceed the supported range.")
        for ring, polygon_ring in zip(described, rings):
            check_ring(ring, size)
            sampled = Polygon(ring_polygon(ring, 1e-4 * size))
            traced = Polygon(polygon_ring)
            if not sampled.is_valid or traced.area <= 0:
                raise ValueError("A fitted boundary crosses itself.")
            # The fitted description must be the outline the user reviewed, not another shape.
            if sampled.symmetric_difference(traced).area > 0.03 * traced.area + 1e-9:
                raise ValueError("A fitted boundary does not match its traced outline.")


class DesignSettings(BaseModel):
    """User-selected design changes, separate from measured source dimensions."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    scale_percent: float = Field(default=100, ge=10, le=400)
    thickness_percent: float = Field(default=100, ge=10, le=400)
    color: str = Field(default="#9ca3af", pattern=r"^#[0-9a-fA-F]{6}$")
    material: Literal["pla", "petg", "abs", "asa", "tpu", "nylon"] = "pla"
    detail_mode: Literal["original", "draft", "balanced", "fine"] = "original"
    nozzle_mm: float = Field(default=0.4, ge=0.1, le=8)
    output_mode: Literal["single", "split"] = "single"
    split_columns: int = Field(default=2, ge=1, le=4)
    split_rows: int = Field(default=1, ge=1, le=4)
    printer_id: str = Field(default="custom", min_length=1, max_length=150)
    bed_width_mm: float = Field(default=220, ge=20, le=5000)
    bed_depth_mm: float = Field(default=220, ge=20, le=5000)
    bed_height_mm: float = Field(default=250, ge=20, le=5000)
    bed_margin_mm: float = Field(default=5, ge=0, le=30)

    @field_validator("color")
    @classmethod
    def normalize_color(cls, value):
        return value.lower()

    @model_validator(mode="after")
    def bounded_grid(self):
        if self.split_columns * self.split_rows > 8:
            raise ValueError("Choose a split grid with at most 8 cells.")
        return self


class BuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    profile: Profile
    width_mm: float = Field(ge=0.1, le=2000)
    thickness_mm: float = Field(ge=0.1, le=500)
    name: str = Field(default="Untitled part", min_length=1, max_length=100)
    revision: str = Field(default="1", min_length=1, max_length=100)
    design: DesignSettings | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError("Use a nonempty project name without control characters.")
        return value

    @model_validator(mode="after")
    def validate_scaled_height(self):
        xs, ys = zip(*self.profile.outer)
        design = self.design or DesignSettings()
        width = self.width_mm * design.scale_percent / 100
        thickness = self.thickness_mm * design.thickness_percent / 100
        height = (max(ys) - min(ys)) * width / (max(xs) - min(xs))
        if not 0.1 <= width <= 2000 or not 0.1 <= thickness <= 500:
            raise ValueError(
                "Design scale must leave width between 0.1 and 2000 mm and thickness between 0.1 and 500 mm."
            )
        if not 0.1 <= height <= 2000:
            raise ValueError(
                "Scaled height must be between 0.1 and 2000 mm. Check the outline and reference width."
            )
        return self


Detail = Literal["coarse", "standard", "fine"]
Reference = Literal["none", "a4", "letter", "custom"]
