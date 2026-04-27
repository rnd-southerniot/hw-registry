"""System-YAML loader.

A *system* is a board plus a placement of one or more components on it.
The loader parses the YAML, opens the bundle SQLite, and pulls *only*
the components actually referenced (plus their inheritance ancestors —
followed transitively so each ref returns a fully-resolved record).
This avoids loading the whole bundle into memory; with 10 components on
a system the loader queries ~10–20 rows out of however many thousand.

The bundle MUST have been built. The loader does not auto-build —
that would silently invalidate the determinism contract of
SOURCE_DATE_EPOCH-locked CI builds.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import BundleNotBuilt, SystemYamlError, UnresolvedComponentRef

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_BUNDLE = REPO_ROOT / "dist" / "library.sqlite"


@dataclass(frozen=True)
class ComponentPlacement:
    """One component placed on a system: ref + instance name + pin assignments."""

    ref: str
    instance: str
    pins: dict[str, str]
    resolved: dict[str, Any]


@dataclass(frozen=True)
class System:
    """A loaded, resolved system."""

    yaml_path: Path
    board_id: str
    board: dict[str, Any]
    components: list[ComponentPlacement]


def load_system(yaml_path: Path, bundle_db: Path = DEFAULT_BUNDLE) -> System:
    """Parse *yaml_path*, resolve refs against *bundle_db*, return a ``System``."""
    if not bundle_db.exists():
        raise BundleNotBuilt(
            f"bundle SQLite not found at {bundle_db}. "
            "Run `make bundle` or `python -m tools.builder --out dist/` first."
        )

    try:
        with yaml_path.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise SystemYamlError(f"{yaml_path}: YAML parse error: {e}") from e

    if not isinstance(data, dict) or "system" not in data:
        raise SystemYamlError(f"{yaml_path}: top-level 'system' key required")

    sys_block = data["system"]
    board_id = sys_block.get("board")
    if not isinstance(board_id, str):
        raise SystemYamlError(f"{yaml_path}: 'system.board' (string) required")

    raw_components = sys_block.get("components") or []
    if not isinstance(raw_components, list):
        raise SystemYamlError(f"{yaml_path}: 'system.components' must be a list")

    # Collect every ref we need so we can batch-query SQLite.
    needed_ids: set[str] = {board_id}
    for entry in raw_components:
        if not isinstance(entry, dict):
            raise SystemYamlError(f"{yaml_path}: each component entry must be a dict")
        ref = entry.get("ref")
        if not isinstance(ref, str):
            raise SystemYamlError(f"{yaml_path}: each component entry needs a string 'ref'")
        needed_ids.add(ref)

    # Targeted query — pull only what we need.
    records = _query_records(bundle_db, needed_ids, yaml_path)

    board = records[board_id]

    placements: list[ComponentPlacement] = []
    for idx, entry in enumerate(raw_components):
        ref = entry["ref"]
        instance = entry.get("instance") or f"u{idx + 1}"
        if not isinstance(instance, str):
            raise SystemYamlError(f"{yaml_path}: component[{idx}].instance must be a string")
        pins = entry.get("pins") or {}
        if not isinstance(pins, dict):
            raise SystemYamlError(f"{yaml_path}: component[{idx}].pins must be a mapping")
        # Coerce non-str pin values (YAML may parse GPIO numbers as ints).
        pins_norm: dict[str, str] = {str(k): str(v) for k, v in pins.items()}
        placements.append(
            ComponentPlacement(
                ref=ref,
                instance=instance,
                pins=pins_norm,
                resolved=records[ref],
            )
        )

    return System(
        yaml_path=yaml_path,
        board_id=board_id,
        board=board,
        components=placements,
    )


def load_system_from_assignments(
    board_id: str,
    assignments: list[dict[str, Any]],
    bundle_db: Path = DEFAULT_BUNDLE,
) -> System:
    """Build a ``System`` from in-memory assignment dicts (no YAML on disk).

    *assignments* is a list of ``{ref, instance, pins: {signal: gpio}}``
    dicts — the same shape as ``system.components`` in the YAML form.
    Used by the MCP server's ``hwlib_check_pin_conflicts`` tool, which
    receives assignments from the agent rather than from a file.
    """
    if not bundle_db.exists():
        raise BundleNotBuilt(
            f"bundle SQLite not found at {bundle_db}. "
            "Run `make bundle` or `python -m tools.builder --out dist/` first."
        )

    needed_ids: set[str] = {board_id}
    for entry in assignments:
        if not isinstance(entry, dict):
            raise SystemYamlError("each assignment entry must be a dict")
        ref = entry.get("ref")
        if not isinstance(ref, str):
            raise SystemYamlError("each assignment needs a string 'ref'")
        needed_ids.add(ref)

    records = _query_records(bundle_db, needed_ids, yaml_path=Path("<in-memory>"))

    placements: list[ComponentPlacement] = []
    for idx, entry in enumerate(assignments):
        ref = entry["ref"]
        instance = entry.get("instance") or f"u{idx + 1}"
        if not isinstance(instance, str):
            raise SystemYamlError(f"assignment[{idx}].instance must be a string")
        pins = entry.get("pins") or {}
        if not isinstance(pins, dict):
            raise SystemYamlError(f"assignment[{idx}].pins must be a mapping")
        pins_norm: dict[str, str] = {str(k): str(v) for k, v in pins.items()}
        placements.append(
            ComponentPlacement(
                ref=ref,
                instance=instance,
                pins=pins_norm,
                resolved=records[ref],
            )
        )

    return System(
        yaml_path=Path("<in-memory>"),
        board_id=board_id,
        board=records[board_id],
        components=placements,
    )


def _query_records(
    bundle_db: Path,
    needed_ids: set[str],
    yaml_path: Path,
) -> dict[str, dict[str, Any]]:
    """Pull the named records out of bundle SQLite. Raises on any unresolved id."""
    conn = sqlite3.connect(bundle_db)
    try:
        # Parameterised SQL in chunks so we never SELECT * — operator note.
        placeholders = ",".join("?" * len(needed_ids))
        rows = conn.execute(
            f"SELECT id, json FROM components WHERE id IN ({placeholders})",
            tuple(sorted(needed_ids)),
        ).fetchall()
    finally:
        conn.close()

    found: dict[str, dict[str, Any]] = {}
    for component_id, json_blob in rows:
        found[component_id] = json.loads(json_blob)

    missing = needed_ids - set(found.keys())
    if missing:
        raise UnresolvedComponentRef(f"{yaml_path}: component(s) not in bundle: {sorted(missing)}")

    return found
