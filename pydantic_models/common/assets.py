"""Asset and datasheet models for binary/external content references."""

from pydantic import Field, HttpUrl

from .identifiable import Strict


class Asset(Strict):
    """Reference to a file living inside the repo (potentially under LFS)."""

    path: str = Field(description="Repo-relative path (e.g. assets/sensors/sht41/pinout.svg).")
    lfs: bool = Field(
        default=False,
        description="True if this asset is stored via Git LFS (binary > 500 KB).",
    )
    license: str = Field(
        description="SPDX identifier for this asset (e.g. CC-BY-4.0, MIT, vendor-redistribution).",
    )


class Datasheet(Strict):
    """Manufacturer datasheet pointer with archival fallback."""

    primary_url: HttpUrl = Field(description="Vendor-hosted authoritative URL.")
    archived_url: HttpUrl | None = Field(
        default=None,
        description="web.archive.org snapshot for offline / link-rot resilience.",
    )
    sha256: str | None = Field(
        default=None,
        description="SHA-256 of the PDF when archived locally; null if linking only.",
    )


class AssetBundle(Strict):
    """Aggregate of datasheet plus optional pinout and additional assets."""

    datasheet: Datasheet = Field(description="Primary datasheet reference.")
    pinout_svg: Asset | None = Field(
        default=None,
        description="Auto-generated SVG pinout (CC-BY-4.0). Populated by tools/render_pinout.py.",
    )
    additional: list[Asset] = Field(
        default_factory=list,
        description="Other linked assets (3D models, KiCad projects, application notes).",
    )
