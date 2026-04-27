"""Bundle builder tests.

Two flavours:

- Roundtrip / inheritance / determinism — built against the real seed
  components in ``library/``.
- Synthetic-fixture tests — mini libraries assembled in tmp_path to
  exercise resolver semantics that the seed components do not cover
  (alt_function shorthand against a rich parent, soft-fallback against
  a stub parent, unknown override keys).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import warnings
from pathlib import Path

import pytest

from tools.builder import (
    MismatchedOverrideShorthand,
    UnknownOverrideKey,
    build,
)
from tools.builder.errors import AltFunctionShorthandWarning

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = REPO_ROOT / "library"

EXPECTED_SEED_IDS = {
    "boards/espressif/esp32-s3-devkitc-1",
    "chips/st/stm32wle5jc",
    "drivers/sensirion/sht41",
    "drivers/ti/ads1115",
    "modules/espressif/esp32-s3-wroom-1",
    "modules/rakwireless/rak3172",
    "sensors/sensirion/sht41",
    "sensors/ti/ads1115",
}


# --- Real library tests -------------------------------------------------


def test_bundle_roundtrip(tmp_path: Path) -> None:
    """library.json / .sqlite / index.json all carry the 8 seed components."""
    build(LIBRARY, tmp_path)

    library = json.loads((tmp_path / "library.json").read_text())
    assert "components" in library
    assert "meta" in library
    assert set(library["components"].keys()) == EXPECTED_SEED_IDS
    assert library["meta"]["total_count"] == 8
    assert library["meta"]["count_by_kind"] == {
        "board": 1,
        "chip": 1,
        "driver": 2,
        "module": 2,
        "sensor": 2,
    }

    conn = sqlite3.connect(tmp_path / "library.sqlite")
    try:
        rows = conn.execute("SELECT id, kind FROM components ORDER BY id").fetchall()
        assert len(rows) == 8
        assert {r[0] for r in rows} == EXPECTED_SEED_IDS

        # FTS5 actually populated.
        humidity_hits = conn.execute(
            "SELECT id FROM components_fts WHERE components_fts MATCH 'humidity'"
        ).fetchall()
        assert ("sensors/sensirion/sht41",) in humidity_hits

        # user_version pinned.
        (uv,) = conn.execute("PRAGMA user_version").fetchone()
        assert uv == 1
    finally:
        conn.close()

    index = json.loads((tmp_path / "index.json").read_text())
    assert "meta" in index
    assert {c["id"] for c in index["components"]} == EXPECTED_SEED_IDS
    # Each summary record has exactly id/kind/summary.
    assert all(set(c.keys()) == {"id", "kind", "summary"} for c in index["components"])


def test_index_size_under_50kb(tmp_path: Path) -> None:
    """index.json must stay small even as the registry grows."""
    build(LIBRARY, tmp_path)
    size = (tmp_path / "index.json").stat().st_size
    assert size < 50 * 1024, f"index.json is {size} bytes, exceeds 50 KB cap"


def test_inheritance_resolution(tmp_path: Path) -> None:
    """Resolver runs cleanly on the seed YAMLs.

    The chip stub (``chips/st/stm32wle5jc``) has only the bare required
    fields, so this is mostly a smoke test that inheritance does not
    error. Richer resolution tests live in the synthetic-fixture suite
    below and arrive in earnest when a real chip YAML lands.

    RAK3172's ``overrides.pins`` use shorthand against the bare chip
    stub, which fires ``AltFunctionShorthandWarning`` for every entry —
    expected behavior, not the focus of this test. Suppress those
    warnings here; ``test_alt_function_shorthand_soft_fallback`` is the
    test that asserts they fire.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", AltFunctionShorthandWarning)
        bundle = build(LIBRARY, tmp_path)

    rak3172 = bundle["components"]["modules/rakwireless/rak3172"]
    assert rak3172["id"] == "modules/rakwireless/rak3172"
    assert rak3172["kind"] == "module"
    # Override-applied: the four pin entries from RAK3172.overrides.pins
    # land on the resolved record. Soft-fallback shorthand coerces to
    # `{function: <name>}` because the chip stub has no AltFunctions.
    pins = rak3172.get("pins") or []
    assert any(p.get("id") == "PA0" for p in pins)
    pa0 = next(p for p in pins if p.get("id") == "PA0")
    alts = pa0.get("alt_functions") or []
    assert len(alts) == 2
    # Soft fallback: bare {function: <name>}.
    assert {"function": "gpio"} in alts
    assert {"function": "uart_rx"} in alts


def test_determinism(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two builds with the same SOURCE_DATE_EPOCH must be byte-identical."""
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1714521600")
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    build(LIBRARY, out1)
    build(LIBRARY, out2)

    for filename in ("library.json", "library.sqlite", "index.json"):
        h1 = hashlib.sha256((out1 / filename).read_bytes()).hexdigest()
        h2 = hashlib.sha256((out2 / filename).read_bytes()).hexdigest()
        assert h1 == h2, (
            f"{filename} not deterministic across two builds with same "
            f"SOURCE_DATE_EPOCH (h1={h1[:16]}…, h2={h2[:16]}…)"
        )


# --- Synthetic-fixture helpers ------------------------------------------


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _chip_stub(lib: Path) -> None:
    _write_yaml(
        lib / "chips/example/foo.yaml",
        """\
apiVersion: hwreg/v1
kind: chip
id: chips/example/foo
revision: 1.0.0
summary: "Example stub chip"
tested: { status: stub, by: test, date: 2026-04-28 }
lifecycle: experimental
vendor: example
manufacturer_part_number: FOO-STUB
package: { type: QFN-32, pin_count: 32 }
""",
    )


def _chip_rich(lib: Path) -> None:
    """Chip with a fully-defined PA0 pin so shorthand has something to match."""
    _write_yaml(
        lib / "chips/example/foo.yaml",
        """\
apiVersion: hwreg/v1
kind: chip
id: chips/example/foo
revision: 1.0.0
summary: "Example chip with PA0 enumerated"
tested: { status: verified, by: test, date: 2026-04-28 }
lifecycle: stable
vendor: example
manufacturer_part_number: FOO-1
package: { type: QFN-32, pin_count: 32 }
pins:
  - id: PA0
    default: gpio
    alt_functions:
      - { function: gpio, direction: bidir }
      - { function: uart_tx, peripheral: usart1, direction: out }
""",
    )


# --- Synthetic-fixture tests --------------------------------------------


def test_alt_function_shorthand_against_rich_parent(tmp_path: Path) -> None:
    """Shorthand resolves to the parent's full AltFunction when the parent has it."""
    lib = tmp_path / "library"
    _chip_rich(lib)
    _write_yaml(
        lib / "modules/example/bar.yaml",
        """\
apiVersion: hwreg/v1
kind: module
id: modules/example/bar
revision: 1.0.0
summary: "Bar module"
tested: { status: verified, by: test, date: 2026-04-28 }
lifecycle: stable
vendor: example
manufacturer_part_number: BAR-1
package: { type: LCC-12, pin_count: 12 }
electrical:
  vcc: { nominal_v: 3.3 }
  logic: { voltage_v: 3.3 }
inherits_from: [chips/example/foo@1.0.0]
overrides:
  pins:
    - id: PA0
      exposed_as: pin1
      alt_functions: [gpio, uart_tx]
""",
    )

    bundle = build(lib, tmp_path / "dist")
    bar = bundle["components"]["modules/example/bar"]

    pins = bar.get("pins") or []
    pa0 = next((p for p in pins if p.get("id") == "PA0"), None)
    assert pa0 is not None
    assert pa0.get("exposed_as") == "pin1"

    alts = pa0.get("alt_functions") or []
    assert len(alts) == 2

    gpio_alt = next((a for a in alts if a.get("function") == "gpio"), None)
    # open_drain defaults to False and is NOT in the dump (exclude_unset=True
    # drops fields the YAML did not explicitly set).
    assert gpio_alt == {"function": "gpio", "direction": "bidir"}

    uart_alt = next((a for a in alts if a.get("function") == "uart_tx"), None)
    assert uart_alt is not None
    assert uart_alt.get("peripheral") == "usart1"
    assert uart_alt.get("direction") == "out"


def test_alt_function_shorthand_soft_fallback(tmp_path: Path) -> None:
    """Shorthand against a stub parent emits warnings + coerces to bare `{function: <name>}`."""
    lib = tmp_path / "library"
    _chip_stub(lib)
    _write_yaml(
        lib / "modules/example/bar.yaml",
        """\
apiVersion: hwreg/v1
kind: module
id: modules/example/bar
revision: 1.0.0
summary: "Bar module against stub chip"
tested: { status: verified, by: test, date: 2026-04-28 }
lifecycle: stable
vendor: example
manufacturer_part_number: BAR-1
package: { type: LCC-12, pin_count: 12 }
electrical:
  vcc: { nominal_v: 3.3 }
  logic: { voltage_v: 3.3 }
inherits_from: [chips/example/foo@1.0.0]
overrides:
  pins:
    - id: PA0
      alt_functions: [gpio, uart_rx]
""",
    )

    with pytest.warns(AltFunctionShorthandWarning) as record:
        bundle = build(lib, tmp_path / "dist")

    # Both shorthand strings ('gpio' and 'uart_rx') were unmatched against
    # the bare stub parent — both should warn.
    messages = [str(w.message) for w in record]
    assert any("'gpio'" in m for m in messages)
    assert any("'uart_rx'" in m for m in messages)
    # Warning text includes the inferred YAML path and the pin id.
    assert all("library/modules/example/bar.yaml" in m for m in messages)
    assert all("'PA0'" in m for m in messages)
    assert all("treating as new function" in m for m in messages)

    bar = bundle["components"]["modules/example/bar"]
    pins = bar.get("pins") or []
    pa0 = next((p for p in pins if p.get("id") == "PA0"), None)
    assert pa0 is not None

    alts = pa0.get("alt_functions") or []
    # Soft fallback: every shorthand becomes a bare AltFunction.
    assert {"function": "gpio"} in alts
    assert {"function": "uart_rx"} in alts


def test_unknown_override_key_raises(tmp_path: Path) -> None:
    """An override key not on the parent model raises UnknownOverrideKey."""
    lib = tmp_path / "library"
    _chip_stub(lib)
    _write_yaml(
        lib / "modules/example/bar.yaml",
        """\
apiVersion: hwreg/v1
kind: module
id: modules/example/bar
revision: 1.0.0
summary: "Bar module with bogus override key"
tested: { status: stub, by: test, date: 2026-04-28 }
lifecycle: experimental
vendor: example
manufacturer_part_number: BAR-1
package: { type: LCC-12, pin_count: 12 }
electrical:
  vcc: { nominal_v: 3.3 }
  logic: { voltage_v: 3.3 }
inherits_from: [chips/example/foo@1.0.0]
overrides:
  not_a_real_field: 42
""",
    )

    with pytest.raises(UnknownOverrideKey, match="not_a_real_field"):
        build(lib, tmp_path / "dist")


def test_alt_functions_non_string_non_dict_raises(tmp_path: Path) -> None:
    """An alt_functions entry that is neither string nor dict raises a structural error."""
    # YAML can't easily express this purely (every value is one of those),
    # so we synthesise a list containing an int via a YAML number — yamllint
    # would catch it but the resolver should too. Use a numeric 42.
    lib = tmp_path / "library"
    _chip_stub(lib)
    _write_yaml(
        lib / "modules/example/bar.yaml",
        """\
apiVersion: hwreg/v1
kind: module
id: modules/example/bar
revision: 1.0.0
summary: "Bar module with bogus alt_functions entry"
tested: { status: stub, by: test, date: 2026-04-28 }
lifecycle: experimental
vendor: example
manufacturer_part_number: BAR-1
package: { type: LCC-12, pin_count: 12 }
electrical:
  vcc: { nominal_v: 3.3 }
  logic: { voltage_v: 3.3 }
inherits_from: [chips/example/foo@1.0.0]
overrides:
  pins:
    - id: PA0
      alt_functions: [42]
""",
    )

    with pytest.raises(MismatchedOverrideShorthand):
        build(lib, tmp_path / "dist")
