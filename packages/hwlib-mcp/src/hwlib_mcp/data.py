"""SQLite query layer reading the ``library.sqlite`` bundle.

Read-only by design. Each function opens a short-lived connection —
SQLite is fast enough that connection pooling buys nothing for an MCP
server's traffic shape, and per-call connections keep us safe from
thread/async lifecycle bugs.

The bundle schema (see ``tools/builder/build.py::emit_library_sqlite``):

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
    CREATE VIRTUAL TABLE components_fts USING fts5(
        id UNINDEXED, summary, vendor, mpn, tags,
        tokenize = 'porter'
    );
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def bundle_present(data_dir: Path) -> bool:
    """True if ``library.sqlite`` is at *data_dir*."""
    return (data_dir / "library.sqlite").is_file()


def _summary_vendor(component_id: str, stored_vendor: str | None) -> str | None:
    """Return the vendor for a search/list summary record.

    Drivers carry no `vendor` field on the model by design (their YAML
    is CC-BY-4.0 metadata, not a part datasheet). The slug structure
    `kind/vendor/part` is authoritative — synthesize from there so search
    results don't show a confusing `vendor: None` for drivers next to
    populated values for sensors/boards/modules. Pure derivation; no
    field added to the model.
    """
    if stored_vendor is not None:
        return stored_vendor
    parts = component_id.split("/")
    if len(parts) >= 3 and parts[1]:
        return parts[1]
    return None


def _connect(data_dir: Path) -> sqlite3.Connection:
    return sqlite3.connect(data_dir / "library.sqlite")


def all_ids(data_dir: Path) -> list[str]:
    """Return every component id (sorted)."""
    with _connect(data_dir) as conn:
        rows = conn.execute("SELECT id FROM components ORDER BY id").fetchall()
    return [r[0] for r in rows]


def search(
    data_dir: Path,
    query: str,
    kind: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """FTS5 search over name/manufacturer/summary. Returns summary records only."""
    sql = (
        "SELECT c.id, c.kind, c.summary, c.vendor "
        "FROM components_fts f "
        "JOIN components c ON c.id = f.id "
        "WHERE components_fts MATCH ? "
    )
    params: list[Any] = [query]
    if kind:
        sql += "AND c.kind = ? "
        params.append(kind)
    sql += "ORDER BY c.id LIMIT ?"
    params.append(limit)

    with _connect(data_dir) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {"id": rid, "kind": rkind, "summary": rsummary, "vendor": _summary_vendor(rid, rvendor)}
        for rid, rkind, rsummary, rvendor in rows
    ]


def list_components(
    data_dir: Path,
    kind: str | None,
    interface: str | None,
    voltage_compatible_with: float | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Faceted browse. Returns one page of summaries plus pagination metadata."""
    sql = "SELECT id, kind, summary, vendor, lifecycle, json FROM components"
    where: list[str] = []
    params: list[Any] = []
    if kind:
        where.append("kind = ?")
        params.append(kind)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id"

    with _connect(data_dir) as conn:
        rows = conn.execute(sql, params).fetchall()

    matched: list[dict[str, Any]] = []
    for rid, rkind, rsummary, rvendor, _rlifecycle, rjson in rows:
        if interface or voltage_compatible_with is not None:
            record = json.loads(rjson)
            if interface:
                rec_iface = (record.get("interface") or {}).get("type")
                if rec_iface != interface:
                    continue
            if voltage_compatible_with is not None and not _voltage_compatible(
                record, voltage_compatible_with
            ):
                continue
        matched.append(
            {
                "id": rid,
                "kind": rkind,
                "summary": rsummary,
                "vendor": _summary_vendor(rid, rvendor),
            }
        )

    total = len(matched)
    offset = (page - 1) * page_size
    page_items = matched[offset : offset + page_size]
    return {
        "components": page_items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


def _voltage_compatible(record: dict[str, Any], bus_voltage: float) -> bool:
    """True if *record*'s vcc envelope contains *bus_voltage* (or is unspecified)."""
    vcc = (record.get("electrical") or {}).get("vcc") or {}
    min_v = vcc.get("min_v")
    max_v = vcc.get("max_v")
    if min_v is None and max_v is None:
        return True  # under-specified — give the benefit of the doubt
    if min_v is not None and bus_voltage < float(min_v):
        return False
    return not (max_v is not None and bus_voltage > float(max_v))


def get_record(data_dir: Path, component_id: str) -> dict[str, Any] | None:
    """Return the full resolved record for *component_id*, or None."""
    with _connect(data_dir) as conn:
        row = conn.execute("SELECT json FROM components WHERE id = ?", (component_id,)).fetchone()
    if row is None:
        return None
    parsed: dict[str, Any] = json.loads(row[0])
    return parsed


def project_record(record: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    """Subset *record* to ``fields`` plus identity (id + kind always included)."""
    if not fields:
        return dict(record)
    keep = set(fields) | {"id", "kind"}
    return {k: v for k, v in record.items() if k in keep}


def get_drivers_for(
    data_dir: Path,
    component_id: str,
    framework: str | None,
) -> list[dict[str, Any]]:
    """Return driver bindings whose ``applies_to`` contains *component_id*.

    The driver's ``applies_to`` is unversioned per the Appendix A
    decision; matching is exact-string equality.
    """
    out: list[dict[str, Any]] = []
    with _connect(data_dir) as conn:
        rows = conn.execute(
            "SELECT id, json FROM components WHERE kind = 'driver' ORDER BY id"
        ).fetchall()
    for driver_id, driver_json in rows:
        record = json.loads(driver_json)
        applies_to = record.get("applies_to") or []
        if component_id not in applies_to:
            continue
        bindings = record.get("bindings") or []
        if framework:
            bindings = [b for b in bindings if b.get("framework") == framework]
        for binding in bindings:
            out.append({"driver_id": driver_id, **binding})
    return out


def index_summary(data_dir: Path) -> dict[str, Any]:
    """High-level catalog summary for ``hwlib://catalog/index`` resource."""
    with _connect(data_dir) as conn:
        rows = conn.execute("SELECT id, kind, summary FROM components ORDER BY id").fetchall()
    by_kind: dict[str, int] = {}
    summaries: list[dict[str, Any]] = []
    for rid, rkind, rsummary in rows:
        by_kind[rkind] = by_kind.get(rkind, 0) + 1
        summaries.append({"id": rid, "kind": rkind, "summary": rsummary})
    return {
        "total": len(summaries),
        "count_by_kind": dict(sorted(by_kind.items())),
        "components": summaries,
    }
