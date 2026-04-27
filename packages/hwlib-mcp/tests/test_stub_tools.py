"""Each stub tool returns the structured not_implemented shape."""

from __future__ import annotations

import pytest
from fastmcp import Client

STUB_TOOLS_AND_ALTERNATIVES = [
    ("hwlib_suggest_pinmap", "hwlib_check_pin_conflicts"),
    ("hwlib_generate_platformio_ini", "hwlib_get_drivers"),
    ("hwlib_generate_sdkconfig", "hwlib_get_drivers"),
    ("hwlib_get_kicad_refs", "hwlib_get with fields=['kicad']"),
]


@pytest.mark.parametrize("tool_name, expected_alternative", STUB_TOOLS_AND_ALTERNATIVES)
@pytest.mark.asyncio
async def test_stub_tool_returns_not_implemented(
    mcp_client: Client, tool_name: str, expected_alternative: str
) -> None:
    """Stub tools return {status, message, alternative_tool} — never raise."""
    # Pass minimal valid arguments per tool signature.
    args: dict[str, object]
    if tool_name == "hwlib_suggest_pinmap":
        args = {
            "board_id": "boards/espressif/esp32-s3-devkitc-1",
            "components": [{"ref": "sensors/sensirion/sht41"}],
        }
    elif tool_name == "hwlib_generate_platformio_ini" or tool_name == "hwlib_generate_sdkconfig":
        args = {
            "board_id": "boards/espressif/esp32-s3-devkitc-1",
            "components": ["sensors/sensirion/sht41"],
        }
    elif tool_name == "hwlib_get_kicad_refs":
        args = {"component_id": "sensors/sensirion/sht41"}
    else:  # pragma: no cover
        pytest.fail(f"unparameterised stub: {tool_name}")

    result = await mcp_client.call_tool(tool_name, args)
    payload = result.data
    assert isinstance(payload, dict), f"{tool_name}: expected dict, got {type(payload)}"
    assert payload["status"] == "not_implemented"
    assert "message" in payload
    assert payload["alternative_tool"] == expected_alternative
