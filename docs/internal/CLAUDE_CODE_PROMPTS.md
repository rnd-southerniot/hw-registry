# Hardware Registry — Claude Code Prompt Pack

**Target repo name:** `hw-registry`
**Driver:** Claude Code (paste prompts one at a time, review each diff)
**MVP coverage:** 5 seed components from the blueprint
**MCP packaging:** PyPI (`uvx hwlib-mcp`) **and** Docker (`ghcr.io/<you>/hwlib-mcp`)

---

## How to use this pack

1. Create empty repo locally:
   ```bash
   mkdir hw-registry && cd hw-registry && git init -b main
   ```
2. Open Claude Code in that directory (`claude` in terminal, or VS Code extension).
3. Paste **Prompt 0** first — it bootstraps `CLAUDE.md` and project conventions for the agent itself.
4. After each prompt, the agent will pause, show a diff, and ask to commit. **Always review the diff** before approving. Run the verification step it suggests.
5. Make the commit, then paste the next prompt.
6. If a prompt produces something you don't like, say "revert and try again with X" — Claude Code handles the rollback.

**Substitute `<your-github-username>` and `<your-email>`** in prompts where indicated.

---

## Prompt 0 — Bootstrap project rules

```text
Bootstrap this empty repo as `hw-registry`, the source of truth for our team's
embedded hardware library. Do these in order, ONE commit per step:

1. Create CLAUDE.md at the repo root with:
   - Project mission: curated, battle-tested hardware components (boards, modules,
     sensors, drivers, connectors) consumed by humans, AI agents (via MCP),
     KiCad/PCB tooling, and BOM exporters.
   - Source-of-truth rule: YAML files under library/ are canonical. Schemas under
     schemas/ are GENERATED from Pydantic models in pydantic_models/. Never
     hand-edit schemas/.
   - Naming rule: id MUST equal the relative path slug, e.g.
     sensors/sensirion/sht41 ⇒ library/sensors/sensirion/sht41.yaml.
   - Vendor slugs come from Zephyr's vendor-prefixes.txt (lowercase).
   - Forbidden: hard-coded secrets; pasting full datasheets; embedding vendor
     pinout images (link instead).
   - SemVer for components: MAJOR = pin/electrical incompatibility, MINOR =
     behavior change, PATCH = errata/silkscreen.
   - Commit hygiene: conventional commits (feat:, fix:, docs:, chore:, ci:).
   - Always run `pre-commit run --all-files` before committing once it's
     installed.

2. Create README.md (concise, ≤80 lines) covering: what this is, who it's for
   (humans / agents / KiCad / BOM), quickstart for contributors (clone, install
   pre-commit, add a component, open PR), and links to docs/, schemas/, tools/.

3. Create LICENSE — dual-licensed: code under MIT, prose/data under CC-BY-4.0.
   Use SPDX expression "MIT AND CC-BY-4.0" in README.

4. Create .gitignore for Python (build/, dist/, __pycache__/, .venv/, *.egg-info,
   .pytest_cache, .ruff_cache, .mypy_cache, site/, node_modules/) and editor
   junk (.idea/, .vscode/ except settings.json, .DS_Store).

5. Create .gitattributes with LFS rules:
   *.pdf filter=lfs diff=lfs merge=lfs -text
   *.step filter=lfs diff=lfs merge=lfs -text
   *.stp  filter=lfs diff=lfs merge=lfs -text
   *.wrl  filter=lfs diff=lfs merge=lfs -text
   *.png  filter=lfs diff=lfs merge=lfs -text
   *.jpg  filter=lfs diff=lfs merge=lfs -text
   *.jpeg filter=lfs diff=lfs merge=lfs -text

6. Create .editorconfig (utf-8, lf, 2-space yaml, 4-space python, trim trailing
   whitespace, insert final newline).

DO NOT install dependencies or run anything yet — just create files.

Commit each step separately with conventional-commit messages. Stop and show me
the diff after step 6.
```

**Verify after Prompt 0:**
```bash
ls -la
cat CLAUDE.md | head -30
git log --oneline
```

---

## Prompt 1 — Python project scaffold + Pydantic models

```text
Scaffold the Python tooling. We use Python 3.12+ and `uv` as the package
manager.

1. Create pyproject.toml with:
   - Build system: hatchling
   - Project name: hw-registry-tools (we'll publish hwlib-data and hwlib-mcp
     as separate distributions later — this pyproject is for the dev tooling)
   - Python ≥ 3.12
   - Runtime deps: pydantic>=2.8, pyyaml>=6.0, jsonschema>=4.23, click>=8.1
   - Dev deps (optional group "dev"): pytest>=8, pytest-cov, syrupy, ruff,
     mypy, pre-commit, check-jsonschema
   - Tool config sections for ruff (line length 100, select E/F/I/UP/B/SIM,
     ignore E501 in tests), mypy (strict, exclude tests), pytest (testpaths,
     -ra --strict-markers).

2. Create pydantic_models/ package:
   - __init__.py exporting all models
   - common/__init__.py
   - common/identifiable.py — base class `Identifiable` with apiVersion (Literal
     "hwreg/v1"), kind (Literal enum), id (str, regex
     ^[a-z]+/[a-z0-9-]+/[a-z0-9-]+$), revision (semver regex), summary
     (str, max 120), tested (Tested submodel), lifecycle (Literal enum),
     code_owner (str | None).
   - common/electrical.py — `Electrical` (vcc: VccSpec, logic: LogicSpec,
     current_draw: CurrentDraw|None, power_budget_mA: float|None).
   - common/pin.py — `Pin` (id, aliases:list[str], package_pin:int|str|None,
     voltage_domain:str|None, default:str, alt_functions:list[AltFunction]).
   - common/assets.py — `Asset` (path, lfs:bool, license:str), `Datasheet`
     (primary_url, archived_url|None, sha256|None).
   - board.py, module.py, chip.py, sensor.py, connector.py, driver.py — each
     extending Identifiable.

   For sensor.py model these required fields:
     vendor, manufacturer_part_number, electrical: Electrical,
     interface: Interface (type: i2c|spi|uart|onewire|analog|pwm),
     constraints: SensorConstraints, package: Package, drivers: list[str]
     (cross-refs), kicad: KicadRefs|None, external_refs: ExternalRefs|None,
     assets: AssetBundle|None.

   For board.py model: vendor, manufacturer_part_number, peripherals,
   electrical, discovery, strapping_pins:list[str], reserved_pins:list[str],
   pins:list[Pin], expansion_headers, build (frameworks/flash/ram/psram), kicad,
   external_refs, assets, inherits_from:list[str].

   For module.py: similar to board but with `contains:list[ContainedPart]`
   and `overrides:dict` and `package` and `firmware_options:list[FirmwareOption]`.

   For driver.py: applies_to:list[str], bindings:list[DriverBinding] with
   framework (esp-idf|arduino|zephyr|micropython|platformio), version_constraint,
   source/component/library/module fields per framework, tested_with, license.

   Use ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=False).
   Match field names EXACTLY to the YAML examples in CLAUDE.md / blueprint
   (snake_case in YAML, snake_case in Pydantic).

3. Create tools/__init__.py and tools/generate_schemas.py:
   - CLI script (`python -m tools.generate_schemas` or `hwlib-genschema` later)
     that walks pydantic_models, calls model_json_schema(mode="validation"),
     writes schemas/<kind>.schema.json with stable key ordering and 2-space
     indent. Uses jsonref to resolve before writing? NO — keep $refs.

4. Run `python -m tools.generate_schemas` once and commit the result under
   schemas/.

5. Add a tiny smoke test tests/test_models_smoke.py that imports each model
   and constructs a minimal valid instance.

DO NOT add any YAML components yet — that's the next prompt.
Stop after committing. Show me the model files (just file list and one
example, e.g. sensor.py) and the generated sensor.schema.json.
```

**Verify:**
```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m tools.generate_schemas
pytest -q
ls schemas/
```

---

## Prompt 2 — Pre-commit hooks and lint baseline

```text
Wire up pre-commit so contributors and CI run identical checks.

1. Create .pre-commit-config.yaml with these hooks:
   - pre-commit-hooks: trailing-whitespace, end-of-file-fixer, check-merge-conflict,
     check-yaml (multi-document false), check-added-large-files (maxkb=500,
     enforce-all)
   - astral-sh/ruff-pre-commit: ruff (with --fix), ruff-format
   - python-jsonschema/check-jsonschema:
       * one hook validating library/boards/**/*.yaml against schemas/board.schema.json
       * one for library/sensors/**/*.yaml against schemas/sensor.schema.json
       * one for library/modules/**/*.yaml against schemas/module.schema.json
       * one for library/chips/**/*.yaml against schemas/chip.schema.json
       * one for library/drivers/**/*.yaml against schemas/driver.schema.json
       * one for library/connectors/**/*.yaml against schemas/connector.schema.json
   - adrienverge/yamllint: with config below
   - gitleaks/gitleaks: protect, redact
   - lycheeverse/lychee (manual stage only — too slow for every commit)
   - local hook "validate-slugs" calling `python -m tools.validate --check
     slug-equals-path` (we'll create this tool below)

2. Create .yamllint.yaml: extends default, line-length 120, indentation 2-space
   with consistent, document-start disabled, truthy allowed-values
   ['true','false'], comments-indentation disabled.

3. Create tools/validate.py — Click CLI with subcommands:
   - slug-equals-path: walks library/, asserts `id` field equals relative path
     minus `.yaml` extension, exit non-zero on mismatch.
   - refs-resolve: parses every `inherits_from`, `contains[].ref`,
     `applies_to[]`, `drivers[]` and confirms the referenced YAML exists.
   - inheritance-cycle: builds a DAG of inherits_from and detects cycles.
   - Catch-all `all` subcommand running every check.

4. Add a Makefile (or justfile if you prefer — pick one and stick with it)
   with targets: install, schema, validate, test, lint, fmt, clean.

5. Run `pre-commit install` and `pre-commit run --all-files`. Fix any failures
   (likely whitespace/EOF in earlier files).

Commit hooks config and any auto-fixes separately from validate.py.
Stop after green pre-commit. Show me the .pre-commit-config.yaml and the
output of `pre-commit run --all-files`.
```

**Verify:**
```bash
pre-commit run --all-files
python -m tools.validate all
```

---

## Prompt 3 — Seed components: 5 YAMLs

```text
Author the 5 seed components from the blueprint. Reference the YAML examples
in the blueprint exactly — those are the canonical shapes. Each file must
include the schema directive line on top:

   # yaml-language-server: $schema=../../../schemas/<kind>.schema.json

Files to create:

1. library/boards/espressif/esp32-s3-devkitc-1.yaml
   - id: boards/espressif/esp32-s3-devkitc-1
   - revision: 1.1.0
   - tested.status: production-tested, by: <your-email>, date: 2026-02-14
   - Full pin list: enumerate ALL exposed GPIOs (GPIO0..GPIO21, GPIO26..GPIO48
     where applicable on the WROOM-1 module). For each pin set aliases (USB
     pins reserved, I2C default pads, SPI default pads, ADC1/ADC2 channels),
     alt_functions matching ESP32-S3 mux table.
   - strapping_pins: [GPIO0, GPIO3, GPIO45, GPIO46]
   - reserved_pins: [GPIO19, GPIO20]   # USB D+/D-
   - discovery.usb: VID/PID for native USB (303A:1001) and CP210x bridge
     (10C4:EA60).
   - peripherals counts as in the ESP32-S3 datasheet.
   - inherits_from: [modules/espressif/esp32-s3-wroom-1@1.0.0] (we'll create
     module file in step 2).
   - kicad block with placeholder symbol/footprint paths.

2. library/modules/espressif/esp32-s3-wroom-1.yaml
   - Minimal but valid: covers the WROOM-1 RF module specs (8MB flash,
     8MB octal PSRAM N8R8 variant), package LCC-WROOM-1, antenna PCB,
     RF certifications.

3. library/modules/rakwireless/rak3172.yaml
   - Use the exact YAML from the blueprint section 3.2 verbatim.
   - inherits_from references chips/st/stm32wle5jc — we won't create the chip
     YAML this round, so use a STUB: leave inherits_from as
     [chips/st/stm32wle5jc@1.0.0] AND add a corresponding stub
     library/chips/st/stm32wle5jc.yaml (kind: chip, status: stub) so refs
     resolve.

4. library/sensors/sensirion/sht41.yaml — Use blueprint section 3.3 verbatim.

5. library/sensors/ti/ads1115.yaml
   - I2C, 4-channel 16-bit ADC, address 0x48 with options [0x48, 0x49,
     0x4A, 0x4B] via ADDR pin, supply 2.0–5.5V (so five_v_tolerant: true on
     logic), package MSOP-10, drivers cross-ref `drivers/ti-ads1115`.

6. library/drivers/sensirion-sht41.yaml — verbatim from blueprint section 3.4.

7. library/drivers/ti-ads1115.yaml — bindings for esp-idf
   (espressif/esp_ads111x), arduino (Adafruit_ADS1X15 ≥ 2.4), zephyr
   (compatible "ti,ads1115"), micropython (community ads1x15 module).

For ANY field where you don't have authoritative numbers, use the official
manufacturer datasheet — quote no more than 15 words from any source and never
copy a table. If a field is genuinely unknown, OMIT it (Pydantic models should
mark it Optional). Do not invent values.

Run `pre-commit run --all-files` after authoring. The schema validation must
pass. The validate.py refs-resolve must pass.

Stop after green checks. Show me the file tree under library/ and one full
YAML (sht41.yaml) for me to spot-check.
```

**Verify:**
```bash
tree library/
pre-commit run --all-files
python -m tools.validate all
```

---

## Prompt 4 — Bundle builder

```text
Build the deterministic bundle that downstream consumers will read.

1. Create tools/builder/ package:
   - __init__.py
   - __main__.py exposing CLI: `python -m tools.builder --out dist/`
   - build.py with the build pipeline.

2. Pipeline:
   a. Walk library/**/*.yaml. For each file, load YAML, validate against the
      matching Pydantic model (re-validate, don't trust filesystem).
   b. Resolve inherits_from chain (depth-first, detect cycles, deep-merge with
      child overriding parent — child's `overrides` block applied last).
   c. Compute a flat object: { components: { "<id>": <resolved record>, ... },
      meta: { generated_at, git_sha, version, count_by_kind } }.
   d. Write dist/library.json (sorted keys, 2-space indent, deterministic).
   e. Write dist/library.sqlite:
        - Table `components` (id PK, kind, vendor, mpn, summary, lifecycle,
          revision, json TEXT — full record).
        - FTS5 virtual table `components_fts` over (id, summary, vendor, mpn,
          tags) with porter tokenizer. Populate via triggers or one-shot insert.
        - Indexes on kind, vendor, lifecycle.
   f. Write dist/index.json — small (≤50KB) summary: counts per kind,
      list of {id, kind, summary} for fast catalog browsing without loading
      the full bundle.

3. Determinism: use sort_keys=True everywhere; pin SQLite page_size=4096
   user_version to bundle schema version (start at 1); strip non-deterministic
   timestamps when CI env var SOURCE_DATE_EPOCH is set.

4. Add tests/test_builder.py:
   - test_bundle_roundtrip: build, then load library.json and library.sqlite
     and assert the 5 seed components are present with expected ids.
   - test_inheritance_resolution: assert RAK3172 record after build contains
     the merged STM32WLE5JC fields where not overridden.
   - test_determinism: run build twice with SOURCE_DATE_EPOCH set, assert byte-
     identical output.

5. Add syrupy snapshot test tests/test_bundle_snapshot.py that snapshots
   the generated index.json. Reviewers will see snapshot diffs in PRs.

Commit. Stop after `pytest -q` is green.
```

**Verify:**
```bash
python -m tools.builder --out dist/
sqlite3 dist/library.sqlite "SELECT id, kind FROM components ORDER BY id;"
jq '.meta' dist/library.json
pytest -q
```

---

## Prompt 5 — Pin-conflict graph validator

```text
Implement the system-level pin-conflict checker described in the blueprint
section 3.5.

1. Create tools/conflicts/ package:
   - graph.py — build a graph from a system YAML using networkx (add to
     pyproject deps). Nodes: PhysicalPin, LogicalSignal, PeripheralInstance,
     ComponentInstance. Edges typed: uses, alt_function, i2c_address,
     voltage_requires.
   - rules.py — pure functions, each returning list[Diagnostic]:
       gpio_double_use, i2c_address_clash, voltage_mismatch,
       missing_required_interrupt, alt_function_unsupported, strapping_pin_misuse
       (severity WARN), current_budget_exceeded (WARN),
       missing_i2c_pullups (WARN).
   - sarif.py — convert list[Diagnostic] to SARIF 2.1.0 JSON for IDE.
   - cli.py — `hwlib-check-conflicts <system.yaml> [--format text|sarif|json]`.

2. Add system fixture loader: a `system:` YAML with `board:`, `components:`
   (list of {ref, instance, pins: {alias_or_logical: physical_gpio}}). The
   loader resolves refs via the bundle (require dist/library.sqlite to exist;
   error if not built).

3. Create tests/fixtures/system_examples/lorawan-node.yaml — exactly as in
   blueprint section 3.5. Add a second fixture
   tests/fixtures/system_examples/conflict-i2c-addr.yaml — two SHT41s on the
   same bus to trigger I2C clash.

4. Add tests/test_conflicts.py covering: clean system → 0 errors;
   conflict-i2c-addr → exactly 1 ERROR with code I2C_ADDR_CLASH;
   strapping pin misuse → 1 WARN.

5. Wire `hwlib-check-conflicts` as a console_script entry point.

Commit. Stop after green tests.
```

**Verify:**
```bash
hwlib-check-conflicts tests/fixtures/system_examples/lorawan-node.yaml
hwlib-check-conflicts tests/fixtures/system_examples/conflict-i2c-addr.yaml
pytest tests/test_conflicts.py -v
```

---

## Prompt 6 — MCP server (PyPI distribution)

```text
Build the FastMCP server that exposes the bundle to AI agents. Package as
`hwlib-mcp` for PyPI / uvx.

1. Create a SEPARATE distribution under packages/hwlib-mcp/:
   - packages/hwlib-mcp/pyproject.toml — name "hwlib-mcp", deps fastmcp>=2.0,
     hwlib-data (we'll publish this in a later prompt; for now reference
     the local builder output via path dep in dev mode).
   - packages/hwlib-mcp/src/hwlib_mcp/__init__.py
   - packages/hwlib-mcp/src/hwlib_mcp/server.py
   - packages/hwlib-mcp/src/hwlib_mcp/__main__.py (so `python -m hwlib_mcp` works)

2. server.py — FastMCP instance with these tools (match the blueprint
   section 7.1 exactly; copy tool descriptions verbatim because agent quality
   depends on them):

   @mcp.tool() async def hwlib_search(query: str, kind: str | None = None,
       limit: int = 10) -> list[ComponentRef]
   @mcp.tool() async def hwlib_list(kind: str | None = None,
       interface: str | None = None, voltage_compatible_with: float | None = None,
       page: int = 1, page_size: int = 20) -> PagedComponents
   @mcp.tool() async def hwlib_get(id: str, fields: list[str] | None = None) -> dict
   @mcp.tool() async def hwlib_check_pin_conflicts(board_id: str,
       components: list[ComponentAssignment]) -> ConflictReport
   @mcp.tool() async def hwlib_compatible_modules(board_id: str,
       interface: str | None = None) -> list[ComponentRef]
   @mcp.tool() async def hwlib_get_drivers(component_id: str,
       framework: str | None = None) -> list[DriverBindingOut]

   For NOW, stub these (return NotImplementedError-shaped error in the
   response — we'll fill them in next iterations):
   - hwlib_suggest_pinmap
   - hwlib_generate_platformio_ini
   - hwlib_generate_sdkconfig
   - hwlib_get_kicad_refs

3. Resources (URI templates):
   - hwlib://component/{id}
   - hwlib://catalog/index
   - hwlib://schema/{kind}

4. Hard caps in tool DESCRIPTIONS (not just defaults): "Returns at most 20
   results — paginate with the page parameter." "Always call hwlib_search or
   hwlib_list before hwlib_get." This shapes agent behavior.

5. Configuration: the server reads `HWLIB_DATA_DIR` env var (default to a
   bundled wheel data path). For local dev, point it at ../../dist/.

6. Transport: stdio by default (for Claude Code). Add --http to run
   Streamable HTTP on a configurable --port and --host. In --http mode,
   --host defaults to 0.0.0.0 (externally reachable, matches uvicorn /
   gunicorn / flask conventions). When --host is set without --http,
   emit a stderr warning and ignore.

7. Tests under packages/hwlib-mcp/tests/:
   - test_server_smoke.py: instantiate FastMCP server in-process, call each
     tool, assert response shape.
   - Use FastMCP's in-memory client for tests (no real stdio needed).

8. Console scripts in pyproject: `hwlib-mcp = hwlib_mcp.__main__:main`.

Commit. Stop after green tests.
```

**Verify:**
```bash
cd packages/hwlib-mcp
uv pip install -e ".[dev]"
HWLIB_DATA_DIR=../../dist hwlib-mcp --help
pytest -q
```

---

## Prompt 7 — Docker image for MCP server

```text
Containerize the MCP server for ghcr.io distribution.

1. Create packages/hwlib-mcp/Dockerfile:
   - Multi-stage build: stage 1 python:3.12-slim with uv, install hwlib-mcp
     and copy dist/library.{json,sqlite} into /opt/hwlib/data; stage 2
     gcr.io/distroless/python3-debian12 with copied site-packages and data.
   - Non-root user (uid 65532).
   - ENTRYPOINT ["python", "-m", "hwlib_mcp"]
   - Expose 8080 (only used in --http mode).
   - Labels: org.opencontainers.image.source, .description, .licenses
     "MIT AND CC-BY-4.0".

2. Create packages/hwlib-mcp/.dockerignore.

3. Create docker-compose.yml at repo root for local testing:
   - service hwlib-mcp using build context packages/hwlib-mcp/
   - volume mount of ./dist to /opt/hwlib/data:ro
   - command: ["--http", "--port", "8080"]
   - port 8080:8080.

4. Add docs/agents/docker.md with quickstart for running the container in
   --http mode and pointing Claude Code at it via `claude mcp add` with
   transport http.

5. Test:
   - `docker build` succeeds; `docker run --rm hwlib-mcp:dev` is a smoke
     test — the bundle is baked into the image at build time, so default
     run starts the server cleanly and exits on stdin EOF.
   - The bundle-missing fast-fail path is exercised by mounting an empty
     volume over /opt/hwlib/data, which masks the baked-in bundle and
     triggers the structured error from Prompt 6 (exit=2).

Stop after green local build. Commit.
```

**Verify:**
```bash
# build + smoke (bundle baked in; banner + clean exit on EOF)
bash packages/hwlib-mcp/scripts/build-image.sh
docker run --rm hwlib-mcp:dev

# compose /health — poll until healthy (no fixed sleep; uvicorn cold-start varies)
docker compose up -d
for i in $(seq 1 60); do
    h=$(docker compose ps --format json hwlib-mcp 2>/dev/null \
        | jq -r 'if type=="array" then .[0] else . end | .Health // empty')
    [ "$h" = "healthy" ] && break
    sleep 1
done
curl -s localhost:8080/health | jq .
docker compose down

# bundle-missing fast-fail (empty-volume mask; expect exit=2)
mkdir -p /tmp/empty
docker run --rm -v /tmp/empty:/opt/hwlib/data hwlib-mcp:dev || echo exit=$?
```

---

## Prompt 8 — MkDocs Material doc site

```text
Build the human-facing doc site that auto-generates one page per component.

1. Add docs/ directory:
   - docs/mkdocs.yml — Material theme, navigation tabs + sections, search,
     mermaid via pymdownx.superfences, admonitions, tabbed code blocks,
     content.code.copy, content.tabs.link, repo_url and edit_uri set.
   - docs/requirements.txt — mkdocs-material, mkdocs-gen-files,
     mkdocs-literate-nav, mkdocs-section-index, mkdocs-macros-plugin,
     pymdown-extensions, mike (for versioning later).
   - docs/index.md — landing page: what this is, search box, top 5 components
     by `tested.status: production-tested`.
   - docs/contributing.md — covers PR template, required fields, POC evidence
     guidance, KiCad symbol policy.
   - docs/architecture.md — short overview pointing at the blueprint.
   - docs/agents/index.md — how to wire Claude Code, Cursor, Cline to the MCP
     server.

2. docs/gen_component_pages.py (mkdocs-gen-files hook):
   - Reads dist/library.json (require it exists; error if not built).
   - For each component, emits a virtual page at
     docs/components/<kind>/<vendor>/<part>.md with:
       - Title (summary)
       - Identity table (id, vendor, MPN, revision, lifecycle, tested status)
       - Pinout (if pins present): rendered as Markdown table
       - Electrical specs table
       - Drivers list
       - KiCad refs
       - "Used in" cross-refs (other components that reference this one in
         contains/inherits_from/applies_to)
       - Datasheet link with archived URL
   - Build a `components/index.md` with faceted lists by kind.
   - Use mkdocs-literate-nav for the auto nav tree.

3. Wire the build:
   - Make target `docs`: build dist/ first, then `mkdocs build --strict`.
   - Output to site/.

4. Test locally:
   - python -m tools.builder --out dist/
   - cd docs && mkdocs serve

Stop after the site builds with --strict and renders the 5 seed components.
Commit.
```

**Verify:**
```bash
make docs
cd docs && mkdocs serve  # open http://127.0.0.1:8000
```

---

## Prompt 9 — GitHub Actions CI

```text
Author CI. Branch protection will reference these check names — get them right
the first time.

Create .github/workflows/ci.yml with these jobs (each in its own `job:` block,
not a matrix; we want individual required-status-checks):

1. lint — runs pre-commit run --all-files. Sets up Python 3.12 with uv and
   caches ~/.cache/pre-commit.

2. schema-validate — depends on lint. Installs runtime deps. Runs
   `python -m tools.generate_schemas` THEN `git diff --exit-code schemas/` to
   catch schemas committed out of sync with models. Then runs check-jsonschema
   against every YAML under library/.

3. validate-semantic — depends on schema-validate. Runs `python -m
   tools.validate all` (slug-equals-path, refs-resolve, inheritance-cycle).

4. conflict-tests — depends on validate-semantic. Runs `pytest
   tests/test_conflicts.py -v`.

5. secret-scan — runs gitleaks-action on full history (`fetch-depth: 0`).

6. build-bundle — depends on validate-semantic. Builds dist/, runs golden
   snapshot test, uploads dist/ as artifact named "bundle".

7. build-mcp — depends on build-bundle. Builds the hwlib-mcp wheel and runs
   its tests. Uploads wheel as artifact.

8. build-docs — depends on build-bundle. Downloads bundle artifact, runs
   `mkdocs build --strict`, uploads site/ as artifact.

9. build-docker — depends on build-bundle. Builds the Docker image but does
   NOT push (push happens in release.yml). Uses docker/setup-buildx + cache.

10. preview-deploy — depends on build-docs. Runs only on pull_request. Deploys
    site/ to Cloudflare Pages or GitHub Pages preview using the deploy-pages
    action with a unique URL per PR. Comments PR with preview link.

Trigger: on: pull_request, push to main, workflow_dispatch.
Permissions block at top: contents: read, pull-requests: write,
actions: read.
Concurrency: group ${{ github.workflow }}-${{ github.ref }} cancel-in-progress
true.

Also create .github/CODEOWNERS:
   /                       @<your-github-username>
   /library/boards/        @<your-github-username>
   /library/sensors/       @<your-github-username>
   /library/modules/       @<your-github-username>
   /library/drivers/       @<your-github-username>
   /.github/               @<your-github-username>
   /schemas/               @<your-github-username>

And .github/PULL_REQUEST_TEMPLATE.md with checklists:
   - [ ] tested.status accurately reflects POC reality
   - [ ] Datasheet linked + archived (web.archive.org URL)
   - [ ] Pin map verified against datasheet
   - [ ] No copyrighted images embedded (links only)
   - [ ] KiCad symbol matches MPN exactly
   - [ ] `pre-commit run --all-files` passes locally
   - [ ] `python -m tools.builder --out dist/` succeeds
   Plus three radio sections: kind (board/module/sensor/driver/connector),
   tier (experimental/stable/production-tested), and "POC evidence" free-text
   field for repo URL or photo path.

And .github/ISSUE_TEMPLATE/component-bug.yml + new-component-request.yml +
deprecation-notice.yml as YAML form templates.

Commit. Don't try to actually deploy preview — the CF Pages token won't
exist yet.
```

**Verify:**
```bash
# After pushing the branch:
# - Open a PR on GitHub
# - Watch the Actions tab; all jobs except preview-deploy should pass
# - Configure branch protection: require all listed checks
```

---

## Prompt 10 — Release workflow + agent integration docs

```text
Final wiring: tagged releases publish PyPI + Docker + GitHub Release artifacts
with attestations. Then ship the agent-side integration docs.

1. Create .github/workflows/release.yml:
   - Triggered on tag push matching `v[0-9]+.[0-9]+.[0-9]+`.
   - Job 1 build: builds dist/, hwlib-mcp wheel, hwlib-data wheel (a thin wheel
     that bundles dist/library.{json,sqlite} as package data).
   - Job 2 attest: uses actions/attest-build-provenance@v1 and
     actions/attest-sbom@v4 (CycloneDX format) on every artifact.
   - Job 3 publish-pypi: trusted publishing (OIDC) for both hwlib-mcp and
     hwlib-data. NO API tokens.
   - Job 4 publish-docker: docker/login-action with GITHUB_TOKEN to ghcr.io,
     pushes ghcr.io/<your-github-username>/hwlib-mcp:<tag> and :latest. Uses
     docker/build-push-action with provenance + sbom enabled.
   - Job 5 github-release: creates a GitHub Release with body autogenerated
     from CHANGELOG.md (use git-cliff or release-please — pick git-cliff,
     simpler). Attaches: library.json, library.sqlite, KiCad libs zip
     (placeholder for now), CycloneDX HBOM, SHA256SUMS, signed.
   - Job 6 publish-docs: builds and deploys docs to GitHub Pages with `mike`
     so multiple versions coexist (mike deploy --push --update-aliases <tag>
     latest).

2. Create packages/hwlib-data/ for the data wheel:
   - pyproject.toml — name "hwlib-data", build-time hook copies ../../dist/
     into src/hwlib_data/data/. Pure-data wheel, no python code beyond a
     `data_path()` helper.

3. Create CHANGELOG.md (Keep-a-Changelog format) with an Unreleased section
   listing prompts 0–10 features.

4. Create cliff.toml for git-cliff config.

5. Author docs/agents/claude-code.md, cursor.md, cline.md showing exact wiring:

   docs/agents/claude-code.md content:
   ```
   ## Local stdio (recommended)
   `claude mcp add hwlib uvx hwlib-mcp`

   ## Pin to a release version
   `claude mcp add hwlib uvx --from hwlib-mcp==0.1.0 hwlib-mcp`

   ## Docker (HTTP)
   ```bash
   docker run -d -p 8080:8080 --name hwlib \
     ghcr.io/<your-github-username>/hwlib-mcp:latest --http --port 8080
   claude mcp add hwlib --transport http http://localhost:8080
   ```

   ## CLAUDE.md snippet to drop in your project
   <copy the block from blueprint section 7.2 verbatim>
   ```

   docs/agents/cursor.md: `.cursor/mcp.json` with hwlib-mcp stdio config and
   .cursor/rules/00-hwlib.mdc identical to CLAUDE.md.

   docs/agents/cline.md: `.clinerules/00-hwlib.md` and Cline MCP settings
   path on macOS/Linux/Windows.

6. Add a top-level INSTALL-OFFLINE.md describing how to consume the air-gap
   tarball: extract release tar, `pip install hwlib-mcp-*.whl hwlib-data-*.whl
   --no-index --find-links .`, point HWLIB_DATA_DIR at the extracted data.

Commit and tag v0.1.0 locally (don't push the tag until you've created the
GitHub repo, configured trusted publishing on PyPI, and wired branch
protection — but tagging locally lets us verify release.yml syntax via
`act` or `gh workflow view`).
```

**Verify:**
```bash
# Local syntax check:
gh workflow view release.yml || act -l
# Dry-run the data wheel build:
cd packages/hwlib-data && python -m build && ls dist/
```

---

## Prompt 11 — Final hardening pass

```text
One pass to catch anything sloppy from the speed-run.

1. Audit and fix:
   - Every public Python function has a one-line docstring.
   - Every Pydantic field has a description= (powers the JSON Schema
     description, which agents see).
   - Every CLI command has --help text that an agent can grep.
   - All test files have >80% coverage on tools/ packages (run `pytest
     --cov=tools --cov=pydantic_models --cov-report=term-missing`).

2. Add tests/test_e2e.py: end-to-end test that builds the bundle, starts the
   MCP server in-memory, simulates an agent calling search → get → check_pin_
   conflicts on the lorawan-node fixture, and asserts the round trip succeeds.

3. Add an `examples/` directory at repo root with:
   - examples/lorawan-node/ — the fixture as a real "starter project" with
     CLAUDE.md, .cursor/rules/, .clinerules/ pre-wired, plus a stub
     platformio.ini and main.c that the agent could complete. README explains
     "this is what an agent would scaffold."

4. Update top-level README.md with a "Quickstart for agents" section linking
   to docs/agents/ and showing the 3-line `claude mcp add` command.

5. Run the full local equivalent of CI:
   pre-commit run --all-files
   python -m tools.generate_schemas && git diff --exit-code schemas/
   python -m tools.validate all
   pytest -q --cov
   python -m tools.builder --out dist/
   (cd docs && mkdocs build --strict)
   docker build -t hwlib-mcp:dev packages/hwlib-mcp/

6. Open a self-PR (gh pr create) so we can see the full CI run.

Stop. Show me the coverage summary and any remaining TODOs.
```

**Verify:**
```bash
pytest --cov=tools --cov=pydantic_models --cov-report=term-missing
gh pr create --title "v0.1.0 hardening pass" --body "Final pre-release pass"
gh pr checks
```

---

## Post-MVP — what to add next (separate prompts, NOT in MVP)

These are deferred to keep the MVP focused. Each becomes its own future Claude Code prompt session:

- **Prompt A**: Implement `hwlib_suggest_pinmap` with a real solver (constraint propagation respecting strapping/mux/voltage/interrupt requirements).
- **Prompt B**: KiCad libs in-tree (`kicad/hw-registry.kicad_sym`, `.pretty`, `.3dshapes`) with KLC checks vendored from `kicad-library-utils`. Generator that populates KiCad symbol fields from YAML.
- **Prompt C**: BOM generators — JLCPCB strict CSV, IPC-2581, CycloneDX HBOM 1.7.
- **Prompt D**: ECN tracking module + revision changelog generator.
- **Prompt E**: Octopart/Nexar nightly cache job.
- **Prompt F**: Auto-generated SVG pinout diagrams via `tools/render_pinout.py`.
- **Prompt G**: `hwlib_generate_platformio_ini` and `hwlib_generate_sdkconfig` real implementations.
- **Prompt H**: Compatibility tier system + deprecation workflow + `hwlib_swap_component`.
- **Prompt I**: Real-world inventory backfill — your full list of tested components.

---

## Operational notes

**When a prompt fails partway through:** tell Claude Code "stop, revert uncommitted changes, and summarize what you did before failing." Then either (a) fix the precondition and re-run the same prompt, or (b) split the prompt into smaller pieces.

**When CI is red on the PR:** paste the failing job log to Claude Code and say "fix this CI failure on branch X." It will pull the branch, reproduce locally, fix, push.

**When you disagree with an authoring decision:** say "you chose X, I want Y because Z." Claude Code will revise and reason about downstream impact (which is its strength — it understands the whole repo by then).

**When you want to slow down:** insert "stop, do not make any more changes, just describe what you'd do next" between prompts. Use this liberally on prompts 4, 5, 6 — they have the most room for design drift.

**Branch strategy:** create a feature branch per prompt (`feat/p0-bootstrap`, `feat/p1-models`, …). Merge to `main` only after CI green on each. After Prompt 9, configure GitHub branch protection.

**Substitutions to make before pasting any prompt:**
- `<your-github-username>` — your GH handle
- `<your-email>` — the email in the `tested.by` field of seed components
- Optional: change `hw-registry` repo name if you prefer

Good luck. Ping me with the output of any failing CI job and we'll iterate.
