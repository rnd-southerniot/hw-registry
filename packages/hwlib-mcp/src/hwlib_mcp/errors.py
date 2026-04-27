"""Structured error response builders.

Every tool returns one of these *shapes*, never raises. Agents pattern-
match on ``status`` to route around failures instead of retrying blindly.
The shapes are part of the protocol contract — adding new shapes here is
a versioning event.
"""

from __future__ import annotations

from typing import Any


def not_found(component_id: str, suggestions: list[str]) -> dict[str, Any]:
    """The requested component id does not exist in the bundle."""
    return {
        "status": "not_found",
        "id": component_id,
        "suggestions": suggestions,
        "message": (
            f"No component with id {component_id!r}. "
            + (f"Closest matches: {', '.join(suggestions)}" if suggestions else "No close matches.")
        ),
    }


def bundle_missing(data_dir: str) -> dict[str, Any]:
    """``library.sqlite`` is not present at the configured data dir."""
    return {
        "status": "bundle_missing",
        "data_dir": data_dir,
        "message": (
            f"library.sqlite not found at {data_dir}. Run "
            "`python -m tools.builder --out dist/` and restart the server."
        ),
    }


def invalid_argument(field: str, message: str) -> dict[str, Any]:
    """A tool argument failed structural validation."""
    return {
        "status": "invalid_argument",
        "field": field,
        "message": message,
    }


def checker_unavailable() -> dict[str, Any]:
    """The conflict-checker module could not be imported.

    Currently raised when ``hwlib-mcp`` is installed standalone (without
    the root ``hw-registry-tools`` package). Prompt 10's packaging story
    will turn this into a hard runtime dependency; for MVP, the tool
    degrades gracefully rather than 500-ing the agent.
    """
    return {
        "status": "checker_unavailable",
        "message": (
            "The pin-conflict checker module is not installed alongside "
            "this MCP server. Install hw-registry-tools (the root "
            "distribution) for full functionality."
        ),
        "alternative_tool": "hwlib_get",
    }


def not_implemented(message: str, alternative_tool: str) -> dict[str, Any]:
    """A stub tool — return a structured shape, never raise."""
    return {
        "status": "not_implemented",
        "message": message,
        "alternative_tool": alternative_tool,
    }
