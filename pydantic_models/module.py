"""Module model — RF/SoM modules that contain other components and expose pads/pins."""

from typing import Annotated, Any, Literal

from pydantic import Field

from .common import (
    COMPONENT_REF_REGEX,
    AssetBundle,
    Electrical,
    ExternalRefs,
    Identifiable,
    KicadRefs,
    Package,
    Pin,
    Strict,
)


ComponentRef = Annotated[str, Field(pattern=COMPONENT_REF_REGEX)]


class ContainedPart(Strict):
    """A component physically integrated into a module (SoC, antenna, memory, etc.)."""

    ref: ComponentRef = Field(
        description="Component ref of the contained part (e.g. chips/st/stm32wle5jc@1.0.0).",
    )
    role: str = Field(
        description="Role within the module (e.g. soc, antenna, flash, psram, balun, tcxo).",
    )


class FirmwareOption(Strict):
    """Pre-flashed firmware variant available from the vendor (e.g. AT-command stack)."""

    name: str = Field(description="Firmware variant name (e.g. RUI3-LoRaWAN-AT, BlueNRG-stack).")
    description: str = Field(description="Short summary of what the firmware exposes.")
    size_kb: int | None = Field(default=None, description="Approximate flash footprint in KB.")
    source_url: str | None = Field(
        default=None,
        description="Vendor URL pointing at the firmware download or repo.",
    )


class Module(Identifiable):
    """An RF / SoM module exposing pads or pins, containing one or more chips."""

    kind: Literal["module"] = "module"  # type: ignore[assignment]

    vendor: str = Field(description="Vendor slug from Zephyr's vendor-prefixes.txt.")
    manufacturer_part_number: str = Field(description="Manufacturer P/N as printed on the module.")
    package: Package = Field(description="Physical package envelope.")
    electrical: Electrical = Field(description="Electrical specs.")
    pins: list[Pin] = Field(
        default_factory=list,
        description="Module pads/pins exposed externally.",
    )
    contains: list[ContainedPart] = Field(
        default_factory=list,
        description="Components physically integrated into this module.",
    )
    overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Field-by-field overrides applied on top of contained parts during inheritance resolution.",  # noqa: E501
    )
    firmware_options: list[FirmwareOption] = Field(
        default_factory=list,
        description="Pre-flashed firmware variants offered by the vendor (e.g. AT-command stacks).",
    )
    rf_certifications: list[str] = Field(
        default_factory=list,
        description="Regulatory certifications (e.g. FCC, CE, IC, NCC, MIC).",
    )
    kicad: KicadRefs | None = Field(default=None)
    external_refs: ExternalRefs | None = Field(default=None)
    assets: AssetBundle | None = Field(default=None)
    inherits_from: list[ComponentRef] = Field(
        default_factory=list,
        description="Component refs this module inherits from (typically the SoC chip).",
    )
