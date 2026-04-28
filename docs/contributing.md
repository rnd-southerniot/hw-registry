# Contributing

## Adding a component

1. Fork the repo and create a feature branch (`feat/<slug>` is the convention).
2. Author the YAML at `library/<kind>/<vendor>/<part>.yaml`. The slug *equals the path*: a sensor at `library/sensors/sensirion/sht41.yaml` has `id: sensors/sensirion/sht41`.
3. Run `pre-commit run --all-files` locally before committing — the hooks validate YAML against the JSON Schema, enforce slug-equals-path, and scan for secrets.
4. Open a PR against `main`. CI runs the same checks as pre-commit, plus the full bundle build and the conflict checker.

## Required fields

Every component carries `id`, `kind`, `vendor`, `revision`, `lifecycle`, `summary`, and `tested`. The structure for each kind lives in [`pydantic_models/`](https://github.com/rnd-southerniot/hw-registry/tree/main/pydantic_models) — those models are canonical for *structure* (what fields exist, what types they have).

The `tested` block must include:

- `status` — one of `stub`, `verified`, `production-tested`
- `by` — engineer email or GitHub handle
- `date` — ISO-8601
- `evidence` — short prose stating *where* the component has been deployed

## Curation gates

`production-tested` is reserved for components that have shipped on at least one production system in the field. State the deployment in `evidence`, e.g. *"Field-deployed in LoRaWAN T/RH nodes since 2025-Q4."* — vague claims like "tested in lab" don't qualify.

`verified` covers bench validation: the part has been reflowed, brought up, and exercised against the datasheet. Less than `production-tested` but more than `stub`.

`stub` is for skeleton entries that exist only to satisfy `inherits_from` or `contains.ref` resolution — they carry no functional claim.

## KiCad symbols

Use placeholder strings of the form `hw-registry:<MPN>` for the `symbol`, `footprint`, and (optionally) `model_3d` fields. Real `.kicad_sym` libraries land in a future milestone — these placeholders ensure the schema accepts the values today and the consuming tooling won't have to be re-plumbed when the real libraries arrive.

## Forbidden

- **No secrets** in YAML, code, commit messages, remote URLs, or test fixtures. `gitleaks` runs in pre-commit and CI.
- **No copy-pasted datasheets.** Link to the manufacturer URL plus a `web.archive.org` archive URL (`primary_url` and `archived_url`). Quoting more than ~15 words from any source is forbidden; never copy a table or figure.
- **No vendor pinout images** committed to the repo. Generated SVG pinouts (from our own YAML) will be added in a future milestone.

For the full set of project conventions see [`CLAUDE.md`](https://github.com/rnd-southerniot/hw-registry/blob/main/CLAUDE.md) at the repo root.
