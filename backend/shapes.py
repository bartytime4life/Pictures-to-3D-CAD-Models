"""Small, explicit inputs for the common-shape flat-part designer (all units are mm)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import BuildRequest


class DesignShape(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str = Field(min_length=1, max_length=60)
    kind: Literal["rectangle", "rounded_rectangle", "circle", "slot", "triangle", "hexagon"]
    operation: Literal["add", "cut"] = "add"
    x_mm: float = Field(default=0, ge=-1000, le=1000)
    y_mm: float = Field(default=0, ge=-1000, le=1000)
    width_mm: float = Field(ge=0.5, le=1000)
    height_mm: float = Field(ge=0.5, le=1000)
    corner_mm: float = Field(default=3, ge=0, le=500)
    rotation_deg: float = Field(default=0, ge=-180, le=180)

    @model_validator(mode="after")
    def valid_corner(self):
        if (
            self.kind == "rounded_rectangle"
            and self.corner_mm > min(self.width_mm, self.height_mm) / 2
        ):
            raise ValueError("Corner radius must be no more than half the smaller side.")
        return self


class ShapeBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    name: str = Field(default="Shape design", min_length=1, max_length=100)
    revision: str = Field(default="1", min_length=1, max_length=100)
    thickness_mm: float = Field(default=4, ge=0.1, le=500)
    shapes: list[DesignShape] = Field(min_length=1, max_length=16)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        return BuildRequest.clean_name(value)

    @model_validator(mode="after")
    def material_present(self):
        if not any(shape.operation == "add" for shape in self.shapes):
            raise ValueError("Add at least one material shape.")
        if len({shape.id for shape in self.shapes}) != len(self.shapes):
            raise ValueError("Each shape needs a unique ID.")
        return self
