"""Chip model — bare silicon (SoC, MCU, transceiver, peripheral IC)."""

from typing import Annotated, Literal

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


class CoreSpec(Strict):
    """CPU core configuration."""

    architecture: str = Field(description="ISA family (e.g. arm-cortex-m4f, xtensa-lx7, riscv32).")
    cores: int = Field(default=1, ge=1, description="Number of CPU cores.")
    max_clock_mhz: int | None = Field(default=None, description="Maximum CPU clock in MHz.")
    fpu: bool | None = Field(default=None, description="Hardware floating-point unit present.")


class Chip(Identifiable):
    """A silicon device — MCU, SoC, transceiver, peripheral IC."""

    kind: Literal["chip"] = "chip"

    vendor: str = Field(description="Vendor slug from Zephyr's vendor-prefixes.txt.")
    manufacturer_part_number: str = Field(description="Manufacturer P/N (e.g. STM32WLE5JCI6).")
    package: Package = Field(description="Physical package.")
    electrical: Electrical | None = Field(
        default=None,
        description="Electrical specs. Optional for stub entries that exist only to anchor refs.",
    )
    core: CoreSpec | None = Field(default=None, description="CPU core spec for MCUs/SoCs.")
    flash_kb: int | None = Field(default=None, description="On-die flash size in KB.")
    ram_kb: int | None = Field(default=None, description="On-die RAM size in KB.")
    pins: list[Pin] = Field(
        default_factory=list,
        description="Pin list with default and alt functions; empty for stubs.",
    )
    kicad: KicadRefs | None = Field(default=None)
    external_refs: ExternalRefs | None = Field(default=None)
    assets: AssetBundle | None = Field(default=None)
    inherits_from: list[ComponentRef] = Field(default_factory=list)
