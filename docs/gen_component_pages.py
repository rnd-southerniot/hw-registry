"""mkdocs-gen-files hook: emit per-component pages from dist/library.json.

One Markdown page per component under ``components/<id>.md`` plus a
faceted ``components/index.md``. Per-kind renderers keep the layout
appropriate to each kind — boards lead with pin tables, sensors lead
with constraints, drivers list framework bindings.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import mkdocs_gen_files

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY_JSON = REPO_ROOT / "dist" / "library.json"

if not LIBRARY_JSON.exists():
    raise FileNotFoundError(
        f"dist/library.json not found at {LIBRARY_JSON}.\n"
        "Run `python -m tools.builder --out dist/` from the repo root before "
        "building the docs site. The doc build does NOT auto-build the "
        "bundle — same fail-fast contract as hwlib-mcp."
    )

_data = json.loads(LIBRARY_JSON.read_text())
COMPONENTS: dict[str, dict[str, Any]] = _data["components"]


# --- Markdown helpers ---------------------------------------------------


def _esc(v: Any) -> str:
    """Render a value safely for a Markdown table cell."""
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, list):
        return ", ".join(_esc(x) for x in v) if v else "—"
    if isinstance(v, dict):
        return ", ".join(f"{k}={_esc(val)}" for k, val in v.items())
    return str(v).replace("|", "\\|").replace("\n", " ")


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return ""
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def _get(d: dict, *path: str, default: Any = None) -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


# --- Common section renderers ------------------------------------------


def _identity_table(c: dict) -> str:
    rows = [
        ["id", f"`{c['id']}`"],
        ["kind", _esc(c.get("kind"))],
        ["vendor", _esc(c.get("vendor"))],
        ["MPN", _esc(c.get("manufacturer_part_number"))],
        ["revision", _esc(c.get("revision"))],
        ["lifecycle", _esc(c.get("lifecycle"))],
    ]
    return _md_table(["field", "value"], rows)


def _tags_row(c: dict) -> str:
    tags = c.get("tags") or []
    if not tags:
        return ""
    return " ".join(f"`{t}`" for t in tags)


def _tested_block(c: dict) -> str:
    t = c.get("tested")
    if not t:
        return ""
    rows = [
        ["status", _esc(t.get("status"))],
        ["by", _esc(t.get("by"))],
        ["date", _esc(t.get("date"))],
    ]
    out = ["## Tested", "", _md_table(["field", "value"], rows)]
    if t.get("evidence"):
        out.append("")
        out.append(f"**Evidence:** {_esc(t['evidence'])}")
    return "\n".join(out)


def _datasheet_block(c: dict) -> str:
    ds = _get(c, "assets", "datasheet")
    if not ds:
        return ""
    out = ["## Datasheet", ""]
    if ds.get("primary_url"):
        out.append(f"- [Manufacturer]({ds['primary_url']})")
    if ds.get("archived_url"):
        out.append(f"- [Archive (web.archive.org)]({ds['archived_url']})")
    return "\n".join(out)


def _kicad_block(c: dict) -> str:
    k = c.get("kicad")
    if not k:
        return ""
    rows = []
    if k.get("symbol"):
        rows.append(["symbol", f"`{k['symbol']}`"])
    if k.get("footprint"):
        rows.append(["footprint", f"`{k['footprint']}`"])
    if k.get("model_3d"):
        rows.append(["3D model", f"`{k['model_3d']}`"])
    if not rows:
        return ""
    return "## KiCad refs\n\n" + _md_table(["field", "value"], rows)


def _electrical_block(c: dict) -> str:
    e = c.get("electrical")
    if not e:
        return ""
    rows = []
    vcc = e.get("vcc") or {}
    if vcc:
        v = []
        if vcc.get("nominal_v") is not None:
            v.append(f"{vcc['nominal_v']} V nominal")
        if vcc.get("min_v") is not None and vcc.get("max_v") is not None:
            v.append(f"{vcc['min_v']}–{vcc['max_v']} V range")
        if vcc.get("source"):
            v.append(f"source: {vcc['source']}")
        rows.append(["VCC", "; ".join(v) or "—"])
    cur = e.get("current_draw") or {}
    if cur:
        v = []
        if cur.get("typ_active_mA") is not None:
            v.append(f"{cur['typ_active_mA']} mA active")
        if cur.get("sleep_uA") is not None:
            v.append(f"{cur['sleep_uA']} µA sleep")
        rows.append(["Current draw", "; ".join(v) or "—"])
    logic = e.get("logic") or {}
    if logic:
        v = []
        if logic.get("family"):
            v.append(_esc(logic["family"]))
        if logic.get("voltage_v") is not None:
            v.append(f"{logic['voltage_v']} V")
        if logic.get("five_v_tolerant") is not None:
            v.append("5V tolerant" if logic["five_v_tolerant"] else "NOT 5V tolerant")
        rows.append(["Logic", "; ".join(v) or "—"])
    if e.get("power_budget_mA") is not None:
        rows.append(["Power budget", f"{e['power_budget_mA']} mA"])
    if not rows:
        return ""
    return "## Electrical\n\n" + _md_table(["field", "value"], rows)


def _description_block(c: dict) -> str:
    d = c.get("description")
    if not d:
        return ""
    return f"## Description\n\n{d}"


def _package_block(c: dict, *, include_dimensions: bool = True) -> str:
    pkg = c.get("package") or {}
    if not pkg:
        return ""
    rows = []
    if pkg.get("type"):
        rows.append(["type", _esc(pkg["type"])])
    if pkg.get("pin_count") is not None:
        rows.append(["pin count", str(pkg["pin_count"])])
    if pkg.get("ipc_name"):
        rows.append(["IPC name", f"`{pkg['ipc_name']}`"])
    if pkg.get("rf_certifications"):
        rows.append(["RF certifications", _esc(pkg["rf_certifications"])])
    if include_dimensions and pkg.get("dimensions"):
        d = pkg["dimensions"]
        dims = "×".join(
            f"{d[k]} mm" for k in ("length_mm", "width_mm", "height_mm") if d.get(k) is not None
        )
        if dims:
            rows.append(["dimensions", dims])
    if not rows:
        return ""
    return "## Package\n\n" + _md_table(["field", "value"], rows)


def _join_sections(parts: list[str]) -> str:
    return "\n\n".join(p for p in parts if p) + "\n"


# --- Per-kind renderers -------------------------------------------------


def render_board(c: dict) -> str:
    parts = [f"# {c.get('summary', c['id'])}"]
    tags = _tags_row(c)
    if tags:
        parts.append(tags)
    parts.append(_identity_table(c))

    pins = c.get("pins") or []
    if pins:
        rows = []
        for p in pins:
            af = p.get("alt_functions") or []
            af_strs = []
            for a in af:
                if isinstance(a, dict):
                    af_strs.append(_esc(a.get("function")))
                else:
                    af_strs.append(_esc(a))
            rows.append(
                [
                    _esc(p.get("id")),
                    _esc(p.get("aliases")),
                    _esc(p.get("default")),
                    _esc(p.get("voltage_domain")),
                    ", ".join(af_strs) if af_strs else "—",
                ]
            )
        parts.append(
            "## Pinout\n\n"
            + _md_table(
                ["pin", "aliases", "default", "voltage", "alt_functions"],
                rows,
            )
        )

    peri = c.get("peripherals") or {}
    if peri:
        rows = [[k, str(v)] for k, v in sorted(peri.items()) if v]
        if rows:
            parts.append("## Peripherals\n\n" + _md_table(["peripheral", "count"], rows))

    build = c.get("build") or {}
    if build:
        rows = []
        if build.get("frameworks"):
            rows.append(["frameworks", _esc(build["frameworks"])])
        if build.get("flash_mb") is not None:
            rows.append(["flash", f"{build['flash_mb']} MB"])
        if build.get("psram_mb") is not None:
            rows.append(["psram", f"{build['psram_mb']} MB"])
        if build.get("ram_kb") is not None:
            rows.append(["ram", f"{build['ram_kb']} KB"])
        if rows:
            parts.append("## Build\n\n" + _md_table(["field", "value"], rows))

    parts.append(_electrical_block(c))

    headers = c.get("expansion_headers") or []
    if headers:
        sub = ["## Expansion headers"]
        for h in headers:
            sub.append(f"\n### {h.get('name', '?')}\n")
            meta_rows = []
            if h.get("pin_count") is not None:
                meta_rows.append(["pin count", str(h["pin_count"])])
            if h.get("pitch_mm") is not None:
                meta_rows.append(["pitch", f"{h['pitch_mm']} mm"])
            if meta_rows:
                sub.append(_md_table(["field", "value"], meta_rows))
            seq = h.get("pins") or []
            if seq:
                sub.append("\nPin sequence:\n")
                sub.append("```\n" + ", ".join(seq) + "\n```")
        parts.append("\n".join(sub))

    usb = _get(c, "discovery", "usb")
    if usb:
        rows = [[_esc(u.get("vid")), _esc(u.get("pid")), _esc(u.get("description"))] for u in usb]
        parts.append(
            "## USB discovery\n\n"
            + _md_table(
                ["VID", "PID", "description"],
                rows,
            )
        )

    parts.append(_kicad_block(c))
    parts.append(_datasheet_block(c))
    parts.append(_tested_block(c))
    parts.append(_description_block(c))
    return _join_sections(parts)


def render_module(c: dict) -> str:
    parts = [f"# {c.get('summary', c['id'])}"]
    tags = _tags_row(c)
    if tags:
        parts.append(tags)
    parts.append(_identity_table(c))

    pins = c.get("pins") or []
    if pins:
        rows = []
        for p in pins:
            af = p.get("alt_functions") or []
            af_strs = []
            for a in af:
                if isinstance(a, dict):
                    af_strs.append(_esc(a.get("function")))
                else:
                    af_strs.append(_esc(a))
            rows.append(
                [
                    _esc(p.get("id")),
                    _esc(p.get("exposed_as") or p.get("aliases")),
                    ", ".join(af_strs) if af_strs else "—",
                ]
            )
        parts.append(
            "## Pin map\n\n"
            + _md_table(
                ["pin", "exposed as", "alt_functions"],
                rows,
            )
        )

    parts.append(_package_block(c))
    parts.append(_electrical_block(c))

    build = c.get("build") or {}
    if build:
        rows = []
        if build.get("frameworks"):
            rows.append(["frameworks", _esc(build["frameworks"])])
        for k in ("flash_mb", "psram_mb", "ram_kb"):
            if build.get(k) is not None:
                rows.append([k, str(build[k])])
        if rows:
            parts.append("## Build\n\n" + _md_table(["field", "value"], rows))

    parts.append(_kicad_block(c))
    parts.append(_datasheet_block(c))
    parts.append(_tested_block(c))
    parts.append(_description_block(c))
    return _join_sections(parts)


def render_chip(c: dict) -> str:
    parts = [f"# {c.get('summary', c['id'])}"]
    tags = _tags_row(c)
    if tags:
        parts.append(tags)
    parts.append(_identity_table(c))
    parts.append(_package_block(c, include_dimensions=False))
    if c.get("alt_functions"):
        parts.append(
            f"## Alt-function table\n\n`{len(c['alt_functions'])}` entries "
            "(see source YAML for details)."
        )
    parts.append(_datasheet_block(c))
    parts.append(_tested_block(c))
    parts.append(_description_block(c))
    return _join_sections(parts)


def render_sensor(c: dict) -> str:
    parts = [f"# {c.get('summary', c['id'])}"]
    tags = _tags_row(c)
    if tags:
        parts.append(tags)
    parts.append(_identity_table(c))

    cons = c.get("constraints") or {}
    if cons:
        block = ["## Constraints"]

        i2c = cons.get("i2c")
        if i2c:
            block.append("\n### I²C\n")
            rows = []
            if i2c.get("address") is not None:
                rows.append(["address", f"`0x{i2c['address']:02X}`"])
            opts = i2c.get("address_pin_options")
            if opts:
                rows.append(
                    [
                        "address pin options",
                        ", ".join(f"`0x{a:02X}`" for a in opts),
                    ]
                )
            if i2c.get("requires_pullups_ohms") is not None:
                rows.append(
                    [
                        "pull-ups",
                        f"{i2c['requires_pullups_ohms']} Ω required",
                    ]
                )
            block.append(_md_table(["field", "value"], rows))

        acc = cons.get("accuracy")
        if acc:
            block.append("\n### Accuracy\n")
            rows = [[k, _esc(v)] for k, v in acc.items()]
            block.append(_md_table(["metric", "value"], rows))

        pw = cons.get("power")
        if pw:
            block.append("\n### Power\n")
            rows = []
            if pw.get("min_startup_time_ms") is not None:
                rows.append(
                    [
                        "min startup time",
                        f"{pw['min_startup_time_ms']} ms",
                    ]
                )
            if pw.get("requires_decoupling"):
                rows.append(
                    [
                        "requires decoupling",
                        _esc(pw["requires_decoupling"]),
                    ]
                )
            block.append(_md_table(["field", "value"], rows))

        intr = cons.get("interrupt")
        if isinstance(intr, dict):
            block.append("\n### Interrupt\n")
            rows = [["required", _esc(intr.get("required"))]]
            if intr.get("pin"):
                rows.append(["pin", _esc(intr["pin"])])
            block.append(_md_table(["field", "value"], rows))

        ot = cons.get("operating_temp_c") or {}
        if ot.get("min_c") is not None and ot.get("max_c") is not None:
            block.append(f"\n### Operating temperature\n\n{ot['min_c']} °C to {ot['max_c']} °C")

        if cons.get("response_time_ms") is not None:
            block.append(f"\n### Response time\n\n{cons['response_time_ms']} ms")

        parts.append("\n".join(block))

    iface = c.get("interface") or {}
    if iface:
        rows = []
        if iface.get("type"):
            rows.append(["type", _esc(iface["type"])])
        if iface.get("speed_max_khz") is not None:
            rows.append(["max speed", f"{iface['speed_max_khz']} kHz"])
        if rows:
            parts.append(
                "## Interface\n\n"
                + _md_table(
                    ["field", "value"],
                    rows,
                )
            )

    parts.append(_electrical_block(c))
    parts.append(_package_block(c))

    drivers = c.get("drivers") or []
    if drivers:
        block = ["## Drivers", ""]
        for did in drivers:
            block.append(f"- [`{did}`](../../{did}.md)")
        parts.append("\n".join(block))

    parts.append(_kicad_block(c))
    parts.append(_datasheet_block(c))
    parts.append(_tested_block(c))
    parts.append(_description_block(c))
    return _join_sections(parts)


def render_driver(c: dict) -> str:
    parts = [f"# {c.get('summary', c['id'])}"]
    parts.append(_identity_table(c))

    applies_to = c.get("applies_to") or []
    if applies_to:
        block = ["## Applies to", ""]
        for cid in applies_to:
            block.append(f"- [`{cid}`](../../{cid}.md)")
        parts.append("\n".join(block))

    bindings = c.get("bindings") or []
    if bindings:
        block = ["## Bindings"]
        for b in bindings:
            fw = b.get("framework", "?")
            block.append(f"\n### {fw}\n")
            rows = []
            for k, v in sorted(b.items()):
                if k == "framework":
                    continue
                rows.append([k, _esc(v)])
            if rows:
                block.append(_md_table(["field", "value"], rows))
        parts.append("\n".join(block))

    parts.append(_tested_block(c))
    return _join_sections(parts)


def render_connector(c: dict) -> str:
    parts = [f"# {c.get('summary', c['id'])}"]
    parts.append(_identity_table(c))
    parts.append(_package_block(c))
    parts.append(_datasheet_block(c))
    parts.append(_tested_block(c))
    parts.append(_description_block(c))
    return _join_sections(parts)


RENDERERS = {
    "board": render_board,
    "module": render_module,
    "chip": render_chip,
    "sensor": render_sensor,
    "driver": render_driver,
    "connector": render_connector,
}


# --- Emit pages (runs at module-import time when mkdocs-gen-files loads
#     this script during the build). Don't import this module from
#     application code — `mkdocs_gen_files.open()` outside a real build
#     context will fall back to writing real files relative to cwd.

KIND_LABELS = {
    "board": "Boards",
    "module": "Modules",
    "chip": "Chips",
    "sensor": "Sensors",
    "driver": "Drivers",
    "connector": "Connectors",
}
KIND_ORDER = ["board", "module", "chip", "sensor", "driver", "connector"]

_by_kind: dict[str, list[tuple[str, dict]]] = defaultdict(list)
for _cid, _c in COMPONENTS.items():
    _by_kind[_c["kind"]].append((_cid, _c))
for _k in _by_kind:
    _by_kind[_k].sort(key=lambda t: t[0])

for _cid, _c in COMPONENTS.items():
    _renderer = RENDERERS.get(_c["kind"])
    if _renderer is None:
        continue
    with mkdocs_gen_files.open(f"components/{_cid}.md", "w") as _fh:
        _fh.write(_renderer(_c))

with mkdocs_gen_files.open("components/index.md", "w") as _fh:
    _fh.write("# Components\n\n")
    _fh.write(f"Total: **{len(COMPONENTS)}** components.\n\n")
    for _kind in KIND_ORDER:
        _items = _by_kind.get(_kind, [])
        _fh.write(f"## {KIND_LABELS[_kind]} ({len(_items)})\n\n")
        if not _items:
            _fh.write("_(none)_\n\n")
            continue
        for _cid, _c in _items:
            _fh.write(f"- [`{_cid}`]({_cid}.md) — {_c.get('summary', '')}\n")
        _fh.write("\n")
