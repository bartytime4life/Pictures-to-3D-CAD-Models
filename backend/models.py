"""Bounded, explicit inputs shared by the API and isolated CAD worker."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from shapely.geometry import Polygon
from shapely.validation import explain_validity

# Bound each hole before its points are parsed; the 2000-point total is checked below.
HoleRing = Annotated[list[tuple[float, float]], Field(max_length=2000)]


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    outer: list[tuple[float, float]] = Field(min_length=3, max_length=2000)
    holes: list[HoleRing] = Field(default_factory=list, max_length=32)

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
        return self


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
