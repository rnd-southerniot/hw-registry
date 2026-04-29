# Offline / air-gap installation

For environments without internet access (factory floors, disconnected lab benches, classified networks). Every release on [GitHub Releases](https://github.com/rnd-southerniot/hw-registry/releases) ships the artifacts you need to install `hwlib-mcp` + `hwlib-data` without `pip install` reaching out to PyPI.

## What's in a release tarball

Each release attaches the following:

| File | Purpose |
|---|---|
| `hwlib_mcp-X.Y.Z-py3-none-any.whl` | MCP server wheel |
| `hwlib_mcp-X.Y.Z.tar.gz` | MCP server sdist |
| `hwlib_data-X.Y.Z-py3-none-any.whl` | Data wheel (catalog SQLite + JSON) |
| `hwlib_data-X.Y.Z.tar.gz` | Data sdist |
| `library.json` | Resolved catalog (JSON) |
| `library.sqlite` | Resolved catalog (SQLite, FTS5-indexed) |
| `index.json` | Catalog summary (counts, build provenance) |
| `SHA256SUMS` | Checksum manifest covering all of the above |

## Steps

```bash
# 1. On a connected machine, download the release tarball.
gh release download v0.1.0 \
    --repo rnd-southerniot/hw-registry \
    --pattern '*' \
    --dir hwlib-v0.1.0/
# Or grab the .zip from the GitHub Release page.

# 2. Transfer hwlib-v0.1.0/ to the air-gapped machine (USB, sneakernet, etc).

# 3. On the air-gapped machine, verify checksums.
cd hwlib-v0.1.0/
sha256sum -c SHA256SUMS
# All files should report `OK`. Anything else, halt.

# 4. Install both wheels with --no-index so pip doesn't reach out.
pip install --no-index --find-links . \
    hwlib_mcp-0.1.0-py3-none-any.whl \
    hwlib_data-0.1.0-py3-none-any.whl

# 5. Smoke test.
hwlib-mcp --help     # argparse help; confirms the binary resolves
python -c 'from hwlib_data import data_path; print(data_path())'
# Should print a real path under your Python's site-packages.

# 6. Wire your agent (see docs/agents/).
```

## Why both `library.sqlite` and the data wheel?

Most consumers should just install the wheel — `pip install hwlib_data-0.1.0-py3-none-any.whl --no-index --find-links .` and use `from hwlib_data import data_path`. That's the supported path.

The standalone `library.sqlite` and `library.json` files are convenient for tooling that doesn't speak Python (KiCad scripts in BASIC, BOM exporters written in Go, etc.) — they're byte-identical to what's inside the wheel, so you can hash-compare to verify provenance.

## Air-gap caveats

- **The Docker image isn't on the release.** Pulling `ghcr.io/rnd-southerniot/hwlib-mcp:latest` requires network access. For air-gap Docker deployments, `docker save ghcr.io/rnd-southerniot/hwlib-mcp:v0.1.0 -o hwlib-mcp-v0.1.0.tar` on a connected machine, transfer, then `docker load -i hwlib-mcp-v0.1.0.tar` on the air-gap.
- **PyPI dependencies aren't bundled.** `hwlib-mcp`'s transitive deps (FastMCP, anyio, etc.) need to be downloaded too. `pip download hwlib-mcp -d offline-deps/` on a connected machine pulls them all; transfer that directory and use `pip install --no-index --find-links offline-deps/`.
- **SLSA attestations live with the GitHub Release.** Verifying provenance offline is possible (Sigstore bundles ship as separate files alongside the wheels) but requires the `sigstore` CLI installed offline as well.

## Updating an air-gap install

The release artifact set is self-contained per version. To upgrade, repeat the process with the new release's tarball and `pip install --upgrade --no-index --find-links .`.

For incremental data-only updates without a server bump, you can install just the new `hwlib_data` wheel — `hwlib-mcp` will pick up the bundle through its normal `hwlib_data.data_path()` fallback, no server restart needed beyond reloading the agent's MCP connection.
