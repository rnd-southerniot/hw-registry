# CLAUDE.md — `hw-registry`

Execution contract for any AI agent (Claude Code, Cursor, Cline, …) or human
contributor working in this repo. Project-level rules; the operator's global
rules still apply on top.

---

## 1. Mission

`hw-registry` is the **single source of truth for our team's embedded hardware
library** — boards, modules, chips, sensors, drivers, connectors. Every entry
is curated and battle-tested. The library is consumed by:

- **Humans** browsing the doc site (MkDocs Material, auto-generated per
  component).
- **AI coding agents** via the MCP server (`hwlib-mcp`, distributed on PyPI
  and `ghcr.io`).
- **KiCad / PCB tooling** consuming symbol/footprint/3D refs.
- **BOM exporters** (JLCPCB, IPC-2581, CycloneDX HBOM).

Curation > coverage. A small library of components we have actually built,
flashed, and shipped beats a large library of speculative entries.

---

## 2. Source-of-truth rule

```
YAML files under  library/             ← CANONICAL. Edit these.
Pydantic models   pydantic_models/     ← CANONICAL. Edit these.
JSON Schemas      schemas/             ← GENERATED. Never hand-edit.
Built bundle      dist/                ← GENERATED. Never commit by hand.
```

Schemas are produced by `python -m tools.generate_schemas` from the Pydantic
models. CI fails the PR if `schemas/` drifts from the models.

---

## 3. Naming rule (slug == path)

A component's `id` field **must equal its relative path under `library/`**,
minus the `.yaml` extension. Examples:

| File path                                            | `id` field                          |
|------------------------------------------------------|-------------------------------------|
| `library/sensors/sensirion/sht41.yaml`               | `sensors/sensirion/sht41`           |
| `library/boards/espressif/esp32-s3-devkitc-1.yaml`   | `boards/espressif/esp32-s3-devkitc-1` |
| `library/modules/rakwireless/rak3172.yaml`           | `modules/rakwireless/rak3172`       |

The slug regex enforced in the model is `^[a-z]+/[a-z0-9-]+/[a-z0-9-]+$`
(kind / vendor / part). `tools.validate slug-equals-path` enforces this in
pre-commit and CI.

---

## 4. Vendor slugs

Vendor segment of the path comes from **Zephyr's `vendor-prefixes.txt`**
(lowercase, hyphenated). When a vendor is missing from that list, add it to
the registry with a short justification in the PR description — do not
silently invent slugs.

Reference: <https://github.com/zephyrproject-rtos/zephyr/blob/main/dts/bindings/vendor-prefixes.txt>

---

## 5. Forbidden

- **No hard-coded secrets.** No tokens, API keys, MQTT passwords, wifi PSKs,
  cloud creds — anywhere. Not in code, not in YAML, not in docs, not in test
  fixtures, not in commit messages, not in remote URLs. `gitleaks` runs in
  pre-commit and CI.
- **No full datasheets in the repo.** Link to the manufacturer URL and an
  `archived_url` (web.archive.org). Quote ≤ 15 words from any source. Never
  copy a table or figure.
- **No vendor pinout / package images.** Link only. Generated SVG pinouts
  (produced from our own YAML) are fine.
- **No `:latest` tags** in any committed compose file destined for
  production.
- **No `curl | bash`** install instructions for tools the project depends on.

---

## 6. SemVer for components

Each component carries a `revision: MAJOR.MINOR.PATCH`:

| Bump  | Trigger                                                                  |
|-------|--------------------------------------------------------------------------|
| MAJOR | Pin assignment or electrical incompatibility with prior revision         |
| MINOR | Behavior or feature change that is backward-compatible electrically      |
| PATCH | Errata, silkscreen, datasheet links, doc fixes — no functional change    |

Consumers may pin against `@MAJOR.MINOR`; bumping MAJOR is a breaking change
event for every downstream system YAML.

---

## 7. Commit hygiene

- **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `refactor:`, `test:`).
- Scope optional but encouraged: `feat(sensors): add sht41 v1.0.0`.
- One logical change per commit. Don't bundle a model change with a YAML change with a CI tweak.
- Never force-push `main`. Feature branches: `--force-with-lease` only.
- Always run `pre-commit run --all-files` **before** `git commit` once
  pre-commit is installed (Prompt 2 wires it in).

---

## 8. Phase gates

This repo is bootstrapped by a phase-gated prompt pack
(`CLAUDE_CODE_PROMPTS.md`). Each phase produces one or more commits and ends
with a green smoke test. Do not advance to the next phase without a green
gate. Do not skip steps to "save time."

---

## 9. Layout (target — populated phase by phase)

```
hw-registry/
├── CLAUDE.md              # this file
├── README.md
├── LICENSE                # MIT AND CC-BY-4.0
├── pyproject.toml         # dev tooling (Prompt 1)
├── pydantic_models/       # canonical models (Prompt 1)
├── schemas/               # GENERATED JSON Schemas (Prompt 1)
├── library/               # canonical YAML components (Prompt 3+)
│   ├── boards/<vendor>/<part>.yaml
│   ├── modules/<vendor>/<part>.yaml
│   ├── chips/<vendor>/<part>.yaml
│   ├── sensors/<vendor>/<part>.yaml
│   ├── drivers/<vendor>/<part>.yaml
│   └── connectors/<vendor>/<part>.yaml
├── tools/                 # generators, validators, builder, conflict checker
├── packages/
│   ├── hwlib-mcp/         # MCP server, PyPI + Docker
│   └── hwlib-data/        # data wheel bundling dist/library.{json,sqlite}
├── docs/                  # MkDocs Material site
├── tests/
├── examples/
└── .github/workflows/
```

---

## 10. When in doubt

1. Read this file.
2. Read `CLAUDE_CODE_PROMPTS.md` (the prompt pack that bootstrapped the repo).
3. Read the relevant Pydantic model — fields carry `description=` strings.
4. Ask the operator a single focused question. Do not invent values.
