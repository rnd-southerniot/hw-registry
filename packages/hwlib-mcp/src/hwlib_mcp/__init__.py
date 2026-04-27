"""hwlib-mcp: an MCP server exposing the hw-registry component bundle to AI agents."""

from .server import build_server

__all__ = ["build_server"]
