"""Integration test: docs site builds with --strict and renders the contract."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


pytest.importorskip(
    "mkdocs",
    reason="mkdocs not installed (run `make docs-deps` to enable docs build tests)",
)


@pytest.fixture(scope="module")
def built_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the site once into a tempdir; reuse across the tests in this file."""
    if not (REPO_ROOT / "dist" / "library.json").exists():
        subprocess.run(
            ["python", "-m", "tools.builder", "--out", str(REPO_ROOT / "dist")],
            cwd=REPO_ROOT,
            check=True,
        )
    out_dir = tmp_path_factory.mktemp("site")
    mkdocs = shutil.which("mkdocs")
    assert mkdocs, "mkdocs must be on PATH"
    subprocess.run(
        [mkdocs, "build", "--strict", "--site-dir", str(out_dir)],
        cwd=REPO_ROOT,
        check=True,
    )
    return out_dir


@pytest.mark.docs
def test_index_page_exists(built_site: Path) -> None:
    assert (built_site / "index.html").exists()


@pytest.mark.docs
def test_sht41_sensor_page_exists(built_site: Path) -> None:
    page = built_site / "components" / "sensors" / "sensirion" / "sht41" / "index.html"
    assert page.exists()
    body = page.read_text()
    # Spot-check that the nested constraints structure renders
    assert "0x44" in body, "I²C address didn't render"
    assert "Constraints" in body
    assert "Pull-ups" in body or "pull-ups" in body
    assert "Operating temperature" in body


@pytest.mark.docs
def test_board_page_pin_table(built_site: Path) -> None:
    page = built_site / "components" / "boards" / "espressif" / "esp32-s3-devkitc-1" / "index.html"
    assert page.exists()
    body = page.read_text()
    assert "Pinout" in body
    # alt_functions joined readably (NOT a Python repr)
    assert "<object" not in body
    assert "AltFunction" not in body


@pytest.mark.docs
def test_internal_docs_excluded(built_site: Path) -> None:
    """BLUEPRINT.md and CLAUDE_CODE_PROMPTS.md must NOT render as published pages.

    (The word ``BLUEPRINT`` may legitimately appear in prose — e.g. on the
    architecture page where the internal blueprint is referenced — but no
    actual page should be rendered from those internal sources.)
    """
    for forbidden_path in (
        built_site / "internal",
        built_site / "BLUEPRINT",
        built_site / "CLAUDE_CODE_PROMPTS",
    ):
        assert not forbidden_path.exists(), f"unexpected: {forbidden_path}"

    forbidden_filenames = ("BLUEPRINT", "CLAUDE_CODE_PROMPTS")
    for path in built_site.rglob("*"):
        if not path.is_file():
            continue
        for needle in forbidden_filenames:
            assert needle not in path.name, (
                f"file with forbidden name leaked: {path.relative_to(built_site)}"
            )


@pytest.mark.docs
def test_components_index_lists_kinds(built_site: Path) -> None:
    page = built_site / "components" / "index.html"
    assert page.exists()
    body = page.read_text()
    for label in ("Boards", "Modules", "Chips", "Sensors", "Drivers"):
        assert label in body, f"{label!r} missing from components index"
