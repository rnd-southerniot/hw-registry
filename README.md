# hw-registry

The single source of truth for our team's curated, battle-tested embedded
hardware library — boards, modules, chips, sensors, drivers, connectors.

## Who consumes this

| Audience            | How                                                          |
|---------------------|--------------------------------------------------------------|
| **Humans**          | Doc site (MkDocs Material), one auto-generated page per part |
| **AI coding agents**| MCP server `hwlib-mcp` (PyPI + `ghcr.io/rnd-southerniot/hwlib-mcp`) |
| **KiCad / PCB**     | Symbol / footprint / 3D refs in each component YAML          |
| **BOM exporters**   | JLCPCB CSV, IPC-2581, CycloneDX HBOM 1.7                     |

## Layout

```
library/      canonical YAML components (kind/vendor/part.yaml)
pydantic_models/  canonical Pydantic models — schemas/ is generated from these
schemas/      GENERATED JSON Schemas. Never hand-edit
tools/        generators, validators, bundle builder, pin-conflict checker
packages/     hwlib-mcp (MCP server) + hwlib-data (data wheel)
docs/         MkDocs Material site
tests/        unit, integration, e2e
```

## Quickstart for contributors

```bash
git clone git@github.com:rnd-southerniot/hw-registry.git
cd hw-registry
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
# Add a component:
$EDITOR library/sensors/<vendor>/<part>.yaml
pre-commit run --all-files
python -m tools.builder --out dist/
git checkout -b feat/sensor-<part>
git commit -am "feat(sensors): add <vendor> <part> v1.0.0"
gh pr create
```

Each component YAML must:

- Live at `library/<kind>/<vendor>/<part>.yaml`.
- Carry `id: <kind>/<vendor>/<part>` (must equal its path slug).
- Use vendor slugs from
  [Zephyr's `vendor-prefixes.txt`](https://github.com/zephyrproject-rtos/zephyr/blob/main/dts/bindings/vendor-prefixes.txt).
- Link the manufacturer datasheet **and** an `archived_url`
  (web.archive.org). Quote ≤ 15 words from any source.
- Carry `tested.status` reflecting POC reality
  (`experimental` | `stable` | `production-tested`).

See [`CLAUDE.md`](CLAUDE.md) for the full execution contract and
[`docs/contributing.md`](docs/contributing.md) for the PR checklist.

## Quickstart for agents

```bash
# Local stdio (recommended for personal dev):
pip install hwlib-mcp
claude mcp add hwlib --stdio -- hwlib-mcp

# Hosted / team (Docker, --http):
docker run -d -p 8080:8080 ghcr.io/rnd-southerniot/hwlib-mcp:latest --http
claude mcp add hwlib --transport http http://localhost:8080/mcp
```

`pip install hwlib-mcp` pulls `hwlib-data` transitively, so the catalog is self-contained — no `HWLIB_DATA_DIR` env var needed for default consumption.

Per-agent wiring snippets: [`docs/agents/`](docs/agents/) (Claude Code, Cursor, Cline, Docker).

## Quickstart for tooling

For KiCad / BOM exporters / CI jobs that consume the catalog directly without going through the MCP layer:

```bash
pip install hwlib-data
```

```python
import sqlite3
from hwlib_data import data_path

conn = sqlite3.connect(data_path() / "library.sqlite")
rows = conn.execute(
    "SELECT id, summary FROM components WHERE kind = 'sensor'"
).fetchall()
```

The wheel ships a deterministic snapshot of the catalog — same content as `dist/library.{json,sqlite,index.json}` after a fresh `python -m tools.builder`. Update by `pip install --upgrade hwlib-data`.

Air-gap / offline install: see [`INSTALL-OFFLINE.md`](INSTALL-OFFLINE.md).

## Releases

Tagged releases publish to PyPI (`hwlib-mcp`, `hwlib-data`), GHCR (`ghcr.io/rnd-southerniot/hwlib-mcp`), the versioned doc site, and GitHub Releases (with SHA256SUMS and SLSA attestations).

- [Latest release](https://github.com/rnd-southerniot/hw-registry/releases/latest)
- [All releases](https://github.com/rnd-southerniot/hw-registry/releases)
- [Versioned doc site](https://rnd-southerniot.github.io/hw-registry/) — `latest` alias plus per-version paths
- [Changelog](CHANGELOG.md)

## Licensing

This project is dual-licensed:

- **Code** (everything under `tools/`, `pydantic_models/`, `packages/`,
  `tests/`, `.github/`) — MIT.
- **Prose & data** (everything under `library/`, `docs/`, `examples/`,
  `schemas/`, this README) — CC-BY-4.0.

SPDX identifier: `MIT AND CC-BY-4.0`. See [`LICENSE`](LICENSE).
