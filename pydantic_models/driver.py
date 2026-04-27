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
    """A per-framework binding describing how to consume the driver in a project.

    Most fields are framework-conditional and optional. Authors populate
    only what their framework's manifest needs:

    - ESP-IDF: ``component`` + ``source`` (Component Manager)
    - Arduino: ``library`` + ``package_index``
    - Zephyr: ``compatible`` + ``binding`` + ``kconfig``
    - MicroPython: ``module`` + ``install``

    ``tested_with`` is intentionally a list — drivers get tested against
    multiple framework versions over time. Section 3.4 of BLUEPRINT.md
    shows it as a single string; that example is wrong (override recorded
    in Appendix A).
    """

    framework: Framework = Field(description="Target firmware framework.")
    version_constraint: str = Field(
        description="Version constraint in framework-native syntax (semver range, npm-style, PEP440).",  # noqa: E501
    )
    source: str | None = Field(
        default=None,
        description="Source URL — git repo, registry URL, or 'core' if shipped with the framework.",
    )

    # Per-framework manifest fields ----------------------------------------

    component: str | None = Field(
        default=None,
        description="ESP-IDF component manifest ID (e.g. espressif/esp_ads111x).",
    )
    library: str | None = Field(
        default=None,
        description="Arduino library name (e.g. Adafruit_ADS1X15).",
    )
    package_index: str | None = Field(
        default=None,
        description="Arduino board / library package-index identifier (e.g. 'arduino', 'esp32').",
    )
    module: str | None = Field(
        default=None,
        description="MicroPython module name (e.g. adafruit_sht4x).",
    )
    install: str | None = Field(
        default=None,
        description="MicroPython install command (e.g. 'mip install adafruit-sht4x').",
    )
    compatible: str | None = Field(
        default=None,
        description="Zephyr Devicetree `compatible` string (e.g. 'sensirion,sht4x').",
    )
    binding: str | None = Field(
        default=None,
        description="Zephyr DT binding path (e.g. dts/bindings/sensor/sensirion,sht4x.yaml).",
    )
    kconfig: str | None = Field(
        default=None,
        description="Zephyr Kconfig symbol (e.g. CONFIG_SHT4X).",
    )
    header: str | None = Field(
        default=None,
        description="Public header file to #include (e.g. sht4x.h).",
    )
    sample_call: str | None = Field(
        default=None,
        description="One-line idiomatic call sample (e.g. 'sht4x_get_measurement(dev, &t, &rh);').",
    )

    # Test + license -------------------------------------------------------

    tested_with: list[str] = Field(
        default_factory=list,
        description="Framework versions verified by hand (e.g. ['esp-idf 5.5', 'arduino-esp32 3.0.1']).",  # noqa: E501
    )
    license: str | None = Field(
        default=None,
        description=(
            "SPDX identifier of the upstream driver library (e.g. MIT, Apache-2.0, BSD-3-Clause). "
            "Optional — some upstream libraries do not publish a clear license."
        ),
    )


class Driver(Identifiable):
    """A driver — pointer + version constraints across one or more frameworks."""

    kind: Literal["driver"] = "driver"

    applies_to: list[ComponentRef] = Field(
        description="Component refs this driver supports (sensors, chips, modules). Unversioned.",
    )
    bindings: list[DriverBinding] = Field(
        description="Per-framework bindings; at least one required.",
        min_length=1,
    )
