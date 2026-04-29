# Cline

[Cline](https://cline.bot/) is a VS Code extension MCP-compatible client. Configuration lives in a JSON file outside the project tree (per-user, not per-project) and operating-manual rules in `.clinerules/`.

## MCP settings file paths

The `cline_mcp_settings.json` file location depends on the OS:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Cline/cline_mcp_settings.json` |
| Linux | `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| Windows | `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json` |

If the file doesn't exist, Cline creates it on first MCP-related action.

## Local stdio

```bash
pip install hwlib-mcp
```

Edit `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "hwlib": {
      "command": "hwlib-mcp",
      "args": [],
      "disabled": false
    }
  }
}
```

The `"disabled": false` is explicit because Cline's UI lets users toggle servers without removing them; saving the JSON-form-true value here keeps the config reproducible.

## Docker / HTTP

```bash
docker run -d -p 8080:8080 --name hwlib \
    ghcr.io/rnd-southerniot/hwlib-mcp:latest --http
```

```json
{
  "mcpServers": {
    "hwlib": {
      "url": "http://localhost:8080/mcp",
      "transport": "http",
      "disabled": false
    }
  }
}
```

## Operating manual

`.clinerules/00-hwlib.md` (project root, applies to projects that opt in):

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
- Pasting full datasheets into chat
- Inventing driver package names — call `hwlib_get_drivers`

## Project conventions
- Default framework: ESP-IDF v5.5+. Use new I2C driver, not legacy `i2c.h`.
- LoRaWAN region defaults EU868 unless project README says otherwise.
- ESP32-S3 strapping pins (GPIO0/3/45/46) and USB pins (GPIO19/20) are reserved.
  Let `hwlib_suggest_pinmap` handle this.
```

## Verify

After saving the settings file, restart VS Code (or use Cline's "Reload MCP servers" command). The MCP panel should show `hwlib` as connected. Smoke test:

> *"Use the hwlib MCP server. Find the SHT41 sensor's I²C address."*

Returns `0x44` if wired correctly.
