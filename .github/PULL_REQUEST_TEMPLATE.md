<!--
Thanks for contributing to hw-registry. Fill in the checklists below; delete
the sections that don't apply to your PR.
-->

## Summary

<!-- One-line summary of the change. Conventional Commits subject if applicable. -->

## Component metadata (delete if PR isn't a component change)

- [ ] Component category (`board` / `module` / `sensor` / `driver` / `chip` / `connector`)
- [ ] Tier declared in `tested.status` (`stub` / `verified` / `production-tested`)
- [ ] `tested.status` accurately reflects POC reality (no `production-tested` without a deployment)
- [ ] Datasheet linked (`assets.datasheet.primary_url`) + archived (`archived_url` via web.archive.org)
- [ ] Pin map verified against datasheet
- [ ] No copyrighted images / PDFs embedded — links only
- [ ] KiCad symbol matches MPN exactly (or marked TODO for post-MVP)

## Local checks

- [ ] `pre-commit run --all-files` passes locally (full tree, not just staged files)
- [ ] `python -m tools.builder --out dist/` succeeds
- [ ] `pytest -q` passes (root)
- [ ] `cd packages/hwlib-mcp && pytest -q` passes (mcp)

## POC evidence

<!--
Required for `tested.status: production-tested`; optional otherwise.
Free text — repo URL, photo path, log capture, deployment context.
-->
