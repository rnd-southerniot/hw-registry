# Cursor

[Cursor](https://cursor.sh/) supports MCP servers via `.cursor/mcp.json`. Two files do the wiring:

- `.cursor/mcp.json` — server config (transport, command, args)
- `.cursor/rules/00-hwlib.mdc` — operating manual the agent reads as context

Both live in the project root.

## Local stdio

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "hwlib": {
      "command": "hwlib-mcp",
      "args": []
    }
  }
}
```

Install the server first:

```bash
pip install hwlib-mcp
```

Cursor spawns `hwlib-mcp` as a subprocess on first tool call.

### Pinned version

```bash
pip install hwlib-mcp==0.1.0
```

`.cursor/mcp.json` doesn't need to change — the resolved binary is whatever's on `PATH`.

## Docker / HTTP

Run the container, then point Cursor at it:

```bash
docker run -d -p 8080:8080 --name hwlib \
    ghcr.io/rnd-southerniot/hwlib-mcp:latest --http
```

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "hwlib": {
      "url": "http://localhost:8080/mcp",
      "transport": "http"
    }
  }
}
```

## Operating manual rule

`.cursor/rules/00-hwlib.mdc`:

```markdown
---
description: Use the hwlib MCP server for hardware component data
alwaysApply: true
---

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
- Pasting full datasheets into chat
- Inventing driver package names — call `hwlib_get_drivers`

## Project conventions
- Default framework: ESP-IDF v5.5+. Use new I2C driver, not legacy `i2c.h`.
- LoRaWAN region defaults EU868 unless project README says otherwise.
- ESP32-S3 strapping pins (GPIO0/3/45/46) and USB pins (GPIO19/20) are reserved.
  Let `hwlib_suggest_pinmap` handle this.
```

## Verify

Cursor's MCP status panel (Settings → MCP) should show `hwlib` as connected after the next restart. The smoke test:

> *"Use the hwlib MCP server. Find the SHT41 sensor's I²C address."*

Returns `0x44` if wired correctly.
