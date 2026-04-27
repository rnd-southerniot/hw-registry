"""Discovery descriptors — how to identify a board on the host (USB, MAC OUI)."""

from pydantic import Field

from .identifiable import Strict


class UsbId(Strict):
    """USB Vendor / Product ID pair for a discovery interface."""

    vid: str = Field(
        pattern=r"^[0-9A-Fa-f]{4}$",
        description="USB Vendor ID, hex without 0x prefix (e.g. 303A for Espressif).",
    )
    pid: str = Field(
        pattern=r"^[0-9A-Fa-f]{4}$",
        description="USB Product ID, hex without 0x prefix.",
    )
    description: str | None = Field(
        default=None,
        description="What this VID/PID represents (e.g. 'native USB serial', 'CP210x bridge').",
    )


class Discovery(Strict):
    """Host-side discovery hooks for the device."""

    usb: list[UsbId] = Field(
        default_factory=list,
        description="USB IDs the device may enumerate as (native + bridge variants).",
    )
    mac_oui: list[str] = Field(
        default_factory=list,
        description="MAC address OUIs assigned to this device's WiFi/BT/Ethernet (e.g. 'D0:EF:76').",
    )
