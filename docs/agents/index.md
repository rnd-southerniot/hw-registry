# AI Agents

The `hw-registry` library is exposed to AI coding agents via the **hwlib-mcp** MCP server, distributed as a PyPI package and a `ghcr.io` container image.

## Available integrations

- [Docker](docker.md) — run `hwlib-mcp` as a container in HTTP mode and point any MCP-compatible client at it. Recommended for shared/hosted deployments.
- *Claude Code* — direct integration via `claude mcp add` (full guide in a future milestone).
- *Cursor* — full guide in a future milestone.
- *Cline* — full guide in a future milestone.

## Tools the server exposes

| Tool | Purpose |
|---|---|
| `hwlib_search` | full-text search across the library (paged) |
| `hwlib_list` | catalog walk with kind/interface/voltage filters (paged) |
| `hwlib_get` | fetch a single component by id |
| `hwlib_check_pin_conflicts` | validate a proposed pinmap against board capabilities |
| `hwlib_compatible_modules` | find modules that match an interface a board exposes |
| `hwlib_get_drivers` | driver bindings (per-framework code paths) for a component |

## How agents are nudged

Tool descriptions are tuned to shape behavior, not just to document mechanics. Agents are instructed to:

- call `hwlib_search` or `hwlib_list` **before** `hwlib_get` (so they don't hallucinate component IDs)
- paginate through results rather than asking for unbounded listings
- treat the `tested.status` field as a curation gate (`stub` ≠ `production-tested`)

The wording in those tool descriptions is part of the contract — changes to them are reviewed for behavioral implications, not just typo fixes.
