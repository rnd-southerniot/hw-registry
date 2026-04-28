# hw-registry

A curated hardware library for embedded development. Single source of truth for the **boards, modules, chips, sensors, drivers, and connectors** we have actually built, flashed, and shipped on real systems.

!!! info "Library size — built {{ library_git_sha() }}"
    **{{ library_total() }}** components: {{ library_count_summary() }}.

## Who consumes this

- **Humans** browsing this site for reference, pinouts, and constraints.
- **AI coding agents** (Claude Code, Cursor, Cline) via the [hwlib-mcp](agents/index.md) MCP server.
- **PCB tooling** (KiCad) via symbol/footprint refs in the component YAML.
- **BOM exporters** (JLCPCB, IPC-2581, CycloneDX HBOM) via deterministic component IDs and revisions.

## Find a component

- Use the **search** box at the top of every page (full-text across all components and prose).
- Or browse the [Components](components/index.md) tab — boards, modules, sensors, etc. faceted by kind.
- Each component page surfaces its identity, electrical envelope, package, datasheet, and (for boards) a full pinout table with alt-function map.

## Adding a new component

See [Contributing](contributing.md). The PR workflow is:
author the YAML at `library/<kind>/<vendor>/<part>.yaml`, run
`pre-commit run --all-files` locally, open a PR. Schema validation,
slug-equals-path enforcement, and secret scanning all run in pre-commit.

## Curation philosophy

Coverage is not the goal. A small library of components we have built and shipped beats a large library of speculative entries. Every component carries a `tested` block — `stub`, `verified`, or `production-tested` — with the engineer, date, and evidence of where it shipped.
