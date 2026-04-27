"""Sensor model — environmental, ADC front-end, IMU, etc."""

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


class SensorConstraints(Strict):
    """Operating envelope and metrology constraints."""

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
    sleep_current_uA: float | None = Field(default=None, description="Sleep current in µA.")
    active_current_uA: float | None = Field(
        default=None, description="Active conversion current in µA."
    )


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
