"""Connector model — physical mating connectors (headers, JST, USB, edge)."""

from typing import Annotated, Literal

from pydantic import Field

from .common import (
    COMPONENT_REF_REGEX,
    AssetBundle,
    ExternalRefs,
    Identifiable,
    KicadRefs,
    Strict,
)

ComponentRef = Annotated[str, Field(pattern=COMPONENT_REF_REGEX)]


Gender = Literal["male", "female", "hermaphroditic"]
Mounting = Literal["smd", "tht", "edge", "panel"]


class ConnectorPin(Strict):
    """A single contact in a connector."""

    position: int = Field(ge=1, description="Pin position (1-indexed).")
    signal: str = Field(description="Default signal name (e.g. VCC, GND, SDA, D+, RX).")
    notes: str | None = Field(default=None, description="Datasheet caveats or polarity notes.")


class Connector(Identifiable):
    """A physical mating connector."""

    kind: Literal["connector"] = "connector"

    vendor: str = Field(description="Vendor slug.")
    manufacturer_part_number: str = Field(
        description="Manufacturer P/N (e.g. JST-PH 2-pin SMD top entry)."
    )
    pin_count: int = Field(ge=1, description="Number of contacts.")
    pitch_mm: float = Field(description="Pin-to-pin pitch in millimetres.")
    gender: Gender = Field(description="Connector gender.")
    mounting: Mounting = Field(description="Board mounting style.")
    pinout: list[ConnectorPin] = Field(
        default_factory=list,
        description="Per-position signal assignment.",
    )
    mating_part: ComponentRef | None = Field(
        default=None,
        description="Component ref of the typical mating connector.",
    )
    kicad: KicadRefs | None = Field(default=None)
    external_refs: ExternalRefs | None = Field(default=None)
    assets: AssetBundle | None = Field(default=None)
