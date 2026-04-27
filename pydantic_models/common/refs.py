"""KiCad and external (distributor / catalog) reference models."""

from pydantic import Field, HttpUrl

from .identifiable import Strict


class KicadRefs(Strict):
    """KiCad symbol, footprint, and 3D model pointers."""

    symbol: str = Field(description="Library:symbol path (e.g. hw-registry:SHT41).")
    footprint: str = Field(description="Library:footprint path (e.g. hw-registry:DFN-4-1EP_2x2mm).")
    model_3d: str | None = Field(
        default=None,
        description="3D model path relative to repo root (typically under LFS).",
    )


class ExternalRefs(Strict):
    """Distributor, catalog, and SBOM cross-references."""

    cpe: str | None = Field(
        default=None,
        description="CPE 2.3 identifier (e.g. 'cpe:2.3:h:sensirion:sht41:-:*:*:*:*:*:*:*'). SBOM-grade.",  # noqa: E501
    )
    purl: str | None = Field(
        default=None,
        description="Package URL (purl) per spec (e.g. 'pkg:generic/sensirion/sht41'). SBOM-grade.",
    )
    octopart_url: HttpUrl | None = Field(default=None, description="Octopart canonical URL.")
    nexar_part_id: str | None = Field(default=None, description="Nexar GraphQL part ID.")
    mouser_pn: str | None = Field(default=None, description="Mouser part number.")
    digikey_pn: str | None = Field(default=None, description="Digi-Key part number.")
    jlcpcb_pn: str | None = Field(
        default=None, description="JLCPCB LCSC part number (e.g. C12345)."
    )
