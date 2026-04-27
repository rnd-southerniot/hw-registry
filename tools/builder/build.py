"""Bundle builder pipeline.

Walks ``library/``, validates each YAML against its Pydantic model,
resolves the ``inherits_from`` chain (depth-first, cycle-detected,
deep-merged with child winning and ``overrides`` applied last), and
emits three deterministic artifacts under ``dist/``:

- ``library.json`` — the full resolved tree, sorted keys, 2-space indent.
- ``library.sqlite`` — components table with FTS5 search, page_size 4096.
- ``index.json`` — small (≤50 KB) summary for fast catalog browsing.

Determinism: sorted keys everywhere; ``SOURCE_DATE_EPOCH`` honoured for
the meta timestamp; SQLite written in id-sorted INSERT order, then
``VACUUM``'d to canonicalise free-page layout.

Resolver semantics live in pydantic_models/module.py's TODO comment;
the soft-fallback policy is documented on ``_coerce_pin_overrides``.
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import subprocess
import warnings
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import yaml
from pydantic import ValidationError

from pydantic_models import (
    Board,
    Chip,
    Connector,
    Driver,
    Identifiable,
    Module,
    Sensor,
)

from .errors import (
    AltFunctionShorthandWarning,
    BuilderError,
    ComponentValidationError,
    InheritanceCycleError,
    MismatchedOverrideShorthand,
    UnknownOverrideKey,
    UnresolvedRefError,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LIBRARY = REPO_ROOT / "library"
DEFAULT_OUT = REPO_ROOT / "dist"

KIND_MODELS: dict[str, type[Identifiable]] = {
    "board": Board,
    "module": Module,
    "chip": Chip,
    "sensor": Sensor,
    "connector": Connector,
    "driver": Driver,
}

BUNDLE_SCHEMA_VERSION = 1


# --- Discovery + first-pass validation -----------------------------------


def discover(library: Path) -> dict[str, dict[str, Any]]:
    """Walk *library*, validate each YAML, return ``{id: dumped_dict}``.

    Re-validates against the kind's Pydantic model; the filesystem is not
    trusted to have already passed schema validation. Pydantic dumps with
    ``by_alias=True`` so ``apiVersion`` (camel) survives the round-trip,
    and ``exclude_unset=True`` so fields the YAML did not explicitly set
    do not appear in the dump. The latter matters during inheritance:
    an unset ``pins`` field on a Module must NOT replace the parent
    chip's pins (``list-replacement`` merge rule), it must let them flow
    through. ``exclude_unset`` is what makes that distinction reliable.
    """
    raw: dict[str, dict[str, Any]] = {}
    for yaml_file in sorted(library.rglob("*.yaml")):
        try:
            with yaml_file.open() as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ComponentValidationError(yaml_file, f"YAML parse error: {e}") from e

        if not isinstance(data, dict):
            continue

        kind = data.get("kind")
        if kind not in KIND_MODELS:
            raise ComponentValidationError(yaml_file, f"unknown kind {kind!r}")

        model = KIND_MODELS[kind]
        try:
            instance = model.model_validate(data)
        except ValidationError as e:
            raise ComponentValidationError(yaml_file, e) from e

        component_id = instance.id
        if component_id in raw:
            raise ComponentValidationError(
                yaml_file, f"duplicate id {component_id!r} (already seen)"
            )
        raw[component_id] = instance.model_dump(by_alias=True, mode="json", exclude_unset=True)
    return raw


# --- Resolver ------------------------------------------------------------


def _strip_version(ref: str) -> str:
    """Strip optional ``@semver`` suffix from a component ref."""
    return ref.split("@", 1)[0]


def _deep_merge(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """Child wins on dict-keys (deep update); child's lists fully replace parent's."""
    result: dict[str, Any] = dict(parent)
    for key, value in child.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve(
    component_id: str,
    raw: dict[str, dict[str, Any]],
    visited: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Recursively resolve the ``inherits_from`` chain for *component_id*.

    Returns the merged record. Raises ``InheritanceCycleError`` on a cycle,
    ``UnresolvedRefError`` on a dangling ``inherits_from`` ref.
    """
    if component_id in visited:
        chain = " → ".join(visited + (component_id,))
        raise InheritanceCycleError(f"inheritance cycle: {chain}")

    record = raw.get(component_id)
    if record is None:
        raise UnresolvedRefError(f"component not found: {component_id!r}")

    merged: dict[str, Any] = {}
    for parent_ref in record.get("inherits_from") or []:
        parent_id = _strip_version(str(parent_ref))
        parent_resolved = resolve(parent_id, raw, visited + (component_id,))
        merged = _deep_merge(merged, parent_resolved)

    merged = _deep_merge(merged, record)

    overrides = record.get("overrides")
    if overrides:
        kind = record.get("kind")
        if kind not in KIND_MODELS:
            raise BuilderError(f"{component_id}: unknown kind {kind!r}")
        merged = _apply_overrides(merged, overrides, KIND_MODELS[kind], component_id)
        # Drop the now-applied overrides block from the resolved record.
        merged.pop("overrides", None)

    return merged


def _apply_overrides(
    merged: dict[str, Any],
    overrides: dict[str, Any],
    model_class: type[Identifiable],
    component_id: str,
) -> dict[str, Any]:
    """Apply the overrides block.

    - Validates each top-level override key against the kind's model fields.
    - Coerces ``overrides.pins[].alt_functions`` shorthand strings.
    - Dict values deep-merge; list values replace.
    """
    valid_fields = set(model_class.model_fields.keys())

    for key, value in overrides.items():
        if key not in valid_fields:
            raise UnknownOverrideKey(
                f"{component_id}: override key {key!r} is not a field on "
                f"{model_class.__name__}; valid keys are {sorted(valid_fields)}"
            )

        if key == "pins":
            value = _coerce_pin_overrides(value, merged.get("pins") or [], component_id)

        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def _coerce_pin_overrides(
    override_pins: list[Any],
    parent_pins: list[Any],
    component_id: str,
) -> list[dict[str, Any]]:
    """Coerce shorthand ``alt_functions`` string entries into AltFunction dicts.

    Per pin, look up the parent component's matching ``AltFunction`` (by
    ``function`` name) and copy it. Mixed shorthand-and-dict forms are
    supported; dict entries with a known ``function`` overlay parent fields
    per-key.

    **Unmatched shorthand is NOT an error.** A module legitimately extends
    its parent's function vocabulary — RAK3172 exposes vendor-specific
    RUI3 AT-firmware functions on pins whose underlying STM32WLE5JC has
    no concept of them. Strict-fail on unmatched shorthand would block
    legitimate extension and force every Module to inline its parent
    chip's full AltFunction surface or abandon shorthand entirely.

    Instead: unmatched shorthand coerces to a minimum-info
    ``{function: <name>}`` entry AND emits an
    ``AltFunctionShorthandWarning`` so reviewers can spot typos in CI
    logs. A typo PR shows the warning, the reviewer asks "did you mean
    ``uart_rx``?", author fixes, warning goes away. Legitimate
    extensions show the warning indefinitely until the parent chip YAML
    is enriched with the new function — at which point shorthand starts
    resolving cleanly and the warning self-clears.

    Structural type errors (``alt_functions`` entry that is neither
    string nor dict) DO raise ``MismatchedOverrideShorthand`` — that is
    a YAML-shape bug, distinct from a function-vocabulary extension.
    """
    parent_pin_map: dict[str, dict[str, Any]] = {}
    for p in parent_pins:
        if isinstance(p, dict) and "id" in p:
            parent_pin_map[p["id"]] = p

    out: list[dict[str, Any]] = []
    for pin in override_pins:
        if not isinstance(pin, dict):
            continue
        coerced_pin = dict(pin)

        if "alt_functions" in coerced_pin:
            parent_pin = parent_pin_map.get(coerced_pin.get("id", ""))
            parent_alts = (parent_pin.get("alt_functions", []) if parent_pin else []) or []
            parent_alt_map: dict[str, dict[str, Any]] = {
                a["function"]: a for a in parent_alts if isinstance(a, dict) and "function" in a
            }

            new_alts: list[dict[str, Any]] = []
            for alt in coerced_pin["alt_functions"]:
                if isinstance(alt, str):
                    if alt in parent_alt_map:
                        new_alts.append(dict(parent_alt_map[alt]))
                    else:
                        # Soft fallback — see docstring. Inferred path
                        # mirrors the slug-equals-path rule from CLAUDE.md
                        # so no extra plumbing is needed to point reviewers
                        # at the offending YAML.
                        inferred_path = f"library/{component_id}.yaml"
                        warnings.warn(
                            f"{inferred_path}: alt_function {alt!r} on pin "
                            f"{coerced_pin.get('id', '<?>')!r} not found in "
                            "parent's AltFunction table; treating as new function.",
                            AltFunctionShorthandWarning,
                            stacklevel=4,
                        )
                        new_alts.append({"function": alt})
                elif isinstance(alt, dict):
                    func_name = alt.get("function")
                    if func_name and func_name in parent_alt_map:
                        merged_alt = {**parent_alt_map[func_name], **alt}
                        new_alts.append(merged_alt)
                    else:
                        new_alts.append(dict(alt))
                else:
                    raise MismatchedOverrideShorthand(
                        f"{component_id}: alt_functions entry must be string or dict, got {alt!r}"
                    )
            coerced_pin["alt_functions"] = new_alts
        out.append(coerced_pin)
    return out


# --- Bundle assembly -----------------------------------------------------


def _format_timestamp(source_date_epoch: int | None) -> str:
    if source_date_epoch is not None:
        return datetime.fromtimestamp(source_date_epoch, tz=UTC).isoformat()
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def _git_sha(cwd: Path) -> str:
    """Return the current git commit SHA, or ``"dev"`` if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "dev"


def assemble_bundle(
    raw: dict[str, dict[str, Any]],
    source_date_epoch: int | None,
    git_sha: str,
) -> dict[str, Any]:
    resolved: dict[str, dict[str, Any]] = {}
    for component_id in sorted(raw.keys()):
        resolved[component_id] = resolve(component_id, raw)

    count_by_kind = dict(Counter(rec.get("kind", "?") for rec in resolved.values()))

    meta: dict[str, Any] = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "generated_at": _format_timestamp(source_date_epoch),
        "git_sha": git_sha,
        "total_count": len(resolved),
        "count_by_kind": dict(sorted(count_by_kind.items())),
    }
    return {"components": resolved, "meta": meta}


# --- Emit ---------------------------------------------------------------


def emit_library_json(bundle: dict[str, Any], target: Path) -> None:
    target.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")


def emit_index_json(bundle: dict[str, Any], target: Path) -> None:
    """Small (≤ 50 KB) summary: counts + {id, kind, summary} per component."""
    components = bundle["components"]
    summary_records = sorted(
        (
            {"id": cid, "kind": rec.get("kind", "?"), "summary": rec.get("summary", "")}
            for cid, rec in components.items()
        ),
        key=lambda r: r["id"],
    )
    index = {"meta": bundle["meta"], "components": list(summary_records)}
    target.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")


def emit_library_sqlite(bundle: dict[str, Any], target: Path) -> None:
    """Write the bundle to a deterministic SQLite file with FTS5 search.

    Determinism requires care: page_size pinned, journal_mode MEMORY (no
    -wal/-shm files), inserts in id-sorted order, single transaction,
    then ``VACUUM`` to compact and canonicalise free-page layout.
    """
    if target.exists():
        target.unlink()

    conn = sqlite3.connect(target)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute(f"PRAGMA user_version = {BUNDLE_SCHEMA_VERSION}")
        conn.execute("PRAGMA journal_mode = MEMORY")
        conn.execute("PRAGMA synchronous = OFF")

        conn.executescript(
            """
            CREATE TABLE components (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                vendor TEXT,
                mpn TEXT,
                summary TEXT NOT NULL,
                lifecycle TEXT NOT NULL,
                revision TEXT NOT NULL,
                json TEXT NOT NULL
            );
            CREATE INDEX idx_components_kind ON components(kind);
            CREATE INDEX idx_components_vendor ON components(vendor);
            CREATE INDEX idx_components_lifecycle ON components(lifecycle);
            CREATE VIRTUAL TABLE components_fts USING fts5(
                id UNINDEXED,
                summary,
                vendor,
                mpn,
                tags,
                tokenize = 'porter'
            );
            """
        )

        components = bundle["components"]
        for component_id in sorted(components.keys()):
            rec = components[component_id]
            kind = str(rec.get("kind", ""))
            vendor = rec.get("vendor")
            mpn = rec.get("manufacturer_part_number")
            summary = str(rec.get("summary", ""))
            lifecycle = str(rec.get("lifecycle", ""))
            revision = str(rec.get("revision", ""))
            tags = " ".join(rec.get("tags") or [])
            json_blob = json.dumps(rec, sort_keys=True, separators=(",", ":"))

            conn.execute(
                "INSERT INTO components (id, kind, vendor, mpn, summary, lifecycle, "
                "revision, json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (component_id, kind, vendor, mpn, summary, lifecycle, revision, json_blob),
            )
            conn.execute(
                "INSERT INTO components_fts (id, summary, vendor, mpn, tags) "
                "VALUES (?, ?, ?, ?, ?)",
                (component_id, summary, vendor or "", mpn or "", tags),
            )

        conn.commit()
        # VACUUM cannot run inside a transaction; commit above closes the
        # implicit txn opened by INSERTs.
        conn.execute("VACUUM")
    finally:
        conn.close()


# --- Pipeline ------------------------------------------------------------


def build(
    library: Path,
    out: Path,
    source_date_epoch: int | None = None,
) -> dict[str, Any]:
    """Run discovery → resolve → emit. Return the assembled bundle dict."""
    if source_date_epoch is None:
        sde_env = os.environ.get("SOURCE_DATE_EPOCH")
        if sde_env:
            with contextlib.suppress(ValueError):
                source_date_epoch = int(sde_env)

    out.mkdir(parents=True, exist_ok=True)

    raw = discover(library)
    bundle = assemble_bundle(
        raw,
        source_date_epoch=source_date_epoch,
        git_sha=_git_sha(REPO_ROOT),
    )

    emit_library_json(bundle, out / "library.json")
    emit_library_sqlite(bundle, out / "library.sqlite")
    emit_index_json(bundle, out / "index.json")

    return bundle


# --- CLI -----------------------------------------------------------------


@click.command()
@click.option(
    "--library",
    type=click.Path(file_okay=False, exists=True, path_type=Path),
    default=DEFAULT_LIBRARY,
    show_default=True,
    help="Path to the library/ directory.",
)
@click.option(
    "--out",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_OUT,
    show_default=True,
    help="Output directory for the bundle.",
)
def main(library: Path, out: Path) -> None:
    """Build the deterministic hw-registry bundle from library/ into out/."""
    try:
        bundle = build(library, out)
    except BuilderError as e:
        raise click.ClickException(str(e)) from e

    meta = bundle["meta"]
    click.echo(f"wrote {out}/library.json   ({meta['total_count']} components)")
    click.echo(f"wrote {out}/library.sqlite ({meta['total_count']} indexed)")
    click.echo(f"wrote {out}/index.json")


if __name__ == "__main__":
    main()
