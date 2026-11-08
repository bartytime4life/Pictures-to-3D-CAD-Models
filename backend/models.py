"""Bounded, explicit inputs shared by the API and isolated CAD worker."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from shapely.geometry import Polygon
from shapely.validation import explain_validity


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    outer: list[tuple[float, float]] = Field(min_length=3, max_length=2000)
    holes: list[list[tuple[float, float]]] = Field(default_factory=list, max_length=32)

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


class BuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    profile: Profile
    width_mm: float = Field(ge=0.1, le=2000)
    thickness_mm: float = Field(ge=0.1, le=500)
    name: str = Field(default="Untitled part", min_length=1, max_length=100)
    revision: str = Field(default="1", min_length=1, max_length=100)

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
        height = (max(ys) - min(ys)) * self.width_mm / (max(xs) - min(xs))
        if not 0.1 <= height <= 2000:
            raise ValueError(
                "Scaled height must be between 0.1 and 2000 mm. Check the outline and reference width."
            )
        return self


Detail = Literal["coarse", "standard", "fine"]
