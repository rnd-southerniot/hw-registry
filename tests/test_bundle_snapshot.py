"""Snapshot test for ``dist/index.json`` — reviewers see diffs in PRs.

Snapshots a deterministic build of the seed components against
``SOURCE_DATE_EPOCH=1714521600``. ``meta.git_sha`` is elided before
snapshot comparison since it changes on every commit and is not a
property of the registry contents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from syrupy.assertion import SnapshotAssertion

from tools.builder import build

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = REPO_ROOT / "library"

# Fixed timestamp so the snapshot is stable across builds.
FIXED_EPOCH = "1714521600"


def test_index_json_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", FIXED_EPOCH)
    build(LIBRARY, tmp_path)

    index: dict[str, Any] = json.loads((tmp_path / "index.json").read_text())

    # git_sha changes per commit; elide before snapshot diff so readers
    # see only registry-content changes.
    if isinstance(index.get("meta"), dict):
        index["meta"]["git_sha"] = "<elided-for-snapshot>"

    assert index == snapshot
