"""Physical package descriptor (chip / module / sensor)."""

from pydantic import Field

from .identifiable import Strict


class PackageDimensions(Strict):
    """Outer dimensions of the physical package in millimetres."""

    length_mm: float = Field(description="Length along the longest axis in mm.")
    width_mm: float = Field(description="Width along the shorter axis in mm.")
    height_mm: float | None = Field(default=None, description="Height (z-axis) in mm.")


class Package(Strict):
    """Physical package envelope."""

    type: str = Field(
        description="Package family (e.g. QFN-32, MSOP-10, LCC-WROOM-1, BGA-484).",
    )
    pin_count: int | None = Field(
        default=None,
        description="Total pin or pad count (null for shielded modules where exposed pads are the contract).",  # noqa: E501
    )
    pitch_mm: float | None = Field(
        default=None,
        description="Pin-to-pin pitch in millimetres.",
    )
    dimensions: PackageDimensions | None = Field(
        default=None,
        description="Outer physical dimensions.",
    )
