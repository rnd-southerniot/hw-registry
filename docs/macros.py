"""mkdocs-macros hooks — exposes live counts from dist/index.json to pages."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_JSON = REPO_ROOT / "dist" / "index.json"

KIND_ORDER = ["board", "module", "chip", "sensor", "driver", "connector"]


def define_env(env) -> None:  # noqa: ANN001
    """Register macros at mkdocs build start."""
    if not INDEX_JSON.exists():
        # Fail loudly rather than silently rendering "0" everywhere — the
        # build expects an up-to-date dist/.
        raise FileNotFoundError(
            f"dist/index.json not found at {INDEX_JSON}.\n"
            "Run `python -m tools.builder --out dist/` from the repo root "
            "before building the docs site."
        )

    data = json.loads(INDEX_JSON.read_text())
    meta = data.get("meta", {})
    counts: dict[str, int] = meta.get("count_by_kind", {})
    total: int = meta.get("total_count", sum(counts.values()))
    git_sha: str = meta.get("git_sha", "unknown")[:7]

    @env.macro
    def library_total() -> int:
        return total

    @env.macro
    def library_count_summary() -> str:
        parts: list[str] = []
        for kind in KIND_ORDER:
            n = counts.get(kind, 0)
            if not n:
                continue
            plural = "s" if n != 1 else ""
            parts.append(f"{n} {kind}{plural}")
        return ", ".join(parts) if parts else "library is empty"

    @env.macro
    def library_git_sha() -> str:
        return git_sha
