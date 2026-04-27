"""Semantic validators for the hw-registry YAML library.

Schemas (under ``schemas/``) catch *structural* errors — missing required
fields, wrong types, regex violations. This tool catches *semantic* errors
that span multiple files or require parsing intent:

- ``slug-equals-path`` — the ``id`` field must equal the YAML's relative
  path under ``library/`` minus the ``.yaml`` extension.
- ``refs-resolve`` — every ref in ``inherits_from``, ``contains[].ref``,
  ``applies_to``, and ``drivers`` must point at a YAML that exists. The
  optional ``@<semver>`` suffix is stripped before the filesystem lookup
  (the version pin is for the bundle resolver, not the path lookup).
- ``inheritance-cycle`` — the ``inherits_from`` DAG must be acyclic.
- ``all`` — runs the three above and aggregates their results.

Empty or missing ``library/`` exits 0 cleanly (zero components is not an
error). Errors print to stderr; exit code is 1 on any failure.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import click
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LIBRARY = REPO_ROOT / "library"

# Component ref with optional @semver suffix. Group 1 captures the slug-only
# portion (kind/vendor/part); the rest of the regex matches an optional
# @x.y.z[-prerelease][+build] tail that we ignore for filesystem lookup.
_REF_RE = re.compile(
    r"^([a-z]+/[a-z0-9-]+/[a-z0-9-]+)"
    r"(?:@\d+\.\d+\.\d+"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)?$"
)


def _strip_version(ref: str) -> str | None:
    """Return the slug-only portion of a ref. None if the ref is malformed."""
    m = _REF_RE.match(ref)
    return m.group(1) if m else None


def _walk(library: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    """Yield ``(path, parsed_yaml)`` for every ``*.yaml`` under *library*.

    Empty / non-existent / unreadable library directory yields nothing.
    """
    if not library.exists() or not library.is_dir():
        return
    for yaml_file in sorted(library.rglob("*.yaml")):
        try:
            with yaml_file.open() as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            click.echo(
                f"{_rel(yaml_file)}: YAML parse error — {e}",
                err=True,
            )
            continue
        if isinstance(data, dict):
            yield yaml_file, data


def _path_to_slug(yaml_file: Path, library: Path) -> str:
    """Convert ``library/boards/foo/bar.yaml`` → ``boards/foo/bar``."""
    return str(yaml_file.relative_to(library).with_suffix(""))


def _rel(p: Path) -> str:
    """Pretty-print a path relative to repo root if possible."""
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def _collect_refs(data: dict[str, Any]) -> list[str]:
    """Extract every component ref from a single component's parsed YAML."""
    refs: list[str] = []
    for key in ("inherits_from", "applies_to", "drivers"):
        value = data.get(key) or []
        refs.extend(str(v) for v in value)
    for c in data.get("contains") or []:
        if isinstance(c, dict) and "ref" in c:
            refs.append(str(c["ref"]))
    return refs


def _count_yamls(library: Path) -> int:
    if not library.exists() or not library.is_dir():
        return 0
    return sum(1 for _ in library.rglob("*.yaml"))


# --- Core check functions (separable for testing) -------------------------


def run_slug_check(library: Path) -> list[str]:
    """Each YAML's ``id`` field must equal its slug (relative path − .yaml)."""
    errors: list[str] = []
    for yaml_file, data in _walk(library):
        expected = _path_to_slug(yaml_file, library)
        actual = data.get("id")
        if actual != expected:
            errors.append(f"{_rel(yaml_file)}: id={actual!r} does not match path slug {expected!r}")
    return errors


def run_refs_check(library: Path) -> list[str]:
    """Every ref must point at an existing YAML (after @semver strip)."""
    errors: list[str] = []
    for yaml_file, data in _walk(library):
        for ref in _collect_refs(data):
            stripped = _strip_version(ref)
            if stripped is None:
                errors.append(f"{_rel(yaml_file)}: malformed ref {ref!r}")
                continue
            target = library / f"{stripped}.yaml"
            if not target.exists():
                errors.append(f"{_rel(yaml_file)}: ref {ref!r} → {_rel(target)} not found")
    return errors


def run_cycle_check(library: Path) -> list[str]:
    """Detect cycles in the ``inherits_from`` DAG via three-color DFS."""
    edges: dict[str, list[str]] = {}
    for _path, data in _walk(library):
        node = data.get("id")
        if not isinstance(node, str):
            continue
        targets: list[str] = []
        for ref in data.get("inherits_from") or []:
            stripped = _strip_version(str(ref))
            if stripped is not None:
                targets.append(stripped)
        edges[node] = targets

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(edges, WHITE)
    cycles: list[list[str]] = []

    def dfs(node: str, path: list[str]) -> None:
        color[node] = GRAY
        for nxt in edges.get(node, []):
            if nxt not in color:
                # Unresolved ref — refs-resolve will report it; skip here.
                continue
            if color[nxt] == GRAY:
                cycles.append(path[path.index(nxt) :] + [nxt])
            elif color[nxt] == WHITE:
                dfs(nxt, path + [nxt])
        color[node] = BLACK

    for node in edges:
        if color[node] == WHITE:
            dfs(node, [node])

    return [f"inheritance cycle: {' → '.join(c)}" for c in cycles]


def _emit(errors: list[str], check_name: str, count: int) -> None:
    if errors:
        click.echo(
            f"{check_name}: {len(errors)} error(s) across {count} component(s):",
            err=True,
        )
        for e in errors:
            click.echo(f"  {e}", err=True)
        sys.exit(1)
    click.echo(f"{check_name}: {count} component(s) checked, 0 errors")


# --- CLI ------------------------------------------------------------------


@click.group()
@click.option(
    "--root",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_LIBRARY,
    show_default=True,
    help="Path to the library/ directory to validate.",
)
@click.pass_context
def cli(ctx: click.Context, root: Path) -> None:
    """Semantic validators for the hw-registry YAML library."""
    ctx.ensure_object(dict)
    ctx.obj["library"] = root


@cli.command("slug-equals-path")
@click.pass_context
def slug_cmd(ctx: click.Context) -> None:
    """Assert each YAML's `id` equals its relative path under library/ minus .yaml."""
    library: Path = ctx.obj["library"]
    _emit(run_slug_check(library), "slug-equals-path", _count_yamls(library))


@cli.command("refs-resolve")
@click.pass_context
def refs_cmd(ctx: click.Context) -> None:
    """Confirm every ref (inherits_from / contains / applies_to / drivers) exists."""
    library: Path = ctx.obj["library"]
    _emit(run_refs_check(library), "refs-resolve", _count_yamls(library))


@cli.command("inheritance-cycle")
@click.pass_context
def cycles_cmd(ctx: click.Context) -> None:
    """Detect cycles in the inherits_from DAG."""
    library: Path = ctx.obj["library"]
    _emit(run_cycle_check(library), "inheritance-cycle", _count_yamls(library))


@cli.command("all")
@click.pass_context
def all_cmd(ctx: click.Context) -> None:
    """Run every validator. Exit non-zero on any error."""
    library: Path = ctx.obj["library"]
    errors = run_slug_check(library) + run_refs_check(library) + run_cycle_check(library)
    _emit(errors, "all", _count_yamls(library))


def main() -> None:
    """Console-script entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
