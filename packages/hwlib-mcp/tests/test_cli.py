"""CLI argument shape: --http binding default and --host override paths."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest
from hwlib_mcp.__main__ import build_run_kwargs


def _ns(**overrides: object) -> argparse.Namespace:
    """Construct a Namespace mirroring the CLI's defaults, with overrides."""
    return argparse.Namespace(
        http=overrides.get("http", False),
        host=overrides.get("host"),
        port=overrides.get("port", 8080),
        log_level=overrides.get("log_level", "info"),
    )


def test_http_default_host_is_external() -> None:
    """--http without --host binds 0.0.0.0 (externally reachable).

    Loopback-only HTTP MCP has no use case (stdio fills that role); the
    default in --http mode is the network-reachable interface.
    """
    assert build_run_kwargs(_ns(http=True)) == {
        "transport": "streamable-http",
        "host": "0.0.0.0",
        "port": 8080,
    }


def test_http_explicit_host_honored() -> None:
    """--http --host 127.0.0.1 honors the explicit loopback override."""
    kwargs = build_run_kwargs(_ns(http=True, host="127.0.0.1"))
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["transport"] == "streamable-http"


def test_host_without_http_warns(
    bundle_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--host without --http emits a stderr warning (loud, not silent)."""
    monkeypatch.setenv("HWLIB_DATA_DIR", str(bundle_dir))
    monkeypatch.setattr(sys, "argv", ["hwlib-mcp", "--host", "0.0.0.0"])

    class _StubServer:
        def run(self, *args: object, **kwargs: object) -> None:
            return None

    monkeypatch.setattr(
        "hwlib_mcp.__main__.build_server",
        lambda _data_dir: _StubServer(),
    )

    from hwlib_mcp import __main__ as cli  # noqa: PLC0415

    cli.main()

    captured = capsys.readouterr()
    assert "--host has no effect without --http" in captured.err
