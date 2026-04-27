"""Every component model must instantiate from a minimal valid payload."""

from datetime import date

import pytest
from pydantic import ValidationError

from pydantic_models import (
    Board,
    BuildSpec,
    Chip,
    Connector,
    Driver,
    DriverBinding,
    Interface,
    Module,
    Package,
    Peripherals,
    Sensor,
    SensorConstraints,
)


def _tested() -> dict:
    return {
        "status": "experimental",
        "by": "rnd@southerniot.net",
        "date": date(2026, 4, 27),
    }


def _electrical() -> dict:
    return {
        "vcc": {"nominal_v": 3.3, "min_v": 3.0, "max_v": 3.6},
        "logic": {"voltage_v": 3.3, "five_v_tolerant": False},
    }


def _package(kind: str = "QFN-32") -> dict:
    return {"type": kind, "pin_count": 32, "pitch_mm": 0.5}


# --- Per-kind smoke tests ----------------------------------------------------


def test_board_minimal() -> None:
    b = Board.model_validate(
        {
            "apiVersion": "hwreg/v1",
            "kind": "board",
            "id": "boards/example/test-board",
            "revision": "0.1.0",
            "summary": "Smoke-test board.",
            "tested": _tested(),
            "lifecycle": "preview",
            "vendor": "example",
            "manufacturer_part_number": "EX-BOARD-01",
            "peripherals": {"uart": 1, "i2c": 1},
            "electrical": _electrical(),
            "build": {"frameworks": ["arduino"]},
        }
    )
    assert b.id == "boards/example/test-board"
    assert b.kind == "board"
    assert isinstance(b.peripherals, Peripherals)
    assert isinstance(b.build, BuildSpec)


def test_module_minimal() -> None:
    m = Module.model_validate(
        {
            "apiVersion": "hwreg/v1",
            "kind": "module",
            "id": "modules/example/test-module",
            "revision": "1.0.0",
            "summary": "Smoke-test module.",
            "tested": _tested(),
            "lifecycle": "active",
            "vendor": "example",
            "manufacturer_part_number": "EX-MOD-01",
            "package": _package("LCC-18"),
            "electrical": _electrical(),
        }
    )
    assert m.kind == "module"
    assert isinstance(m.package, Package)


def test_chip_minimal() -> None:
    c = Chip.model_validate(
        {
            "apiVersion": "hwreg/v1",
            "kind": "chip",
            "id": "chips/example/ex123",
            "revision": "1.0.0",
            "summary": "Smoke-test chip.",
            "tested": _tested(),
            "lifecycle": "active",
            "vendor": "example",
            "manufacturer_part_number": "EX123",
            "package": _package(),
        }
    )
    assert c.kind == "chip"


def test_chip_stub_minimal() -> None:
    """Stubs are minimal entries that exist only to anchor refs (e.g. inherits_from)."""
    c = Chip.model_validate(
        {
            "apiVersion": "hwreg/v1",
            "kind": "chip",
            "id": "chips/example/stub-soc",
            "revision": "1.0.0",
            "summary": "Stub for ref resolution.",
            "tested": {**_tested(), "status": "stub"},
            "lifecycle": "preview",
            "vendor": "example",
            "manufacturer_part_number": "STUB",
            "package": _package(),
        }
    )
    assert c.tested.status == "stub"


def test_sensor_minimal() -> None:
    s = Sensor.model_validate(
        {
            "apiVersion": "hwreg/v1",
            "kind": "sensor",
            "id": "sensors/example/temp",
            "revision": "1.0.0",
            "summary": "Smoke-test temperature sensor.",
            "tested": _tested(),
            "lifecycle": "active",
            "vendor": "example",
            "manufacturer_part_number": "TEMP-01",
            "electrical": _electrical(),
            "interface": {"type": "i2c", "i2c_address": 0x44},
            "constraints": {},
            "package": _package("DFN-4"),
        }
    )
    assert s.kind == "sensor"
    assert isinstance(s.interface, Interface)
    assert isinstance(s.constraints, SensorConstraints)
    assert s.interface.i2c_address == 0x44


def test_connector_minimal() -> None:
    conn = Connector.model_validate(
        {
            "apiVersion": "hwreg/v1",
            "kind": "connector",
            "id": "connectors/jst/ph-2",
            "revision": "1.0.0",
            "summary": "JST PH 2-pin SMD.",
            "tested": _tested(),
            "lifecycle": "active",
            "vendor": "jst",
            "manufacturer_part_number": "S2B-PH-SM4-TB",
            "pin_count": 2,
            "pitch_mm": 2.0,
            "gender": "male",
            "mounting": "smd",
        }
    )
    assert conn.kind == "connector"


def test_driver_minimal() -> None:
    d = Driver.model_validate(
        {
            "apiVersion": "hwreg/v1",
            "kind": "driver",
            "id": "drivers/example/temp",
            "revision": "0.1.0",
            "summary": "Driver for example/temp.",
            "tested": _tested(),
            "lifecycle": "active",
            "applies_to": ["sensors/example/temp"],
            "bindings": [
                {
                    "framework": "arduino",
                    "version_constraint": ">=1.0.0",
                    "library": "ExampleTemp",
                    "license": "MIT",
                }
            ],
        }
    )
    assert d.kind == "driver"
    assert isinstance(d.bindings[0], DriverBinding)


# --- Negative paths ---------------------------------------------------------


def test_extra_field_forbidden() -> None:
    """extra='forbid' must reject unknown YAML keys."""
    with pytest.raises(ValidationError):
        Connector.model_validate(
            {
                "apiVersion": "hwreg/v1",
                "kind": "connector",
                "id": "connectors/jst/ph-2",
                "revision": "1.0.0",
                "summary": "JST PH 2-pin SMD.",
                "tested": _tested(),
                "lifecycle": "active",
                "vendor": "jst",
                "manufacturer_part_number": "S2B-PH-SM4-TB",
                "pin_count": 2,
                "pitch_mm": 2.0,
                "gender": "male",
                "mounting": "smd",
                "unknown_field": "should be rejected",
            }
        )


def test_invalid_id_slug_rejected() -> None:
    """id must match the kind/vendor/part regex (lowercase, hyphenated)."""
    with pytest.raises(ValidationError):
        Sensor.model_validate(
            {
                "apiVersion": "hwreg/v1",
                "kind": "sensor",
                "id": "Sensors/Example/Temp",  # uppercase rejected
                "revision": "1.0.0",
                "summary": "x",
                "tested": _tested(),
                "lifecycle": "active",
                "vendor": "example",
                "manufacturer_part_number": "T",
                "electrical": _electrical(),
                "interface": {"type": "i2c"},
                "constraints": {},
                "package": _package("DFN-4"),
            }
        )


def test_invalid_revision_rejected() -> None:
    """revision must be SemVer 2.0."""
    with pytest.raises(ValidationError):
        Sensor.model_validate(
            {
                "apiVersion": "hwreg/v1",
                "kind": "sensor",
                "id": "sensors/example/temp",
                "revision": "1.0",  # not SemVer
                "summary": "x",
                "tested": _tested(),
                "lifecycle": "active",
                "vendor": "example",
                "manufacturer_part_number": "T",
                "electrical": _electrical(),
                "interface": {"type": "i2c"},
                "constraints": {},
                "package": _package("DFN-4"),
            }
        )


def test_semver_prerelease_accepted() -> None:
    """Full SemVer 2.0 — 1.0.0-rc.1 must validate."""
    s = Sensor.model_validate(
        {
            "apiVersion": "hwreg/v1",
            "kind": "sensor",
            "id": "sensors/example/temp",
            "revision": "1.0.0-rc.1",
            "summary": "x",
            "tested": _tested(),
            "lifecycle": "preview",
            "vendor": "example",
            "manufacturer_part_number": "T",
            "electrical": _electrical(),
            "interface": {"type": "i2c"},
            "constraints": {},
            "package": _package("DFN-4"),
        }
    )
    assert s.revision == "1.0.0-rc.1"


def test_apiversion_only_accepts_camelcase() -> None:
    """populate_by_name=False — api_version snake_case must NOT validate."""
    with pytest.raises(ValidationError):
        Sensor.model_validate(
            {
                "api_version": "hwreg/v1",  # snake_case — must be rejected
                "kind": "sensor",
                "id": "sensors/example/temp",
                "revision": "1.0.0",
                "summary": "x",
                "tested": _tested(),
                "lifecycle": "active",
                "vendor": "example",
                "manufacturer_part_number": "T",
                "electrical": _electrical(),
                "interface": {"type": "i2c"},
                "constraints": {},
                "package": _package("DFN-4"),
            }
        )


def test_pin_package_pin_str_or_int_or_none() -> None:
    """Pin.package_pin accepts int (QFN/QFP), str (BGA grid), or None (breakout)."""
    from pydantic_models import Pin

    Pin.model_validate({"id": "GPIO5", "default": "GPIO", "package_pin": 12})
    Pin.model_validate({"id": "BGA_A4", "default": "GPIO", "package_pin": "A4"})
    Pin.model_validate({"id": "GPIO5", "default": "GPIO"})  # package_pin omitted
