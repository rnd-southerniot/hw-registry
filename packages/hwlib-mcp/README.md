# hwlib-mcp

An MCP server exposing the `hw-registry` component bundle to AI coding
agents — Claude Code, Cursor, Cline, and anything else that speaks
[Model Context Protocol](https://modelcontextprotocol.io/).

The server is **read-only**. It serves the deterministic bundle produced
by [`hwlib-build`](../../tools/builder/) (see [BLUEPRINT.md](../../docs/internal/BLUEPRINT.md)).

## Install

```bash
uvx hwlib-mcp        # PyPI publish lands in Prompt 10
```

For local dev, see the [root README](../../README.md) `make mcp-install`.

## Configuration

| Environment variable | Default                      | Purpose                                     |
|----------------------|------------------------------|---------------------------------------------|
| `HWLIB_DATA_DIR`     | `<repo>/dist`                | Directory holding `library.sqlite` + friends |

If `library.sqlite` is missing the server prints a diagnostic and exits
non-zero — it does not auto-build. Run `python -m tools.builder --out
dist/` first.

## Wiring it into agents

### Claude Code

```bash
claude mcp add hwlib uvx hwlib-mcp
# or, pinned to a release:
claude mcp add hwlib uvx --from hwlib-mcp==0.1.0 hwlib-mcp
```

### Cursor

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "hwlib": {
      "command": "uvx",
      "args": ["hwlib-mcp"]
    }
  }
}
```

### Cline

VS Code settings → `cline.mcpServers`:

```json
{
  "hwlib": {
    "command": "uvx",
    "args": ["hwlib-mcp"]
  }
}
```

## Hosted / Streamable HTTP

```bash
HWLIB_DATA_DIR=/srv/hwlib/dist hwlib-mcp --http --port 8080
```

Agents connect via `claude mcp add hwlib --transport http
http://host:8080`. **Stdio is the default**; `--http` is for shared /
hosted deployments. SSE is intentionally not supported (deprecated in
MCP 2025-03-26 spec).

## Tool surface

| Tool                          | Returns                | Token-discipline note                                |
|-------------------------------|------------------------|------------------------------------------------------|
| `hwlib_search`                | summaries (≤ 20)       | call BEFORE `hwlib_get`                              |
| `hwlib_list`                  | paginated summaries    | filter by kind / interface / voltage                 |
| `hwlib_get`                   | one full record        | always pass `fields:` to project                     |
| `hwlib_check_pin_conflicts`   | `{ok, diagnostics[]}`  | call BEFORE generating any pin-using code            |
| `hwlib_compatible_modules`    | summaries              | best-effort; absence ≠ incompatible                  |
| `hwlib_get_drivers`           | per-framework bindings | use when scaffolding firmware                        |
| `hwlib_suggest_pinmap`        | stub                   | post-MVP; alternative_tool: `hwlib_check_pin_conflicts` |
| `hwlib_generate_platformio_ini` | stub                 | post-MVP; alternative_tool: `hwlib_get_drivers`      |
| `hwlib_generate_sdkconfig`    | stub                   | post-MVP; alternative_tool: `hwlib_get_drivers`      |
| `hwlib_get_kicad_refs`        | stub                   | post-MVP; alternative_tool: `hwlib_get fields=['kicad']` |

Resources (Claude Code first-class, lower-tier elsewhere):

- `hwlib://component/{id}`
- `hwlib://catalog/index`
- `hwlib://schema/{kind}`

Every capability is also available as a Tool — Resources are an
ergonomics win for Claude Code's @-mention but never the only path.

## Debugging

```bash
hwlib-mcp --log-level debug             # verbose logs to stderr
hwlib-mcp --http --port 8080            # then point MCP Inspector at localhost:8080
```

Errors are returned as structured shapes, never exceptions:
`{"status": "not_found", "id": "...", "suggestions": [...]}` etc. If you
see a Python traceback in agent output, please file a bug.
