"""Driver model — pointer to per-framework driver libraries for a component."""

from typing import Annotated, Literal

from pydantic import Field

from .common import (
    COMPONENT_REF_REGEX,
    Identifiable,
    Strict,
)


ComponentRef = Annotated[str, Field(pattern=COMPONENT_REF_REGEX)]

Framework = Literal["esp-idf", "arduino", "zephyr", "micropython", "platformio"]


class DriverBinding(Strict):
    """A per-framework binding describing how to consume the driver in a project."""

    framework: Framework = Field(description="Target firmware framework.")
    version_constraint: str = Field(
        description="Version constraint in framework-native syntax (semver range, npm-style, PEP440).",
    )
    source: str | None = Field(
        default=None,
        description="Source URL — git repo, registry URL, or 'core' if shipped with the framework.",
    )
    component: str | None = Field(
        default=None,
        description="ESP-IDF component manifest ID (e.g. espressif/esp_ads111x).",
    )
    library: str | None = Field(
        default=None,
        description="Arduino library name (e.g. Adafruit_ADS1X15).",
    )
    module: str | None = Field(
        default=None,
        description="Zephyr/MicroPython module name or DT-compatible string (e.g. 'ti,ads1115').",
    )
    tested_with: list[str] = Field(
        default_factory=list,
        description="Framework versions verified by hand (e.g. ['esp-idf 5.2.1', 'esp-idf 5.3.0']).",
    )
    license: str = Field(
        description="SPDX identifier of the upstream driver library (e.g. MIT, Apache-2.0, BSD-3-Clause).",
    )


class Driver(Identifiable):
    """A driver — pointer + version constraints across one or more frameworks."""

    kind: Literal["driver"] = "driver"

    applies_to: list[ComponentRef] = Field(
        description="Component refs this driver supports (sensors, chips, modules).",
    )
    bindings: list[DriverBinding] = Field(
        description="Per-framework bindings; at least one required.",
        min_length=1,
    )
