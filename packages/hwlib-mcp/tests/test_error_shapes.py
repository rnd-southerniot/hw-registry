"""Error responses are structured shapes the agent can pattern-match on."""

from __future__ import annotations

import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_hwlib_get_bogus_id_returns_suggestions(mcp_client: Client) -> None:
    """Typoed slug returns {status: not_found, suggestions: [closest IDs]}."""
    result = await mcp_client.call_tool(
        "hwlib_get",
        {"id": "sensors/sensirion/sht40"},  # typo: 40 vs 41
    )
    payload = result.data
    assert payload["status"] == "not_found"
    assert payload["id"] == "sensors/sensirion/sht40"
    # The fuzzy-match engine must include the canonical SHT41 id.
    assert "sensors/sensirion/sht41" in payload["suggestions"]
    # The message text mentions the closest matches so an LLM that doesn't
    # parse `suggestions` still gets the hint.
    assert "sht41" in payload["message"]


@pytest.mark.asyncio
async def test_hwlib_get_drivers_bogus_component_404(mcp_client: Client) -> None:
    """get_drivers on a missing component also returns the suggestion shape."""
    result = await mcp_client.call_tool(
        "hwlib_get_drivers", {"component_id": "sensors/nonexistent/widget"}
    )
    payload = result.data
    assert payload["status"] == "not_found"
    assert "suggestions" in payload


@pytest.mark.asyncio
async def test_hwlib_check_pin_conflicts_unresolved_ref(mcp_client: Client) -> None:
    """A bogus component ref in the assignment returns unresolved_ref status."""
    result = await mcp_client.call_tool(
        "hwlib_check_pin_conflicts",
        {
            "board_id": "boards/espressif/esp32-s3-devkitc-1",
            "components": [
                {
                    "ref": "sensors/nonexistent/widget",
                    "instance": "u2",
                    "pins": {"SDA": "GPIO8", "SCL": "GPIO9"},
                }
            ],
        },
    )
    payload = result.data
    assert payload["status"] == "unresolved_ref"


@pytest.mark.asyncio
async def test_hwlib_search_invalid_query(mcp_client: Client) -> None:
    """Empty query → invalid_argument shape."""
    result = await mcp_client.call_tool("hwlib_search", {"query": ""})
    payload = result.data
    assert payload["status"] == "invalid_argument"
    assert payload["field"] == "query"
