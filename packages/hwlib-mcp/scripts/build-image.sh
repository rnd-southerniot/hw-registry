#!/usr/bin/env bash
#
# Build the hwlib-mcp container image.
#
# Builds the bundle first (the Dockerfile copies dist/ during stage 1),
# then runs `docker build` with the repo root as the build context.
# Tags with both the package version from pyproject.toml and `dev`.
#
# Usage (from anywhere):
#     bash packages/hwlib-mcp/scripts/build-image.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PACKAGE_DIR="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${PACKAGE_DIR}/../.." >/dev/null 2>&1 && pwd)"

cd "${REPO_ROOT}"

echo "==> Building bundle (dist/) before docker build…"
if [[ ! -d .venv ]]; then
    echo "    error: .venv missing — run 'make install' first." >&2
    exit 2
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m tools.builder --out dist/

# Read version from pyproject.toml (no toml parser assumed; grep + sed).
VERSION="$(
    grep -E '^version = ' "${PACKAGE_DIR}/pyproject.toml" \
        | head -n1 \
        | sed -E 's/version = "(.*)"/\1/'
)"
if [[ -z "${VERSION}" ]]; then
    echo "    error: could not parse version from pyproject.toml." >&2
    exit 2
fi

IMAGE="hwlib-mcp"
TAG_DEV="${IMAGE}:dev"
TAG_VERSION="${IMAGE}:${VERSION}"

echo "==> Building ${TAG_DEV} (also tagged ${TAG_VERSION})…"
docker build \
    -f "${PACKAGE_DIR}/Dockerfile" \
    -t "${TAG_DEV}" \
    -t "${TAG_VERSION}" \
    "${REPO_ROOT}"

echo "==> Image size:"
docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}' \
    | grep -E "^${IMAGE}:(dev|${VERSION})\b" || true

echo "==> Done. Tags: ${TAG_DEV}, ${TAG_VERSION}"
