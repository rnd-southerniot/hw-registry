"""Resource handlers return structured bundle_missing errors, mirroring tools.

Resources return strings, so the structured error is JSON-serialized in
the response body. Agents that pattern-match on ``status`` see the same
shape they get from tools — symmetry keeps future tooling
interchangeable across the two surfaces.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client
from hwlib_mcp import build_server


@pytest.mark.asyncio
async def test_component_resource_returns_bundle_missing(tmp_path: Path) -> None:
    """``hwlib://component/{id}`` returns structured bundle_missing JSON."""
    server = build_server(tmp_path)  # empty dir
    async with Client(server) as client:
        response = await client.read_resource("hwlib://component/sensors/sensirion/sht41")
        assert response, "expected at least one content block"
        body = response[0].text  # type: ignore[union-attr]
        payload = json.loads(body)
        assert payload["status"] == "bundle_missing"
        assert "data_dir" in payload
        assert str(tmp_path) in payload["data_dir"]


@pytest.mark.asyncio
async def test_catalog_index_resource_returns_bundle_missing(tmp_path: Path) -> None:
    """``hwlib://catalog/index`` returns structured bundle_missing JSON."""
    server = build_server(tmp_path)
    async with Client(server) as client:
        response = await client.read_resource("hwlib://catalog/index")
        assert response
        body = response[0].text  # type: ignore[union-attr]
        payload = json.loads(body)
        assert payload["status"] == "bundle_missing"
