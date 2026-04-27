"""Server fails fast and operator-friendly when the bundle is missing."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client
from hwlib_mcp import build_server


@pytest.mark.asyncio
async def test_tools_return_bundle_missing_status(tmp_path: Path) -> None:
    """When the configured data dir has no library.sqlite, every active
    bundle-touching tool returns ``{"status": "bundle_missing", ...}``.

    Specifically asserted shape — not a raw exception, not an ad-hoc dict.
    Agents pattern-match on ``status`` to distinguish bundle-missing from
    other error classes.
    """
    server = build_server(tmp_path)  # empty directory, no library.sqlite
    async with Client(server) as client:
        for tool_name, args in [
            ("hwlib_search", {"query": "anything"}),
            ("hwlib_list", {}),
            ("hwlib_get", {"id": "sensors/sensirion/sht41"}),
            ("hwlib_get_drivers", {"component_id": "sensors/sensirion/sht41"}),
            (
                "hwlib_compatible_modules",
                {"board_id": "boards/espressif/esp32-s3-devkitc-1"},
            ),
            (
                "hwlib_check_pin_conflicts",
                {
                    "board_id": "boards/espressif/esp32-s3-devkitc-1",
                    "components": [],
                },
            ),
        ]:
            result = await client.call_tool(tool_name, args)
            payload = result.data
            assert isinstance(payload, dict), (
                f"{tool_name}: expected dict response, got {type(payload).__name__}"
            )
            assert payload.get("status") == "bundle_missing", (
                f"{tool_name}: expected bundle_missing status, got {payload!r}"
            )
            assert "data_dir" in payload
            assert "message" in payload


def test_main_exits_nonzero_on_missing_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`python -m hwlib_mcp` with no bundle prints a message and exits non-zero."""
    monkeypatch.setenv("HWLIB_DATA_DIR", str(tmp_path))
    from hwlib_mcp import __main__ as cli  # noqa: PLC0415

    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
