"""Pin-conflict checker tests.

Builds the bundle into a tmp_path and runs the conflict checker against
the three system fixtures committed under
``tests/fixtures/system_examples/``. SARIF output is asserted against
the bundled SARIF 2.1.0 schema.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tools.builder import build
from tools.conflicts import (
    Diagnostic,
    UnresolvedComponentRef,
    build_graph,
    load_system,
    run_all,
    to_sarif,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = REPO_ROOT / "library"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "system_examples"
SARIF_SCHEMA = REPO_ROOT / "tests" / "fixtures" / "sarif-2.1.0-schema.json"


@pytest.fixture(scope="module")
def bundle_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the bundle once for the whole test module."""
    out = tmp_path_factory.mktemp("dist")
    build(LIBRARY, out)
    return out


def _diagnose(bundle_dir: Path, fixture_name: str) -> list[Diagnostic]:
    system = load_system(FIXTURES / fixture_name, bundle_db=bundle_dir / "library.sqlite")
    graph = build_graph(system)
    return run_all(graph, system)


# --- Per-fixture rule tests ---------------------------------------------


def test_clean_system(bundle_dir: Path) -> None:
    """lorawan-node fixture must produce 0 errors AND 0 warnings."""
    diagnostics = _diagnose(bundle_dir, "lorawan-node.yaml")
    errors = [d for d in diagnostics if d.severity == "error"]
    warnings_ = [d for d in diagnostics if d.severity == "warning"]
    assert errors == [], f"unexpected errors: {[(d.id, d.message) for d in errors]}"
    assert warnings_ == [], f"unexpected warnings: {[(d.id, d.message) for d in warnings_]}"


def test_i2c_addr_clash(bundle_dir: Path) -> None:
    """conflict-i2c-addr fixture → exactly 1 ERROR with id I2C_ADDR_CLASH."""
    diagnostics = _diagnose(bundle_dir, "conflict-i2c-addr.yaml")
    errors = [d for d in diagnostics if d.severity == "error"]
    assert len(errors) == 1
    err = errors[0]
    assert err.id == "I2C_ADDR_CLASH"
    # Message must include both component instance names.
    assert "u2" in err.message
    assert "u3" in err.message
    # Message must include the remediation hint with the alternative address.
    assert "0x45" in err.message


def test_strapping_warn(bundle_dir: Path) -> None:
    """conflict-strapping fixture → exactly 1 WARN, id STRAPPING_PIN_MISUSE."""
    diagnostics = _diagnose(bundle_dir, "conflict-strapping.yaml")
    errors = [d for d in diagnostics if d.severity == "error"]
    warnings_ = [d for d in diagnostics if d.severity == "warning"]
    assert errors == []
    assert len(warnings_) == 1
    assert warnings_[0].id == "STRAPPING_PIN_MISUSE"
    assert "GPIO0" in warnings_[0].message


# --- SARIF output ------------------------------------------------------


def test_sarif_output(bundle_dir: Path) -> None:
    """Clean system → SARIF JSON validates against the bundled SARIF 2.1.0 schema."""
    fixture = FIXTURES / "lorawan-node.yaml"
    diagnostics = _diagnose(bundle_dir, "lorawan-node.yaml")
    sarif = to_sarif(diagnostics, fixture)

    schema = json.loads(SARIF_SCHEMA.read_text())
    # Validate. Raises jsonschema.ValidationError on a real schema failure.
    jsonschema.validate(instance=sarif, schema=schema)

    # Spot-check structure.
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "hwlib-conflicts"
    # Clean system → empty results array.
    assert sarif["runs"][0]["results"] == []


def test_sarif_with_diagnostics(bundle_dir: Path) -> None:
    """Conflict-bearing system → SARIF results carry rule + level + message + location."""
    fixture = FIXTURES / "conflict-i2c-addr.yaml"
    diagnostics = _diagnose(bundle_dir, "conflict-i2c-addr.yaml")
    sarif = to_sarif(diagnostics, fixture)

    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(instance=sarif, schema=schema)

    results = sarif["runs"][0]["results"]
    assert len(results) >= 1
    addr_clash = next((r for r in results if r["ruleId"] == "I2C_ADDR_CLASH"), None)
    assert addr_clash is not None
    assert addr_clash["level"] == "error"
    assert "0x44" in addr_clash["message"]["text"]


# --- Loader error path -------------------------------------------------


def test_unknown_component_ref(bundle_dir: Path, tmp_path: Path) -> None:
    """A system YAML with a ref not in the bundle raises UnresolvedComponentRef."""
    fixture = tmp_path / "bogus-ref.yaml"
    fixture.write_text(
        "system:\n"
        "  board: boards/espressif/esp32-s3-devkitc-1\n"
        "  components:\n"
        "    - ref: sensors/nonexistent/widget\n"
        "      instance: u2\n"
        "      pins: {SDA: GPIO8, SCL: GPIO9}\n"
    )
    with pytest.raises(UnresolvedComponentRef, match="sensors/nonexistent/widget"):
        load_system(fixture, bundle_db=bundle_dir / "library.sqlite")
