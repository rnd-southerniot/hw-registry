# Claude Code

[Claude Code](https://docs.claude.com/en/docs/claude-code/overview) is Anthropic's official CLI for Claude. It supports MCP servers via `claude mcp add`.

## Local stdio (recommended for personal dev)

```bash
pip install hwlib-mcp
claude mcp add hwlib --stdio -- hwlib-mcp
```

That's it. The next `claude` session has the `hwlib_*` tools available. No env vars to set — `hwlib-mcp` falls back to `hwlib_data.data_path()` when `HWLIB_DATA_DIR` isn't set, and `hwlib-data` is a transitive dep of `hwlib-mcp`.

### Pinned to a specific catalog version

```bash
pip install hwlib-mcp==0.1.0
claude mcp add hwlib --stdio -- hwlib-mcp
```

Pin both packages independently if you want explicit control over the data version separately from the server version:

```bash
pip install hwlib-mcp==0.1.0 hwlib-data==0.1.0
```

## Docker (for hosted / team use)

Run the container in `--http` mode, then point Claude Code at it:

```bash
docker run -d -p 8080:8080 --name hwlib \
    ghcr.io/rnd-southerniot/hwlib-mcp:latest --http
claude mcp add hwlib --transport http http://localhost:8080/mcp
```

The image bakes in a frozen bundle that matches the image tag (a `v0.1.0` image carries the `v0.1.0` bundle). See the [Docker guide](docker.md) for mounting an alternate bundle, the `/health` endpoint, and orchestrator probes.

## Verify the connection

```bash
claude mcp list
```

Should show `hwlib` with status `connected`. If it shows an error, the most common causes:

- `hwlib-mcp` not on `PATH` — confirm `which hwlib-mcp` resolves to your install.
- For HTTP mode: server not bound on `0.0.0.0` (older versions defaulted to `127.0.0.1` and weren't reachable from outside the container — fixed in `v0.1.0`).
- For Docker mode: bundle missing — `docker logs hwlib` shows the structured fail-fast error pointing at `python -m tools.builder --out dist/`.

A live smoke test:

> *"Use the hwlib MCP server. Find the SHT41 sensor's I²C address."*

A working integration returns `0x44` with `0x45` as the alternate. The wired-up agent will call `hwlib_search` → `hwlib_get` rather than guessing.

## CLAUDE.md operating manual

Drop this into a `CLAUDE.md` at the root of any project that consumes the registry. Claude Code loads it automatically; agents read it as part of their context. Keep it ~50 lines: tells the agent the catalog *exists*, never enumerates it.

```markdown
# Embedded HW Library — Agent Operating Manual

A curated component catalog is exposed via the **`hwlib` MCP server**.
Always prefer it over guessing component specs from training data.

## When to call hwlib
- Picking or validating a component (sensor, radio, MCU, regulator)
- I2C addresses, voltage rails, peripheral muxing, strapping pins
- Pinmaps, platformio.ini, sdkconfig.defaults, KiCad refs
- Driver/library selection for ESP-IDF, Arduino, MicroPython, Zephyr

## Efficient tool sequence
1. `hwlib_search` or `hwlib_list` first → ID + 1-line summary only.
2. `hwlib_get` for the 1–3 candidates you actually need; use `fields:` projection.
3. `hwlib_suggest_pinmap` if pins not specified.
4. `hwlib_check_pin_conflicts` BEFORE generating any pin-using code.
5. `hwlib_get_drivers` → manifest snippets.
6. `hwlib_generate_platformio_ini` / `hwlib_generate_sdkconfig` last.

## Forbidden
- Hard-coding I²C addresses or abs-max ratings from memory
- Pasting full datasheets into chat (use `@hwlib://component/{id}` resource)
- Inventing driver package names — call `hwlib_get_drivers`

## Project conventions
- Default framework: ESP-IDF v5.5+. Use new I2C driver, not legacy `i2c.h`.
- LoRaWAN region defaults EU868 unless project README says otherwise.
- ESP32-S3 strapping pins (GPIO0/3/45/46) and USB pins (GPIO19/20) are reserved.
  Let `hwlib_suggest_pinmap` handle this.
```

## Slash commands

The server registers a few prompts as slash-commands when the integration is wired:

- `/scaffold-sensor-node` — board + sensor + radio sketch with full pinmap
- `/audit-pinmap` — validate an existing pinmap against the board's strapping/peripheral constraints
- `/swap-component` — suggest a drop-in replacement (e.g. SHT41 → SHT45) with delta tables

These are conveniences over the raw tools; the agent can produce equivalent output by chaining the tools manually.

## Resource references

In Claude Code, you can `@`-mention MCP resources:

- `@hwlib://component/sensors/sensirion/sht41` — full record of one component
- `@hwlib://catalog/index` — high-level counts + category tree
- `@hwlib://schema/sensor` — JSON Schema for that kind

Useful for pinning context to specific catalog entries without burning tokens on tool-call round-trips.
