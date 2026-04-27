# Running `hwlib-mcp` in a Docker container

Use the container when you want to:

- Host the MCP server for a team (Streamable HTTP transport, one server,
  many agent clients across a network).
- Pin to an exact bundle snapshot in a CI job that consumes the catalog.
- Distribute the catalog into an air-gap environment as a single image
  artifact (Prompt 10 wires the GHCR push).

For local solo use, prefer `uvx hwlib-mcp` over a container — Docker
adds latency and an extra layer with no upside when stdio works.

## Quickstart

```bash
# 1. Build the bundle and the image (one shot).
bash packages/hwlib-mcp/scripts/build-image.sh

# 2. Bring up the service in --http mode with the bundle mounted.
make compose-up

# 3. Probe.
curl -s http://localhost:8080/health | jq
# {"status":"ok","bundle_present":true,"component_count":8,"schema_version":1}

# 4. Wire an agent.
claude mcp add hwlib --transport http http://localhost:8080/mcp

# 5. Tear down.
make compose-down
```

## Pulling from GHCR

(Available after Prompt 10's release-wiring lands.)

```bash
docker pull ghcr.io/rnd-southerniot/hwlib-mcp:latest
docker run -d --name hwlib \
    -e HWLIB_DATA_DIR=/opt/hwlib/data \
    -p 8080:8080 \
    ghcr.io/rnd-southerniot/hwlib-mcp:latest \
    --http --port 8080
```

The image bakes in a frozen copy of the bundle that matches the image
tag (a v0.1.0 image carries the v0.1.0 bundle). Override at runtime by
mounting your own:

```bash
docker run -d \
    -v /path/to/your/dist:/opt/hwlib/data:ro \
    -p 8080:8080 \
    ghcr.io/rnd-southerniot/hwlib-mcp:latest \
    --http --port 8080
```

## Image structure

Multi-stage build:

| Stage   | Base image                           | Purpose                                   |
|---------|--------------------------------------|-------------------------------------------|
| builder | `python:3.12-slim` + `uv`            | Install package + deps into `/opt/site-packages`; copy `dist/` into `/opt/hwlib/data/` |
| runtime | `gcr.io/distroless/python3-debian12:nonroot` | Copies the two prepared dirs; runs as `nonroot` (uid 65532); no shell, no apt |

The runtime stage is **distroless** by design. There is no shell, no
package manager, no `bash`, no `sh`, no `apt`. `docker exec -it
hwlib-mcp sh` will fail. This is correct for a single-purpose runtime —
the smaller attack surface is worth more than ergonomic shell access.

## Debugging

You cannot `docker exec` into the container. The two debugging surfaces:

```bash
# 1. Container stdout/stderr — hwlib-mcp logs go to stderr.
docker logs hwlib-mcp -f

# 2. The MCP protocol itself, via FastMCP's introspection or the
#    /health endpoint in --http mode.
curl -s http://localhost:8080/health | jq
```

To enable verbose server logs (per-tool-call timings and decisions),
override the command:

```bash
docker run --rm \
    -e HWLIB_DATA_DIR=/opt/hwlib/data \
    -v $(pwd)/dist:/opt/hwlib/data:ro \
    -p 8080:8080 \
    hwlib-mcp:dev \
    --http --port 8080 --log-level debug
```

## Bundle-missing behaviour

Starting the container without a bundle exits non-zero quickly with a
structured error message on stderr, *not* a hang on stdio:

```bash
docker run --rm hwlib-mcp:dev
# Container exits with code 2; logs:
#   hwlib-mcp: library.sqlite not found at /opt/hwlib/data.
#     Run `python -m tools.builder --out dist/` and/or set
#     HWLIB_DATA_DIR to a directory that contains library.sqlite.
```

The image bakes in a bundle at build time, so this only fires when the
mount overrides it with an empty volume — which is itself a useful
sanity check during deployment.

## Health endpoint

`GET /health` (HTTP-only, **outside the MCP protocol surface**) returns:

| HTTP | Body shape                                                                   |
|------|------------------------------------------------------------------------------|
| 200  | `{"status": "ok", "bundle_present": true, "component_count": <int>, "schema_version": <int>}` |
| 503  | `{"status": "bundle_missing", "bundle_present": false, "data_dir": "<path>"}` |

Compose's healthcheck uses this via `urllib.request.urlopen` (no shell
required). Orchestrators (Kubernetes, Nomad, ECS) should configure a
liveness probe against the same endpoint.
