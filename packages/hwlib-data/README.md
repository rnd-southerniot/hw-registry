# hwlib-data

Bundled component data for [hw-registry](https://github.com/rnd-southerniot/hw-registry) as a PyPI data wheel.

## What this package is

A pure-data Python package containing the deterministic bundle of curated embedded hardware components — boards, modules, sensors, drivers, chips, connectors. The bundle ships as three artifacts:

- `library.sqlite` — fully-resolved component catalog, indexed for FTS5 search and direct query
- `library.json` — same data in JSON for tooling that prefers it
- `index.json` — faceted summary (counts by kind, build provenance)

Updates to this package track the *content* of the registry. The MCP server (`hwlib-mcp`) and other consumers update independently.

## Who uses this

- **`hwlib-mcp`** — depends on `hwlib-data` as the data source when `HWLIB_DATA_DIR` isn't set. After `pip install hwlib-mcp`, the MCP server is self-contained.
- **KiCad / BOM tooling** — reads `library.sqlite` directly to resolve component refs without going through the MCP layer.
- **Custom integrations** — any Python tool that wants the catalog without the MCP protocol overhead.

Humans browsing the catalog should use the [doc site](https://rnd-southerniot.github.io/hw-registry/) instead.

## Usage

```python
from hwlib_data import data_path
import sqlite3

conn = sqlite3.connect(data_path() / "library.sqlite")
rows = conn.execute("SELECT id, summary FROM components WHERE kind = 'sensor'").fetchall()
```

The path is also valid for `json.load`:

```python
import json
from hwlib_data import data_path

with open(data_path() / "library.json") as f:
    catalog = json.load(f)
```

## License

Data: **CC-BY-4.0**. Quote, redistribute, build derivatives — attribution required.

## Versioning

`hwlib-data` follows semver against the *bundle schema*, not the component count. Adding a component is a PATCH bump. Adding a column to `library.sqlite` is a MINOR bump. Removing or renaming a column is a MAJOR bump. Component IDs themselves carry their own per-component revision (`MAJOR.MINOR.PATCH` per `BLUEPRINT.md` §6).
