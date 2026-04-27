"""FastMCP instance + tool / resource definitions.

Tool descriptions are LLM-facing protocol — read once, by every agent
session, forever. They are calibrated per BLUEPRINT.md sec 7.1: enough
context that an agent picks the right tool, terse enough that the
catalog itself isn't a context drag. Hard caps live in the description
text (not just defaults), so agents that override defaults still see
the limit.

Errors are returned as structured shapes (see ``errors.py``), never
raised. If a tool would have raised, it returns a dict with a
``status`` key the agent can pattern-match.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from . import data, errors
from .suggestions import suggest_close_ids

logger = logging.getLogger(__name__)

# Lazy import of the conflict checker. In dev mode the root
# ``hw-registry-tools`` package is editable-installed alongside
# ``hwlib-mcp`` and these imports succeed; when ``hwlib-mcp`` is
# installed standalone (post-Prompt-10 PyPI publish), the module is
# absent and ``hwlib_check_pin_conflicts`` returns a structured
# checker_unavailable response.
#
# TODO(prompt-10): replace lazy-import + checker_unavailable fallback
# with a proper path-dep on tools/conflicts/. The right shape depends
# on how the release wiring extracts conflict-checker code: own wheel
# (`hwlib-conflicts`?), folded into `hwlib-data`, or kept inside the
# root `hw-registry-tools` distribution. The lazy fallback is the
# correct hold pattern until that question is answered holistically;
# hardening to a path-dep now requires the root tooling to be wheel-
# installable, which it is not yet (still a flat dev tree under
# tools/).
try:
    from tools.conflicts import (  # type: ignore[import-not-found]
        BundleNotBuilt as _ToolsBundleNotBuilt,
    )
    from tools.conflicts import (
        UnresolvedComponentRef as _ToolsUnresolvedRef,
    )
    from tools.conflicts import (
        build_graph,
        load_system_from_assignments,
        run_all,
    )

    _CONFLICTS_AVAILABLE = True
except ImportError:
    _CONFLICTS_AVAILABLE = False
    logger.info("tools.conflicts unavailable; hwlib_check_pin_conflicts will degrade")


def build_server(data_dir: Path) -> FastMCP:
    """Construct and return the FastMCP server bound to *data_dir*."""
    mcp: FastMCP = FastMCP(
        name="hwlib",
        instructions=(
            "Curated catalog of embedded components (boards, modules, sensors, "
            "drivers, chips, connectors). Use search/list to discover candidates, "
            "get to inspect specifics, check_pin_conflicts to validate "
            "assignments before generating code. Bundle is read-only."
        ),
    )

    # --- Active tools ----------------------------------------------------

    def _bundle_guard() -> dict[str, Any] | None:
        """Return a bundle_missing error if the bundle is absent, else None."""
        if not data.bundle_present(data_dir):
            return errors.bundle_missing(str(data_dir))
        return None

    @mcp.tool()
    async def hwlib_search(
        query: str,
        kind: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Fuzzy full-text search over component name, manufacturer, and summary.

        Returns at most 20 candidates (the `limit` parameter is capped at 20),
        each as {id, kind, summary, vendor}. Use this BEFORE hwlib_get when
        you don't already have a specific component ID. Filter by kind to
        narrow: 'board', 'module', 'sensor', 'driver', 'chip', 'connector'.
        """
        if (guard := _bundle_guard()) is not None:
            return guard
        if not query or not isinstance(query, str):
            return errors.invalid_argument("query", "must be a non-empty string")
        capped = max(1, min(int(limit), 20))
        try:
            results = data.search(data_dir, query, kind, capped)
        except Exception as e:  # noqa: BLE001
            logger.exception("hwlib_search failed")
            return errors.invalid_argument("query", f"search error: {e}")
        return {"results": results, "count": len(results)}

    @mcp.tool()
    async def hwlib_list(
        kind: str | None = None,
        interface: str | None = None,
        voltage_compatible_with: float | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Faceted browse of the catalog.

        Returns one page of components matching the filters. Each page item
        is a summary {id, kind, summary, vendor} — NOT the full record. For
        full records, follow up with hwlib_get on the IDs you want. page_size
        is capped at 50. Use this when enumerating by category (e.g. all I²C
        sensors, all 3.3V-compatible boards).
        """
        if (guard := _bundle_guard()) is not None:
            return guard
        if page < 1:
            return errors.invalid_argument("page", "must be >= 1")
        capped_page_size = max(1, min(int(page_size), 50))
        return data.list_components(
            data_dir,
            kind=kind,
            interface=interface,
            voltage_compatible_with=voltage_compatible_with,
            page=page,
            page_size=capped_page_size,
        )

    @mcp.tool()
    async def hwlib_get(
        id: str,  # noqa: A002 — `id` is the canonical name for the slug
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Returns the full resolved record for a single component.

        Identified by slug ID (e.g. 'sensors/sensirion/sht41'). Always pass
        `fields` to project only the keys you need — full records can exceed
        5KB. Common projections: ['pins', 'electrical', 'constraints'] for
        pinout work; ['kicad', 'package'] for PCB integration; ['drivers']
        for binding cross-refs. On miss, returns
        {"status": "not_found", "id": "...", "suggestions": [...]} with up
        to 3 closest IDs — don't retry the same wrong ID.
        """
        if (guard := _bundle_guard()) is not None:
            return guard
        if not id or not isinstance(id, str):
            return errors.invalid_argument("id", "must be a non-empty string")
        record = data.get_record(data_dir, id)
        if record is None:
            sugg = suggest_close_ids(id, data.all_ids(data_dir), n=3)
            return errors.not_found(id, sugg)
        return data.project_record(record, fields)

    @mcp.tool()
    async def hwlib_check_pin_conflicts(
        board_id: str,
        components: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Validates a proposed pin assignment against the board's constraints.

        Each `components[i]` is {ref, instance, pins: {signal: gpio}}.
        Returns {ok: bool, error_count, warning_count, info_count, diagnostics}
        where diagnostics use the SARIF-compatible Diagnostic shape (id,
        severity, message, rule, locations). Call this BEFORE generating any
        pin-using code — even a clean-looking assignment may collide on I²C
        addresses, reserved pins, or voltage compatibility.
        """
        if (guard := _bundle_guard()) is not None:
            return guard
        if not _CONFLICTS_AVAILABLE:
            return errors.checker_unavailable()

        if not isinstance(board_id, str) or not board_id:
            return errors.invalid_argument("board_id", "must be a non-empty string")
        if not isinstance(components, list):
            return errors.invalid_argument("components", "must be a list of assignments")

        try:
            system = load_system_from_assignments(
                board_id, components, bundle_db=data_dir / "library.sqlite"
            )
        except _ToolsBundleNotBuilt:
            return errors.bundle_missing(str(data_dir))
        except _ToolsUnresolvedRef as e:
            missing = str(e).split(": ", 1)[-1]
            return {
                "status": "unresolved_ref",
                "message": str(e),
                "missing": missing,
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("hwlib_check_pin_conflicts: load failed")
            return errors.invalid_argument("components", str(e))

        graph = build_graph(system)
        diagnostics = run_all(graph, system)

        error_count = sum(1 for d in diagnostics if d.severity == "error")
        warning_count = sum(1 for d in diagnostics if d.severity == "warning")
        info_count = sum(1 for d in diagnostics if d.severity == "info")
        return {
            "ok": error_count == 0,
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "diagnostics": [d.to_dict() for d in diagnostics],
        }

    @mcp.tool()
    async def hwlib_compatible_modules(
        board_id: str,
        interface: str | None = None,
    ) -> dict[str, Any]:
        """Returns components known to work with the given board.

        Compatibility heuristic: voltage-compatible electrical envelope
        (component's vcc range overlaps board's IO voltage) AND a populated
        driver binding for at least one framework supported by the board's
        `build.frameworks`. Filter by interface (i2c/spi/uart) when supplied.
        Best-effort, NOT exhaustive — absence from this list does NOT prove
        incompatibility, only that the heuristic didn't recognize it.
        """
        if (guard := _bundle_guard()) is not None:
            return guard
        board = data.get_record(data_dir, board_id)
        if board is None:
            sugg = suggest_close_ids(board_id, data.all_ids(data_dir), n=3)
            return errors.not_found(board_id, sugg)

        board_iov = ((board.get("electrical") or {}).get("logic") or {}).get("voltage_v")
        board_frameworks = set((board.get("build") or {}).get("frameworks") or [])

        # Walk every non-board component, filter by interface + voltage,
        # then check driver-framework overlap.
        candidates = data.list_components(
            data_dir,
            kind=None,
            interface=interface,
            voltage_compatible_with=board_iov,
            page=1,
            page_size=1000,
        )["components"]

        compatible: list[dict[str, Any]] = []
        for cand in candidates:
            cid = cand["id"]
            if cand["kind"] in ("board", "driver"):
                continue
            if cid == board_id:
                continue
            drivers = data.get_drivers_for(data_dir, cid, framework=None)
            framework_overlap = bool(
                board_frameworks & {b.get("framework") for b in drivers if b.get("framework")}
            )
            if not framework_overlap:
                continue
            compatible.append(cand)

        return {"results": compatible, "count": len(compatible), "board_id": board_id}

    @mcp.tool()
    async def hwlib_get_drivers(
        component_id: str,
        framework: str | None = None,
    ) -> dict[str, Any]:
        """Returns vetted driver bindings for a component.

        Each binding has {framework, version_constraint,
        component/library/module/compatible (per framework),
        header/sample_call (where applicable), tested_with, license}. Filter
        by framework: 'esp-idf', 'arduino', 'zephyr', 'micropython',
        'platformio'. Use this when scaffolding firmware — the bindings
        tell you which idf_component.yml entry, library.json dependency, or
        DTS compatible string to emit.
        """
        if (guard := _bundle_guard()) is not None:
            return guard
        if not isinstance(component_id, str) or not component_id:
            return errors.invalid_argument("component_id", "must be a non-empty string")
        # 404 if the component itself is unknown.
        if data.get_record(data_dir, component_id) is None:
            sugg = suggest_close_ids(component_id, data.all_ids(data_dir), n=3)
            return errors.not_found(component_id, sugg)
        bindings = data.get_drivers_for(data_dir, component_id, framework)
        return {"component_id": component_id, "bindings": bindings, "count": len(bindings)}

    # --- Stub tools — return structured not_implemented responses --------

    @mcp.tool()
    async def hwlib_suggest_pinmap(
        board_id: str,
        components: list[dict[str, Any]],
        pin_constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """[STUB - post-MVP] Will optimize pin assignment respecting strapping
        pins, peripheral mux, and shared-bus conventions. Currently returns a
        not_implemented response.

        Workaround: assign pins manually using hwlib_get to read each
        component's required signals, then validate with
        hwlib_check_pin_conflicts.
        """
        return errors.not_implemented(
            (
                "hwlib_suggest_pinmap is deferred to post-MVP "
                "(BLUEPRINT.md Prompt A in the post-MVP queue). "
                "Manual assignment + hwlib_check_pin_conflicts is the "
                "current workflow."
            ),
            alternative_tool="hwlib_check_pin_conflicts",
        )

    @mcp.tool()
    async def hwlib_generate_platformio_ini(
        board_id: str,
        components: list[str],
        framework: str = "arduino",
    ) -> dict[str, Any]:
        """[STUB - post-MVP] Will emit a ready-to-use platformio.ini snippet for
        the given board + components. Currently returns a not_implemented
        response.

        Workaround: call hwlib_get_drivers for each component and compose
        platformio.ini manually from the returned package_index / library
        / version_constraint fields.
        """
        return errors.not_implemented(
            (
                "hwlib_generate_platformio_ini is deferred to post-MVP "
                "(BLUEPRINT.md Prompt G). Compose the file by hand from "
                "hwlib_get_drivers output for now."
            ),
            alternative_tool="hwlib_get_drivers",
        )

    @mcp.tool()
    async def hwlib_generate_sdkconfig(
        board_id: str,
        components: list[str],
    ) -> dict[str, Any]:
        """[STUB - post-MVP] Will emit ESP-IDF Kconfig fragment(s) for the
        given board + components. Currently returns a not_implemented
        response.

        Workaround: call hwlib_get_drivers with framework='zephyr' to read
        kconfig symbols (e.g. CONFIG_SHT4X) and compose sdkconfig.defaults
        manually.
        """
        return errors.not_implemented(
            (
                "hwlib_generate_sdkconfig is deferred to post-MVP "
                "(BLUEPRINT.md Prompt G). Compose Kconfig fragments by hand "
                "from hwlib_get_drivers output for now."
            ),
            alternative_tool="hwlib_get_drivers",
        )

    @mcp.tool()
    async def hwlib_get_kicad_refs(component_id: str) -> dict[str, Any]:
        """[STUB - post-MVP] Will return symbol/footprint/3D-model paths
        ready for KiCad consumption. Currently the data is on each
        component's `kicad` field — call hwlib_get with fields=['kicad'] for
        the same information.
        """
        return errors.not_implemented(
            (
                "hwlib_get_kicad_refs is deferred to post-MVP "
                "(BLUEPRINT.md Prompt B). The same data is available "
                "today via hwlib_get with fields=['kicad']."
            ),
            alternative_tool="hwlib_get with fields=['kicad']",
        )

    # --- Resources -------------------------------------------------------
    #
    # Resources are first-class only in Claude Code; Cursor's UX is
    # shallower, Cline's is partial, Aider has none. Every resource here
    # has a Tool counterpart (or is reachable via hwlib_get) — never
    # Resource-only, that would strand non-Claude-Code users.

    @mcp.resource("hwlib://component/{id*}")
    async def component_resource(id: str) -> str:  # noqa: A002
        """Full resolved record for a single component, JSON-serialized.

        URI template uses ``{id*}`` (wildcard path parameter) so the
        slug's slashes — ``sensors/sensirion/sht41`` — are captured as
        a single id, not interpreted as path segments.
        """
        if not data.bundle_present(data_dir):
            return json.dumps(errors.bundle_missing(str(data_dir)), indent=2)
        record = data.get_record(data_dir, id)
        if record is None:
            sugg = suggest_close_ids(id, data.all_ids(data_dir), n=3)
            return json.dumps(errors.not_found(id, sugg), indent=2)
        return json.dumps(record, indent=2, sort_keys=True)

    @mcp.resource("hwlib://catalog/index")
    async def catalog_index() -> str:
        """High-level catalog summary: counts per kind plus {id, kind, summary} per component."""
        if not data.bundle_present(data_dir):
            return json.dumps(errors.bundle_missing(str(data_dir)), indent=2)
        return json.dumps(data.index_summary(data_dir), indent=2, sort_keys=True)

    @mcp.resource("hwlib://schema/{kind}")
    async def schema_resource(kind: str) -> str:
        """JSON Schema for a component kind. Sourced from <repo>/schemas/<kind>.schema.json."""
        # Schemas live at <data_dir>/../schemas/<kind>.schema.json in dev,
        # or alongside the wheel data in production. Walk up from data_dir
        # to find the repo's schemas/ directory.
        schemas_dir = data_dir.parent / "schemas"
        schema_file = schemas_dir / f"{kind}.schema.json"
        if not schema_file.is_file():
            return json.dumps(
                {
                    "status": "not_found",
                    "kind": kind,
                    "message": (
                        f"No schema for kind {kind!r}. "
                        f"Valid kinds: board, module, chip, sensor, connector, driver."
                    ),
                },
                indent=2,
            )
        return schema_file.read_text()

    return mcp
