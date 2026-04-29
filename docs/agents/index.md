# AI Agents

`hw-registry` is exposed to AI coding agents via the **`hwlib-mcp`** MCP server, distributed as:

- **PyPI wheels** — `pip install hwlib-mcp` (pulls `hwlib-data` transitively, so the catalog is self-contained)
- **GHCR Docker image** — `ghcr.io/rnd-southerniot/hwlib-mcp:latest` (deterministic, signed with SLSA build provenance)

## Pick a transport

| Transport | When to use |
|---|---|
| **stdio** | Local single-developer use. The agent spawns the server as a subprocess; no network. Lower latency, simpler. |
| **Streamable HTTP (`--http`)** | Hosted/team deployments. Run `hwlib-mcp --http` once; multiple agent clients connect over the network. The container image (`ghcr.io/rnd-southerniot/hwlib-mcp:latest`) is built for this case. |

For a personal dev environment, prefer stdio. For a shared catalog server, use HTTP via the container.

## Agent-specific guides

- [Claude Code](claude-code.md) — `claude mcp add` flow, `CLAUDE.md` operating-manual snippet, slash-command shortcuts.
- [Cursor](cursor.md) — `.cursor/mcp.json` config, `.cursor/rules/00-hwlib.mdc`.
- [Cline](cline.md) — `cline_mcp_settings.json` per-OS path, `.clinerules/00-hwlib.md`.
- [Docker](docker.md) — running `hwlib-mcp` as a container; `--http` mode, health probe, GHCR pull.

## Tools the server exposes

| Tool | Purpose |
|---|---|
| `hwlib_search` | full-text search across the library (paged) |
| `hwlib_list` | catalog walk with kind/interface/voltage filters (paged) |
| `hwlib_get` | fetch a single component by id |
| `hwlib_check_pin_conflicts` | validate a proposed pinmap against board capabilities |
| `hwlib_compatible_modules` | find modules that match an interface a board exposes |
| `hwlib_get_drivers` | driver bindings (per-framework code paths) for a component |

Tool descriptions are tuned to shape behavior, not just to document mechanics. Agents are instructed to:

- call `hwlib_search` or `hwlib_list` **before** `hwlib_get` (so they don't hallucinate component IDs)
- paginate through results rather than asking for unbounded listings
- treat the `tested.status` field as a curation gate (`stub` ≠ `production-tested`)

## Self-check after wiring

Whichever agent you've configured, the smoke test is the same:

> *"Use the hwlib MCP server. Find the SHT41 sensor's I²C address."*

A working integration returns `0x44` (with `0x44/0x45` selectable). Anything else — the agent guessing from training data, or claiming the catalog is unavailable — means the wiring isn't right.
