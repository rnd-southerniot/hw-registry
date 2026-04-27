"""Board model — physical dev board / breakout / final product PCB."""

from typing import Annotated, Literal

from pydantic import Field

from .common import (
    COMPONENT_REF_REGEX,
    AssetBundle,
    Discovery,
    Electrical,
    ExternalRefs,
    Identifiable,
    KicadRefs,
    Pin,
    Strict,
)


class Peripherals(Strict):
    """Counts of peripheral instances exposed by the board's main SoC.

    Flat int form is intentional. BLUEPRINT.md sec 3.1 shows a richer
    nested shape (``spi: { count: 4, max_clock_mhz: 80, user_usable: 2 }``);
    the flat form aligns with Prompt 3's "peripherals counts" wording and
    is sufficient for the MVP. See BLUEPRINT.md Appendix A "Section 3.1
    illustrative-only divergences" for the rationale.

    TODO(post-mvp): consider migrating to nested {count, max_clock_*,
    user_usable} once the conflict checker (Prompt 5) grows
    peripheral-allocation rules — at that point the extra metadata
    earns its keep.
    """

    uart: int | None = Field(default=None, ge=0)
    i2c: int | None = Field(default=None, ge=0)
    spi: int | None = Field(default=None, ge=0)
    can: int | None = Field(default=None, ge=0)
    adc: int | None = Field(default=None, ge=0)
    dac: int | None = Field(default=None, ge=0)
    pwm_channels: int | None = Field(default=None, ge=0)
    usb: int | None = Field(default=None, ge=0)
    ethernet: int | None = Field(default=None, ge=0)
    sd_mmc: int | None = Field(default=None, ge=0)
    i2s: int | None = Field(default=None, ge=0)
    rmt: int | None = Field(default=None, ge=0)
    touch: int | None = Field(default=None, ge=0)


class ExpansionHeader(Strict):
    """Through-hole or SMD header exposed for expansion / breakout."""

    name: str = Field(description="Header silkscreen designator (e.g. J1, header_left).")
    pin_count: int = Field(ge=1, description="Total pin count of the header.")
    pitch_mm: float = Field(description="Pin-to-pin pitch in millimetres (typically 2.54).")
    pins: list[str] = Field(
        description="Pin.id values in physical order, starting at pin 1. Must match length pin_count.",  # noqa: E501
    )


class BuildSpec(Strict):
    """Toolchain / memory configuration relevant to firmware build."""

    frameworks: list[
        Literal[
            "esp-idf", "arduino", "zephyr", "micropython", "platformio", "stm32-hal", "pico-sdk"
        ]
    ] = Field(  # noqa: E501
        description="Supported firmware frameworks for this board.",
    )
    flash_mb: float | None = Field(default=None, description="External flash size in MB.")
    ram_kb: int | None = Field(default=None, description="On-die RAM in KB.")
    psram_mb: float | None = Field(default=None, description="External PSRAM in MB.")


ComponentRef = Annotated[str, Field(pattern=COMPONENT_REF_REGEX)]


class Board(Identifiable):
    """A physical board — dev kit, breakout, custom PCB."""

    kind: Literal["board"] = "board"

    vendor: str = Field(description="Vendor slug from Zephyr's vendor-prefixes.txt.")
    manufacturer_part_number: str = Field(
        description="Manufacturer P/N as printed on the board / box."
    )
    peripherals: Peripherals = Field(description="Peripheral instance counts of the main SoC.")
    electrical: Electrical = Field(description="Electrical specs.")
    discovery: Discovery = Field(
        default_factory=Discovery,
        description="Host-side discovery hooks (USB IDs, MAC OUIs).",
    )
    strapping_pins: list[str] = Field(
        default_factory=list,
        description="Pin.id values that latch boot mode at reset; constrain at design time.",
    )
    reserved_pins: list[str] = Field(
        default_factory=list,
        description="Pin.id values reserved by on-board peripherals (e.g. USB D+/D-, flash).",
    )
    pins: list[Pin] = Field(
        default_factory=list,
        description="Every exposed I/O pin with default and alt functions.",
    )
    expansion_headers: list[ExpansionHeader] = Field(
        default_factory=list,
        description="Physical headers exposed for expansion.",
    )
    build: BuildSpec = Field(description="Toolchain and memory configuration.")
    kicad: KicadRefs | None = Field(default=None, description="KiCad symbol/footprint refs.")
    external_refs: ExternalRefs | None = Field(default=None, description="Distributor cross-refs.")
    assets: AssetBundle | None = Field(default=None, description="Datasheet and additional assets.")
    inherits_from: list[ComponentRef] = Field(
        default_factory=list,
        description="Component refs (e.g. modules/espressif/esp32-s3-wroom-1@1.0.0) this board inherits from.",  # noqa: E501
    )
