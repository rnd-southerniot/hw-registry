"""Hatchling build hook: stage dist/library.{json,sqlite,index.json} into the wheel.

Runs before sdist/wheel packaging. The bundle in ``dist/`` at the repo root
gets copied into ``src/hwlib_data/data/`` so the wheel ships with the data
embedded. Fails fast if the bundle hasn't been built — same BundleNotFound
contract pattern as hwlib-mcp.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

REQUIRED_FILES = ("library.json", "library.sqlite", "index.json")


class CustomBuildHook(BuildHookInterface):
    """Stage bundle artifacts into the package's ``data/`` directory."""

    PLUGIN_NAME = "hwlib-data-bundle-stage"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        package_dir = Path(__file__).resolve().parent
        # packages/hwlib-data/build_hook.py -> repo_root is parents[2].
        repo_root = package_dir.parent.parent
        src_dist = repo_root / "dist"
        target_dir = package_dir / "src" / "hwlib_data" / "data"

        # Idempotency: if the target is already populated (e.g. wheel build
        # from an sdist that captured the staged files), preserve what's
        # there rather than try to re-copy from a path that may not exist
        # in the build environment.
        if all((target_dir / f).is_file() for f in REQUIRED_FILES):
            return

        missing = [f for f in REQUIRED_FILES if not (src_dist / f).is_file()]
        if missing:
            raise RuntimeError(
                f"hwlib-data build: bundle artifacts missing from {src_dist}: "
                f"{missing}\n"
                "Run `python -m tools.builder --out dist/` from the repo root "
                "before building this wheel."
            )

        target_dir.mkdir(parents=True, exist_ok=True)
        for f in REQUIRED_FILES:
            shutil.copy2(src_dist / f, target_dir / f)
