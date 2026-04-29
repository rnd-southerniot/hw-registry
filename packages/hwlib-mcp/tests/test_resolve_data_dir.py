"""Test the HWLIB_DATA_DIR -> hwlib_data -> BundleNotFound fallback chain."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hwlib_mcp import data


def test_resolve_uses_env_var_when_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """HWLIB_DATA_DIR takes precedence over the hwlib_data fallback."""
    monkeypatch.setenv("HWLIB_DATA_DIR", str(tmp_path))
    resolved = data.resolve_data_dir()
    assert resolved == tmp_path.resolve()


def test_resolve_falls_back_to_hwlib_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When HWLIB_DATA_DIR is unset, fall back to hwlib_data.data_path()."""
    monkeypatch.delenv("HWLIB_DATA_DIR", raising=False)

    # Stub the hwlib_data module — we don't want the test to depend on
    # whether the real wheel is installed.
    fake = type(sys)("hwlib_data")
    fake.data_path = lambda: tmp_path  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hwlib_data", fake)

    assert data.resolve_data_dir() == tmp_path


def test_resolve_raises_bundle_not_found_when_no_path_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both env var unset AND hwlib_data not importable -> BundleNotFound."""
    monkeypatch.delenv("HWLIB_DATA_DIR", raising=False)

    # Block hwlib_data from importing — even if it's installed in the test
    # environment from sub-phase 1a's editable install, this test should
    # still surface the BundleNotFound path.
    monkeypatch.setitem(sys.modules, "hwlib_data", None)

    with pytest.raises(data.BundleNotFound) as exc:
        data.resolve_data_dir()

    msg = str(exc.value)
    assert "HWLIB_DATA_DIR" in msg
    assert "hwlib-data" in msg
