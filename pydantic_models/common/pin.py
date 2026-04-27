"""Pin / signal model used by boards, modules, and chips."""

from pydantic import Field

from .identifiable import Strict


class AltFunction(Strict):
    """Mux-selectable peripheral function on a pin."""

    name: str = Field(description="Function name (e.g. I2C0_SDA, SPI2_MOSI).")
    peripheral: str | None = Field(
        default=None,
        description="Peripheral instance owning this function (e.g. I2C0, SPI2).",
    )
    channel: int | None = Field(
        default=None,
        description="Peripheral channel or index (e.g. ADC1 channel 3).",
    )


class Pin(Strict):
    """A single I/O pin on a chip, module, or board."""

    id: str = Field(
        description="Pin identifier in the device's native namespace (e.g. GPIO5, PA0)."
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternate human-friendly names (e.g. SDA, LED_BUILTIN).",
    )
    package_pin: int | str | None = Field(
        default=None,
        description=(
            "Physical pin reference: int for numbered packages (QFN/QFP), "
            "str for grid refs like 'A4' (BGA), null for breakouts without a package mapping."
        ),
    )
    voltage_domain: str | None = Field(
        default=None,
        description="Voltage rail powering this pin (e.g. VDDIO, VDDA).",
    )
    default: str = Field(
        description="Default function on cold boot (e.g. GPIO, JTAG_TDI, I2C_SDA).",
    )
    alt_functions: list[AltFunction] = Field(
        default_factory=list,
        description="Mux-selectable alternate functions in addition to the default.",
    )
