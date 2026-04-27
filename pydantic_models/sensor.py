"""Sensor model — environmental, ADC front-end, IMU, etc.

``SensorConstraints`` is structured per BLUEPRINT.md sec 3.3 — bus-specific
constraints nest under their bus name (``constraints.i2c``, ``.spi``,
``.uart``); cross-bus concerns get their own siblings (``constraints.power``,
``.interrupt``); flat metrology fields (operating temp range, accuracy)
remain at the top level. The conflict checker (Prompt 5) consumes this
shape directly — a flat layout would force the checker to do bus-detection
work that the YAML structure already encodes.

NOTE: ``constraints.power`` is its own type, distinct from
``Electrical.vcc``: the former describes *requirements imposed on the
integrating system* (decoupling caps, startup sequencing); the latter
describes *the part's operating envelope*.
"""

from typing import Annotated, Literal

from pydantic import Field

from .common import (
    COMPONENT_REF_REGEX,
    AssetBundle,
    Electrical,
    ExternalRefs,
    Identifiable,
    Interface,
    KicadRefs,
    Package,
    Strict,
)

ComponentRef = Annotated[str, Field(pattern=COMPONENT_REF_REGEX)]


class TempRange(Strict):
    """Temperature range in degrees Celsius."""

    min_c: float = Field(description="Minimum temperature in °C.")
    max_c: float = Field(description="Maximum temperature in °C.")


class VoltageRange(Strict):
    """Voltage range in volts."""

    min_v: float = Field(description="Minimum voltage in volts.")
    max_v: float = Field(description="Maximum voltage in volts.")


# --- Bus-specific constraints --------------------------------------------


class I2CConstraints(Strict):
    """I²C bus constraints. Populated when ``Interface.type == 'i2c'``."""

    address: int = Field(
        description="Default 7-bit I²C address (decimal — write 0xNN syntax in YAML).",
    )
    address_pin_options: list[int] | None = Field(
        default=None,
        description="Selectable addresses via ADDR pin / strap (7-bit values).",
    )
    requires_pullups_ohms: int | None = Field(
        default=None,
        description=(
            "Required pull-up resistance in ohms. Integer (e.g. 4700, 10000) so the board "
            "author knows what value to size pull-ups to; null = device integrates pull-ups."
        ),
    )


class SPIConstraints(Strict):
    """SPI bus constraints. Populated when ``Interface.type == 'spi'``."""

    cs_active_low: bool = Field(
        default=True,
        description="True if chip-select is active-low (typical).",
    )


class UARTConstraints(Strict):
    """UART bus constraints. Populated when ``Interface.type == 'uart'``."""

    flow_control: Literal["none", "rts-cts", "xon-xoff"] | None = Field(
        default=None,
        description="Hardware/software flow control mode the device requires.",
    )


# --- Cross-bus constraints -----------------------------------------------


class InterruptConstraint(Strict):
    """Whether the device requires a host-side interrupt line."""

    required: bool = Field(description="True if the device cannot be polled and needs an IRQ pin.")
    pin: str | None = Field(
        default=None,
        description="Pin name on the device that emits the interrupt (e.g. INT, ALERT, DRDY).",
    )


class PowerConstraints(Strict):
    """System-side power requirements imposed by integrating this part.

    Distinct from ``Electrical.vcc`` (operating envelope) — these are the
    integration *demands*: decoupling, startup, sequencing.
    """

    min_startup_time_ms: float | None = Field(
        default=None,
        description="Minimum delay between VDD stable and first valid command, in ms.",
    )
    requires_decoupling: list[str] = Field(
        default_factory=list,
        description="Required decoupling caps (free-form, e.g. '100nF X7R close to VDD').",
    )


class SensorConstraints(Strict):
    """Operating envelope, metrology, and bus / power / interrupt constraints."""

    # Bus-specific constraints (only one populated per sensor based on interface.type).
    i2c: I2CConstraints | None = Field(
        default=None,
        description="I²C-specific constraints. Set when interface.type == 'i2c'.",
    )
    spi: SPIConstraints | None = Field(
        default=None,
        description="SPI-specific constraints. Set when interface.type == 'spi'.",
    )
    uart: UARTConstraints | None = Field(
        default=None,
        description="UART-specific constraints. Set when interface.type == 'uart'.",
    )

    # Cross-bus.
    interrupt: InterruptConstraint | None = Field(
        default=None,
        description="Host-side interrupt line requirements.",
    )
    power: PowerConstraints | None = Field(
        default=None,
        description="System-side power requirements (decoupling, startup).",
    )

    # Flat metrology — kept from Prompt 1; not in the 22-site list, not removed.
    operating_temp_c: TempRange | None = Field(
        default=None,
        description="Operating temperature range.",
    )
    storage_temp_c: TempRange | None = Field(
        default=None,
        description="Storage / handling temperature range.",
    )
    supply_voltage_v: VoltageRange | None = Field(
        default=None,
        description="Acceptable VDD range. Often duplicates electrical.vcc.{min,max}_v.",
    )
    measurement_range: dict[str, str | float | int] | None = Field(
        default=None,
        description="Sensor-specific measurement bounds (e.g. {humidity_pct: '0-100'}).",
    )
    accuracy: dict[str, str | float] | None = Field(
        default=None,
        description="Accuracy spec per measurand (e.g. {temp_c: '±0.2', rh_pct: '±1.8'}).",
    )
    response_time_ms: float | None = Field(default=None, description="Response time τ₆₃ in ms.")


class Sensor(Identifiable):
    """A sensor or analog front-end IC."""

    kind: Literal["sensor"] = "sensor"

    vendor: str = Field(description="Vendor slug from Zephyr's vendor-prefixes.txt.")
    manufacturer_part_number: str = Field(description="Manufacturer P/N.")
    electrical: Electrical = Field(description="Electrical specs.")
    interface: Interface = Field(description="Primary communication interface.")
    constraints: SensorConstraints = Field(description="Operating envelope and metrology.")
    package: Package = Field(description="Physical package.")
    drivers: list[ComponentRef] = Field(
        default_factory=list,
        description="Driver component refs (e.g. drivers/sensirion/sht41).",
    )
    kicad: KicadRefs | None = Field(default=None)
    external_refs: ExternalRefs | None = Field(default=None)
    assets: AssetBundle | None = Field(default=None)
    inherits_from: list[ComponentRef] = Field(default_factory=list)
