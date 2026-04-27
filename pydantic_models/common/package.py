"""Physical package descriptor (chip / module / sensor / connector)."""

from pydantic import Field

from .identifiable import Strict


class PackageDimensions(Strict):
    """Outer dimensions of the physical package in millimetres.

    Long-form names (length / width / height) are intentional. Section 3.2/3.3
    of BLUEPRINT.md uses {x, y, z}; that example is wrong (which is length?).
    Override recorded in BLUEPRINT.md Appendix A.
    """

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
    ipc_name: str | None = Field(
        default=None,
        description="IPC-7351 land-pattern name (e.g. DFN40P150X150X50-4N, LCC50P15X15X25-50N).",
    )
    rf_certifications: list[str] = Field(
        default_factory=list,
        description=(
            "Regulatory certifications attached to this physical package (e.g. FCC, CE, IC, KC). "
            "Meaningful for RF modules; left empty for non-RF parts."
        ),
    )
