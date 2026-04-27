# hw-registry

The single source of truth for our team's curated, battle-tested embedded
hardware library — boards, modules, chips, sensors, drivers, connectors.

## Who consumes this

| Audience            | How                                                          |
|---------------------|--------------------------------------------------------------|
| **Humans**          | Doc site (MkDocs Material), one auto-generated page per part |
| **AI coding agents**| MCP server `hwlib-mcp` (PyPI + `ghcr.io/<your-github-username>/hwlib-mcp`) |
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
git clone git@github.com:<your-github-username>/hw-registry.git
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

## Use it from an agent

```bash
claude mcp add hwlib uvx hwlib-mcp                         # PyPI / stdio
# or
docker run -d -p 8080:8080 ghcr.io/<your-github-username>/hwlib-mcp:latest \
  --http --port 8080
claude mcp add hwlib --transport http http://localhost:8080
```

Per-agent wiring snippets: [`docs/agents/`](docs/agents/).

## Licensing

This project is dual-licensed:

- **Code** (everything under `tools/`, `pydantic_models/`, `packages/`,
  `tests/`, `.github/`) — MIT.
- **Prose & data** (everything under `library/`, `docs/`, `examples/`,
  `schemas/`, this README) — CC-BY-4.0.

SPDX identifier: `MIT AND CC-BY-4.0`. See [`LICENSE`](LICENSE).
