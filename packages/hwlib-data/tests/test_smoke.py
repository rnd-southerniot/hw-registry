"""Smoke test: verify the bundled data is accessible after install.

Skipped when ``hwlib_data`` isn't importable (wheel not built/installed).
After ``pip install -e ./packages/hwlib-data`` (or after a release-workflow
wheel install), all three tests should pass.
"""

from __future__ import annotations

import sqlite3

import pytest

hwlib_data = pytest.importorskip(
    "hwlib_data",
    reason="hwlib-data not installed (run `pip install -e ./packages/hwlib-data` first)",
)


def test_data_path_returns_real_directory() -> None:
    p = hwlib_data.data_path()
    assert p.is_dir(), f"data_path() = {p} is not a directory"


def test_required_files_present() -> None:
    p = hwlib_data.data_path()
    for fname in ("library.json", "library.sqlite", "index.json"):
        assert (p / fname).is_file(), f"missing: {fname}"


def test_sqlite_query_returns_components() -> None:
    """Query the bundled SQLite for the expected MVP component count."""
    conn = sqlite3.connect(str(hwlib_data.data_path() / "library.sqlite"))
    try:
        count = conn.execute("SELECT COUNT(*) FROM components").fetchone()[0]
    finally:
        conn.close()
    # MVP seed: 1 board, 1 chip, 2 modules, 2 sensors, 2 drivers = 8.
    # Test asserts >0 rather than ==8 so adding components in future
    # releases doesn't break this smoke test — the existence of the
    # FTS-indexed table and at least one row is the contract here.
    assert count > 0, "library.sqlite has zero components"
