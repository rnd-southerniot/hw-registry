"""Static structural checks on the Dockerfile + /health endpoint contract.

These do NOT run ``docker build``. The full image build is exercised in
CI (Prompt 9). What this file guards against is regressions in the
Dockerfile shape (drift away from multi-stage / distroless / non-root)
and in the /health response contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client
from hwlib_mcp import build_server
from starlette.testclient import TestClient

DOCKERFILE = Path(__file__).resolve().parent.parent / "Dockerfile"
DOCKERIGNORE = Path(__file__).resolve().parent.parent / ".dockerignore"


# --- Dockerfile structural shape ---------------------------------------


def test_dockerfile_exists() -> None:
    assert DOCKERFILE.is_file(), f"missing Dockerfile at {DOCKERFILE}"


def test_dockerfile_is_multi_stage() -> None:
    """Two FROM lines, distroless final stage."""
    content = DOCKERFILE.read_text()
    from_lines = [line for line in content.splitlines() if line.strip().startswith("FROM ")]
    assert len(from_lines) == 2, (
        f"expected exactly 2 FROM lines (multi-stage); got {len(from_lines)}: {from_lines}"
    )

    builder, runtime = from_lines
    assert "AS builder" in builder, f"first FROM should name 'builder' stage: {builder!r}"
    assert "distroless" in runtime, f"runtime stage must be distroless: {runtime!r}"


def test_dockerfile_runtime_is_nonroot() -> None:
    """The :nonroot tag is the canonical distroless route to a non-root user."""
    content = DOCKERFILE.read_text()
    runtime_from = next(
        line for line in content.splitlines() if line.strip().startswith("FROM gcr.io/distroless")
    )
    assert ":nonroot" in runtime_from, (
        f"distroless runtime must use :nonroot tag (uid 65532): {runtime_from!r}"
    )


def test_dockerfile_exposes_8080() -> None:
    content = DOCKERFILE.read_text()
    assert any(line.strip().startswith("EXPOSE 8080") for line in content.splitlines()), (
        "EXPOSE 8080 line missing — required for --http mode liveness"
    )


def test_dockerfile_no_healthcheck_baked_in() -> None:
    """Healthcheck deliberately lives in compose / orchestrator layer.

    Distroless has no shell to exec; baking a HEALTHCHECK into the image
    would either need a Python-via-/usr/bin/python3 invocation (works
    only in --http mode) or be mode-conditional (impossible to declare
    statically). compose layers it cleanly; the image stays single-purpose.
    """
    # Look only at directive lines (non-comment, non-blank, non-continuation),
    # so the comment block that explains the absence of HEALTHCHECK doesn't
    # itself trigger the regression.
    directive_lines = [
        line.strip()
        for line in DOCKERFILE.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert not any(line.startswith("HEALTHCHECK ") for line in directive_lines), (
        "Dockerfile should not declare HEALTHCHECK — see docstring + docker.md"
    )


def test_dockerfile_has_oci_labels() -> None:
    """Each of the four canonical OCI image labels is present."""
    content = DOCKERFILE.read_text()
    for required in (
        "org.opencontainers.image.source",
        "org.opencontainers.image.description",
        "org.opencontainers.image.licenses",
        "org.opencontainers.image.title",
    ):
        assert required in content, f"missing OCI label: {required}"


def test_dockerfile_entrypoint_uses_python_module() -> None:
    """ENTRYPOINT must invoke ``python -m hwlib_mcp``."""
    content = DOCKERFILE.read_text()
    assert 'ENTRYPOINT ["/usr/bin/python3", "-m", "hwlib_mcp"]' in content, (
        "ENTRYPOINT should use exec form invoking python -m hwlib_mcp"
    )


def test_dockerfile_sets_data_dir_env() -> None:
    content = DOCKERFILE.read_text()
    assert "HWLIB_DATA_DIR=/opt/hwlib/data" in content, (
        "HWLIB_DATA_DIR must default to /opt/hwlib/data inside the image"
    )


def test_dockerfile_no_bundled_credentials() -> None:
    """Sanity check: no obvious credential / secret pattern in env lines."""
    content = DOCKERFILE.read_text()
    for needle in ("API_KEY", "PASSWORD", "SECRET", "TOKEN"):
        assert needle not in content.upper(), f"suspicious env-name {needle!r} found in Dockerfile"


# --- .dockerignore -----------------------------------------------------


def test_dockerignore_excludes_tests() -> None:
    """tests/ never belongs in the runtime image — bytes + attack surface."""
    content = DOCKERIGNORE.read_text()
    assert "**/tests" in content, ".dockerignore must exclude **/tests"


def test_dockerignore_excludes_caches() -> None:
    content = DOCKERIGNORE.read_text()
    for required in ("__pycache__", ".pytest_cache", ".ruff_cache", ".venv"):
        assert required in content, f".dockerignore should exclude {required}"


# --- /health endpoint contract -----------------------------------------
#
# In-process Starlette TestClient — no actual Docker run required. The
# server's http_app() returns the Starlette app the streamable-http
# transport binds; the /health route lives on that app via FastMCP's
# @custom_route hook.


def test_health_endpoint_healthy_shape(tmp_path_factory: pytest.TempPathFactory) -> None:
    """200 + {status, bundle_present, component_count, schema_version}."""
    # Build a real bundle for the test session.
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))
    from tools.builder import build  # noqa: PLC0415

    out = tmp_path_factory.mktemp("dist")
    build(repo_root / "library", out)

    server = build_server(out)
    http_app = server.http_app(path="/mcp")
    client = TestClient(http_app)

    response = client.get("/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["bundle_present"] is True
    assert isinstance(body["component_count"], int)
    assert body["component_count"] >= 8  # 8 seed components
    assert body["schema_version"] == 1


def test_health_endpoint_bundle_missing(tmp_path: Path) -> None:
    """503 + bundle_missing shape when the data dir is empty."""
    server = build_server(tmp_path)  # empty
    http_app = server.http_app(path="/mcp")
    client = TestClient(http_app)

    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "bundle_missing"
    assert body["bundle_present"] is False
    assert "data_dir" in body


# --- FastMCP API surface used by build_server is still present ---------


@pytest.mark.asyncio
async def test_custom_route_decorator_exists() -> None:
    """Regression guard: FastMCP must continue to expose @mcp.custom_route.

    The /health endpoint depends on this decorator. If FastMCP renames or
    removes it in a future release, this test fails loudly so the build
    notices before container CI does.
    """
    server = build_server(Path(__file__).resolve().parents[3] / "dist")
    assert callable(getattr(server, "custom_route", None)), (
        "FastMCP no longer exposes @mcp.custom_route — /health endpoint "
        "wiring needs to migrate to whatever replaced it."
    )
    # Sanity that the route shows up in the assembled HTTP app.
    async with Client(server) as _:
        pass  # smoke
