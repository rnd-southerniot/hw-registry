"""Shared test fixtures: builds the bundle once + spins an in-memory MCP client."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastmcp import Client

# The MCP server lives under packages/hwlib-mcp/. Tests live alongside it.
# To use the in-tree builder + library, add the repo root to sys.path.
TESTS_DIR = Path(__file__).resolve().parent
PACKAGES_HWLIB_MCP_DIR = TESTS_DIR.parent
REPO_ROOT = PACKAGES_HWLIB_MCP_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from hwlib_mcp import build_server  # noqa: E402

from tools.builder import build  # noqa: E402


@pytest.fixture(scope="session")
def bundle_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the bundle once for the whole test session."""
    out = tmp_path_factory.mktemp("dist")
    build(REPO_ROOT / "library", out)
    return out


@pytest_asyncio.fixture
async def mcp_client(bundle_dir: Path) -> AsyncIterator[Client]:
    """Yield an in-memory FastMCP client connected to the server under test."""
    server = build_server(bundle_dir)
    async with Client(server) as client:
        yield client
