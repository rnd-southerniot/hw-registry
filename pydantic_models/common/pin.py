"""Pin / signal model used by boards, modules, and chips."""

from typing import Literal

from pydantic import Field

from .identifiable import Strict

PinDirection = Literal["in", "out", "bidir"]


class AltFunction(Strict):
    """Mux-selectable peripheral function on a pin."""

    function: str = Field(
        description="Function identifier (e.g. gpio, i2c_sda, spi_mosi, adc_in, uart_tx).",
    )
    peripheral: str | None = Field(
        default=None,
        description="Peripheral instance owning this function (e.g. i2c0, spi2, adc1).",
    )
    channel: int | None = Field(
        default=None,
        description="Peripheral channel or index (e.g. ADC1 channel 7).",
    )
    direction: PinDirection | None = Field(
        default=None,
        description="Signal direction relative to the device (in / out / bidir).",
    )
    open_drain: bool = Field(
        default=False,
        description="True if the function is open-drain (e.g. I²C SDA/SCL).",
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
        description="Voltage rail powering this pin (e.g. VDDIO, VDDA, vdd_io).",
    )
    exposed_as: str | None = Field(
        default=None,
        description=(
            "When this pin is re-exposed at a different level (e.g. chip pin PA0 brought out "
            "as module pin 'pin1'), the outer-level identifier."
        ),
    )
    default: str = Field(
        description="Default function on cold boot (e.g. gpio, JTAG_TDI, i2c_sda).",
    )
    alt_functions: list[AltFunction] = Field(
        default_factory=list,
        description="Mux-selectable alternate functions in addition to the default.",
    )
