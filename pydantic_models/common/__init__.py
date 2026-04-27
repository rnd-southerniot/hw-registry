"""Shared submodels reused across component kinds."""

from .assets import Asset, AssetBundle, Datasheet
from .discovery import Discovery, UsbId
from .electrical import CurrentDraw, Electrical, LogicSpec, VccSpec
from .identifiable import (
    COMPONENT_ID_REGEX,
    COMPONENT_REF_REGEX,
    SEMVER_REGEX,
    Identifiable,
    Kind,
    Lifecycle,
    Strict,
    Tested,
    TestedStatus,
)
from .interface import Interface, InterfaceType
from .package import Package, PackageDimensions
from .pin import AltFunction, Pin
from .refs import ExternalRefs, KicadRefs

__all__ = [
    "COMPONENT_ID_REGEX",
    "COMPONENT_REF_REGEX",
    "SEMVER_REGEX",
    "AltFunction",
    "Asset",
    "AssetBundle",
    "CurrentDraw",
    "Datasheet",
    "Discovery",
    "Electrical",
    "ExternalRefs",
    "Identifiable",
    "Interface",
    "InterfaceType",
    "KicadRefs",
    "Kind",
    "Lifecycle",
    "LogicSpec",
    "Package",
    "PackageDimensions",
    "Pin",
    "Strict",
    "Tested",
    "TestedStatus",
    "UsbId",
    "VccSpec",
]
