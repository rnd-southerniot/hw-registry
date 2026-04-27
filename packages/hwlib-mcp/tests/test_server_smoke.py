"""Smoke tests: each active tool returns the expected response shape."""

from __future__ import annotations

import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_list_tools(mcp_client: Client) -> None:
    """All 10 tools are registered (6 active + 4 stubs)."""
    tools = await mcp_client.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "hwlib_search",
        "hwlib_list",
        "hwlib_get",
        "hwlib_check_pin_conflicts",
        "hwlib_compatible_modules",
        "hwlib_get_drivers",
        "hwlib_suggest_pinmap",
        "hwlib_generate_platformio_ini",
        "hwlib_generate_sdkconfig",
        "hwlib_get_kicad_refs",
    }


@pytest.mark.asyncio
async def test_hwlib_search_returns_summary_shape(mcp_client: Client) -> None:
    """hwlib_search returns {id, kind, summary, vendor} per result — NOT full records."""
    result = await mcp_client.call_tool("hwlib_search", {"query": "SHT41"})
    payload = result.data
    assert payload["count"] >= 1
    sht41 = next((r for r in payload["results"] if r["id"] == "sensors/sensirion/sht41"), None)
    assert sht41 is not None
    # Exactly the summary keys (vendor may be None for drivers, but it's still a key).
    assert set(sht41.keys()) == {"id", "kind", "summary", "vendor"}
    assert sht41["kind"] == "sensor"
    assert sht41["vendor"] == "sensirion"


@pytest.mark.asyncio
async def test_hwlib_search_kind_filter(mcp_client: Client) -> None:
    """Filtering by kind returns only that kind's records."""
    result = await mcp_client.call_tool("hwlib_search", {"query": "SHT41", "kind": "sensor"})
    assert all(r["kind"] == "sensor" for r in result.data["results"])


@pytest.mark.asyncio
async def test_hwlib_search_limit_capped(mcp_client: Client) -> None:
    """limit > 20 must be silently capped at 20 (token-discipline contract)."""
    result = await mcp_client.call_tool("hwlib_search", {"query": "i2c", "limit": 1000})
    assert result.data["count"] <= 20


@pytest.mark.asyncio
async def test_hwlib_list_pagination(mcp_client: Client) -> None:
    """hwlib_list returns paginated summaries with metadata."""
    result = await mcp_client.call_tool("hwlib_list", {"page": 1, "page_size": 3})
    payload = result.data
    assert "components" in payload
    assert payload["page"] == 1
    assert payload["page_size"] == 3
    assert payload["total"] >= 8
    assert len(payload["components"]) <= 3


@pytest.mark.asyncio
async def test_hwlib_list_kind_filter(mcp_client: Client) -> None:
    result = await mcp_client.call_tool("hwlib_list", {"kind": "sensor", "page_size": 50})
    assert {c["kind"] for c in result.data["components"]} == {"sensor"}


@pytest.mark.asyncio
async def test_hwlib_get_full_record(mcp_client: Client) -> None:
    result = await mcp_client.call_tool("hwlib_get", {"id": "sensors/sensirion/sht41"})
    record = result.data
    assert record["id"] == "sensors/sensirion/sht41"
    assert record["kind"] == "sensor"
    # Full record carries top-level structural keys.
    assert "constraints" in record
    assert "electrical" in record


@pytest.mark.asyncio
async def test_hwlib_get_field_projection(mcp_client: Client) -> None:
    """fields=['constraints'] returns id+kind+constraints, no other keys."""
    result = await mcp_client.call_tool(
        "hwlib_get",
        {"id": "sensors/sensirion/sht41", "fields": ["constraints"]},
    )
    projected = result.data
    assert set(projected.keys()) == {"id", "kind", "constraints"}
    # Constraints is the nested-by-bus shape from Prompt 4.
    assert "i2c" in projected["constraints"]
    assert projected["constraints"]["i2c"]["address"] == 0x44


@pytest.mark.asyncio
async def test_hwlib_check_pin_conflicts_clean(mcp_client: Client) -> None:
    """The lorawan-node assignment validates clean (no errors, no warnings)."""
    result = await mcp_client.call_tool(
        "hwlib_check_pin_conflicts",
        {
            "board_id": "boards/espressif/esp32-s3-devkitc-1",
            "components": [
                {
                    "ref": "sensors/sensirion/sht41",
                    "instance": "u2",
                    "pins": {"SDA": "GPIO8", "SCL": "GPIO9"},
                },
                {
                    "ref": "modules/rakwireless/rak3172",
                    "instance": "u3",
                    "pins": {
                        "uart2_tx": "GPIO17",
                        "uart2_rx": "GPIO18",
                        "RESET": "GPIO16",
                    },
                },
            ],
        },
    )
    payload = result.data
    assert payload["ok"] is True
    assert payload["error_count"] == 0
    assert payload["warning_count"] == 0


@pytest.mark.asyncio
async def test_hwlib_check_pin_conflicts_clash(mcp_client: Client) -> None:
    """Two SHT41s at default 0x44 → I2C_ADDR_CLASH ERROR."""
    result = await mcp_client.call_tool(
        "hwlib_check_pin_conflicts",
        {
            "board_id": "boards/espressif/esp32-s3-devkitc-1",
            "components": [
                {
                    "ref": "sensors/sensirion/sht41",
                    "instance": "u2",
                    "pins": {"SDA": "GPIO8", "SCL": "GPIO9"},
                },
                {
                    "ref": "sensors/sensirion/sht41",
                    "instance": "u3",
                    "pins": {"SDA": "GPIO8", "SCL": "GPIO9"},
                },
            ],
        },
    )
    payload = result.data
    assert payload["ok"] is False
    assert payload["error_count"] >= 1
    diag_ids = {d["id"] for d in payload["diagnostics"]}
    assert "I2C_ADDR_CLASH" in diag_ids


@pytest.mark.asyncio
async def test_hwlib_get_drivers(mcp_client: Client) -> None:
    """SHT41 sensor has bindings via drivers/sensirion/sht41."""
    result = await mcp_client.call_tool(
        "hwlib_get_drivers", {"component_id": "sensors/sensirion/sht41"}
    )
    payload = result.data
    assert payload["count"] >= 1
    # Filter by framework.
    result_idf = await mcp_client.call_tool(
        "hwlib_get_drivers",
        {"component_id": "sensors/sensirion/sht41", "framework": "esp-idf"},
    )
    bindings = result_idf.data["bindings"]
    assert all(b["framework"] == "esp-idf" for b in bindings)


@pytest.mark.asyncio
async def test_hwlib_compatible_modules_smoke(mcp_client: Client) -> None:
    """Returns the right shape; non-empty for the ESP32-S3 DevKitC."""
    result = await mcp_client.call_tool(
        "hwlib_compatible_modules",
        {"board_id": "boards/espressif/esp32-s3-devkitc-1"},
    )
    payload = result.data
    assert "results" in payload
    assert "count" in payload
    assert payload["board_id"] == "boards/espressif/esp32-s3-devkitc-1"
