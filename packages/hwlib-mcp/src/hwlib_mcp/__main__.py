"""``hwlib-mcp`` CLI entry: stdio by default, ``--http`` for hosted deployments."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from . import data
from .server import build_server


def _resolve_data_dir() -> Path:
    """Read HWLIB_DATA_DIR or fall back to a dev-friendly default.

    Default looks up to the repo root from this file (works for editable
    installs). Production wheels will set HWLIB_DATA_DIR explicitly via
    the hwlib-data package's data_path() helper (Prompt 10).
    """
    env = os.environ.get("HWLIB_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    # Editable-install fallback: packages/hwlib-mcp/src/hwlib_mcp/__main__.py
    # → repo_root = parents[4]
    here = Path(__file__).resolve()
    repo_root = here.parents[4]
    return repo_root / "dist"


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="hwlib-mcp",
        description="MCP server for the hw-registry component bundle.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run with Streamable HTTP transport instead of stdio.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for --http mode (default 8080).",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Stderr log level.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    data_dir = _resolve_data_dir()

    # Fail fast and operator-friendly on missing bundle. The loader's own
    # check fires per-tool-call too, but a clean startup error is what
    # an operator sees when they wire the server up wrong.
    if not data.bundle_present(data_dir):
        sys.stderr.write(
            f"hwlib-mcp: library.sqlite not found at {data_dir}.\n"
            "  Run `python -m tools.builder --out dist/` and/or set\n"
            "  HWLIB_DATA_DIR to a directory that contains library.sqlite.\n"
        )
        sys.exit(2)

    server = build_server(data_dir)

    if args.http:
        server.run(transport="streamable-http", port=args.port)
    else:
        server.run()


if __name__ == "__main__":
    main()
