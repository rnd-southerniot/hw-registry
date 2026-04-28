# syntax=docker/dockerfile:1.7
#
# hwlib-mcp container image.
#
# Build context MUST be the repo root (so the COPY of dist/ resolves).
# From the repo root:
#
#     docker build -t hwlib-mcp:dev -f packages/hwlib-mcp/Dockerfile .
#
# Multi-stage:
#   builder  — python:3.12-slim with uv; installs hwlib-mcp into a
#              standalone /opt/site-packages directory and copies the
#              built bundle into /opt/hwlib/data/.
#   runtime  — gcr.io/distroless/python3-debian12:nonroot; copies the
#              two prepared directories. No shell, no package manager,
#              no apt — single-purpose runtime. Debugging happens at
#              the host level (`docker logs`) or via the MCP protocol
#              itself, NOT by `docker exec`.

# ----- Stage 1: builder ------------------------------------------------
# Builder ABI MUST equal runtime ABI for C-extension wheels (pydantic_core,
# watchfiles). Pinned to 3.13 to match Stage 2 — see Stage 2 comment for the
# version-choice rationale.

FROM python:3.13-slim AS builder

# Pin uv via official image so build is reproducible without a network
# install step inside this stage.
COPY --from=ghcr.io/astral-sh/uv:0.5.30 /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /build

# Copy the package metadata + sources. README is referenced by pyproject.
COPY packages/hwlib-mcp/pyproject.toml \
     packages/hwlib-mcp/README.md \
     ./packages/hwlib-mcp/
COPY packages/hwlib-mcp/src ./packages/hwlib-mcp/src

# Install hwlib-mcp + its dependencies into a target directory we can
# copy across stages. --target avoids the venv-shebang path-mismatch
# headache (builder's /usr/local/bin/python ≠ distroless's
# /usr/bin/python3.12); a flat site-packages directory works regardless.
RUN uv pip install --system --target /opt/site-packages ./packages/hwlib-mcp

# The bundle is mandatory at image build time. The Dockerfile does NOT
# auto-build — `bash packages/hwlib-mcp/scripts/build-image.sh` does
# that step before invoking `docker build`. Failing here on a missing
# dist/ is the right error: tells the operator the build script wasn't
# used.
COPY dist/library.json    /opt/hwlib/data/library.json
COPY dist/library.sqlite  /opt/hwlib/data/library.sqlite
COPY dist/index.json      /opt/hwlib/data/index.json

# ----- Stage 2: runtime ------------------------------------------------
# Distroless Debian 13 (Python 3.13) matches requires-python = ">=3.13".
# dev=prod=3.13 is load-bearing for C-extension ABI compatibility.
#
# Why not 3.12: no free distroless ships Python 3.12 as of 2026-Q1.
#   gcr.io/distroless/python3-debian12 → 3.11   (ABI mismatch with 3.13 builder)
#   gcr.io/distroless/python3-debian13 → 3.13   ← chosen
#   cgr.dev/chainguard/python:3.12     → paywalled (Chainguard Containers)
#   cgr.dev/chainguard/python:latest   → 3.14

FROM gcr.io/distroless/python3-debian13:nonroot

LABEL org.opencontainers.image.source="https://github.com/rnd-southerniot/hw-registry"
LABEL org.opencontainers.image.description="MCP server exposing the hw-registry hardware catalog to AI agents"
LABEL org.opencontainers.image.licenses="MIT AND CC-BY-4.0"
LABEL org.opencontainers.image.title="hwlib-mcp"
LABEL org.opencontainers.image.vendor="Southern IoT Limited"

COPY --from=builder /opt/site-packages /opt/site-packages
COPY --from=builder /opt/hwlib/data    /opt/hwlib/data

# Distroless's nonroot user (uid 65532) is set automatically by the
# `:nonroot` tag — no need for an explicit USER line.

ENV HWLIB_DATA_DIR=/opt/hwlib/data \
    PYTHONPATH=/opt/site-packages \
    PYTHONUNBUFFERED=1

# Only meaningful in --http mode; stdio invocations ignore the port.
EXPOSE 8080

# Distroless image's default entrypoint is /usr/bin/python3 — override
# explicitly to be precise about which Python we invoke and to add the
# -m argument.
ENTRYPOINT ["/usr/bin/python3", "-m", "hwlib_mcp"]

# Default to stdio (no args). Override at runtime for HTTP mode:
#   docker run --rm -p 8080:8080 hwlib-mcp:dev --http --port 8080
# CMD intentionally empty — hwlib_mcp's argparse defaults handle stdio.

# HEALTHCHECK is intentionally not declared in this Dockerfile.
# - In stdio mode the server has no HTTP surface to probe.
# - In --http mode the orchestrator (or compose) is the right place to
#   declare the probe; the server exposes GET /health returning the
#   contract shape {status, bundle_present, component_count,
#   schema_version} — see docs/agents/docker.md.
