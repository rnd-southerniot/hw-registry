"""Sensor / chip electrical interface descriptor.

Single flat model with type-specific fields nullable. A model_validator that
enforces field-vs-type compatibility (no spi_* on i2c interfaces, etc.) is a
post-MVP refinement; today extra='forbid' blocks unknown keys but does NOT
block known keys set on the wrong type. Authoring discipline carries the
weight until the validator lands.
"""

from typing import Literal

from pydantic import Field

from .identifiable import Strict

InterfaceType = Literal["i2c", "spi", "uart", "onewire", "analog", "pwm"]


class Interface(Strict):
    """Communication / signal interface for a sensor or peripheral."""

    type: InterfaceType = Field(description="Bus or signal protocol family.")

    # --- I2C ---------------------------------------------------------------
    i2c_address: int | None = Field(
        default=None,
        description="Default I2C address (7-bit, decimal). Use 0xNN syntax in YAML.",
    )
    i2c_address_options: list[int] | None = Field(
        default=None,
        description="Selectable addresses via ADDR pin / strap (7-bit values).",
    )
    i2c_max_clock_khz: int | None = Field(
        default=None,
        description="Maximum I2C bus clock the device tolerates, in kHz.",
    )
    i2c_pullups_required: bool | None = Field(
        default=None,
        description="True if the device does not integrate I2C pull-ups.",
    )

    # --- SPI ---------------------------------------------------------------
    spi_max_clock_mhz: float | None = Field(default=None, description="Max SPI clock in MHz.")
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
