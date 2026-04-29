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

        missing_source = [f for f in REQUIRED_FILES if not (src_dist / f).is_file()]
        target_populated = all((target_dir / f).is_file() for f in REQUIRED_FILES)

        if missing_source:
            # If source is missing but target is populated, this is the
            # sdist->wheel round-trip case (sdist preserves data/, wheel
            # built from sdist re-uses it). Preserve what's there.
            # If source is missing and target is empty, halt with the
            # actionable error.
            if target_populated:
                return
            raise RuntimeError(
                f"hwlib-data build: bundle artifacts missing from {src_dist}: "
                f"{missing_source}\n"
                "Run `python -m tools.builder --out dist/` from the repo root "
                "before building this wheel."
            )

        # Source is present — always overwrite. Fresh data wins, even over
        # a previously-populated target. Defensive against COPY-based Docker
        # builds bringing in stale data files from a developer's local tree.
        target_dir.mkdir(parents=True, exist_ok=True)
        for f in REQUIRED_FILES:
            shutil.copy2(src_dist / f, target_dir / f)
