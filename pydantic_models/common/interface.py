"""Sensor / chip electrical interface descriptor.

Bus-specific *constraints* (I²C address, address pin options, pullup
requirement) live on ``SensorConstraints.i2c`` per BLUEPRINT.md sec 3.3.
``Interface`` carries the bus *type* and a generic ``speed_max_khz`` plus
SPI/UART/OneWire/analog/PWM-specific fields the model has historically
accepted.

TODO(post-mvp): tighten Interface with a type-discriminated validator
(e.g. forbid spi_mode on i2c interfaces).

TODO(blueprint-driven): when a real SPI / UART / OneWire sensor lands,
move the protocol-specific fields off Interface and onto
SensorConstraints.<bus> — analogous to the I²C move done for site #17/18.
"""

from typing import Literal

from pydantic import Field

from .identifiable import Strict

InterfaceType = Literal["i2c", "spi", "uart", "onewire", "analog", "pwm"]


class Interface(Strict):
    """Communication / signal interface for a sensor or peripheral."""

    type: InterfaceType = Field(description="Bus or signal protocol family.")
    speed_max_khz: int | None = Field(
        default=None,
        description=(
            "Maximum bus clock the device tolerates, in kHz. Generic across buses; "
            "interpret as 'kHz' for I²C and SPI, baud rate analogue for UART."
        ),
    )

    # --- SPI ---------------------------------------------------------------
    spi_mode: int | None = Field(default=None, ge=0, le=3, description="SPI mode 0–3 (CPOL/CPHA).")

    # --- UART --------------------------------------------------------------
    uart_baud_default: int | None = Field(default=None, description="Default baud rate.")
    uart_max_baud: int | None = Field(default=None, description="Maximum supported baud rate.")

    # --- 1-Wire ------------------------------------------------------------
    onewire_parasite_power: bool | None = Field(
        default=None,
        description="True if the device supports parasite-power mode.",
    )

    # --- Analog ------------------------------------------------------------
    analog_resolution_bits: int | None = Field(
        default=None,
        description="ADC/DAC resolution in bits.",
    )
    analog_input_range_v: tuple[float, float] | None = Field(
        default=None,
        description="Input range as (min_v, max_v).",
    )

    # --- PWM ---------------------------------------------------------------
    pwm_max_freq_hz: int | None = Field(
        default=None,
        description="Maximum PWM frequency in Hz.",
    )
