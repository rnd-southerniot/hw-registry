# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

The first labeled release will be `v0.1.0`. Pre-release development cycle covered Prompts 0–10 from the bootstrap pack and is described below for context.

### Added — bootstrap milestones

- **Pydantic models** for the six component kinds (board, module, chip, sensor, driver, connector). Canonical structural surfaces backing the YAML catalog under `library/`.
- **JSON-Schema generator** (`tools.generate_schemas`) producing `schemas/<kind>.schema.json` from the Pydantic models, kept in lockstep via a pre-commit hook (`check-schemas-synced`).
- **Deterministic bundle builder** (`tools.builder`) producing `library.json`, `library.sqlite`, `index.json` from `library/**/*.yaml` with `SOURCE_DATE_EPOCH` honored.
- **Pin-conflict graph validator** (`tools.conflicts`) for system-wide pinmap reasoning across composed components.
- **MCP server `hwlib-mcp`** (FastMCP-based) exposing six tools to AI coding agents, with a `/health` endpoint for HTTP-mode orchestrator probes.
- **Distroless container image** for the MCP server, on `gcr.io/distroless/python3-debian13:nonroot` (Python 3.13 throughout); operator-verified runtime checks against the bundle-missing fast-fail and `/health` contract.
- **MkDocs Material doc site** at `https://rnd-southerniot.github.io/hw-registry/` with auto-generated per-component pages (per-kind renderers) and a search-indexed catalog.
- **Data wheel `hwlib-data`** bundling the deterministic catalog as a PyPI package, consumed by `hwlib-mcp` as the default fallback when `HWLIB_DATA_DIR` isn't set.
- **GitHub Actions CI** with 9 required status checks, branch protection on `main` (linear history, code-owner reviews, dismiss-stale-reviews), and a versioned doc deploy via `mike`.
- **Release workflow** publishing to PyPI (trusted publishing), GHCR (with SLSA provenance + CycloneDX SBOM), the versioned doc site, and a GitHub Release with SHA256SUMS.

### Documentation

- `docs/agents/{claude-code,cursor,cline,docker}.md` — onboarding guides per AI coding agent.
- `INSTALL-OFFLINE.md` — air-gapped deployment from the GitHub Release tarball.
- `docs/internal/BLUEPRINT.md` — architectural reasoning and reconciliation notes (committed to the repo, excluded from the published doc site).
- `docs/internal/CLAUDE_CODE_PROMPTS.md` — the prompt pack used to bootstrap the repo.

### Security

- `gitleaks` runs in pre-commit AND in CI's `secret-scan` job (binary, no organization license required).
- All published artifacts (wheels + Docker images) carry SLSA build-provenance attestations via Sigstore.
- Branch protection enforces 1 CODEOWNERS approval + 9 required status checks before merge to `main`.

[Unreleased]: https://github.com/rnd-southerniot/hw-registry/compare/main...HEAD
