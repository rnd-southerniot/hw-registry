"""Module model — RF/SoM modules that contain other components and expose pads/pins."""

from typing import Annotated, Any, Literal

from pydantic import Field

from .common import (
    COMPONENT_REF_REGEX,
    AssetBundle,
    Electrical,
    ExternalRefs,
    Identifiable,
    KicadRefs,
    Package,
    Pin,
    Strict,
)

ComponentRef = Annotated[str, Field(pattern=COMPONENT_REF_REGEX)]


class ContainedPart(Strict):
    """A component physically integrated into a module (SoC, antenna, memory, etc.).

    NOTE: passive components (caps, resistors, TCXOs) are intentionally NOT
    cataloged in MVP — the registry only tracks parts with a POC. The
    `passives/...` example in BLUEPRINT.md sec 3.2 is illustrative only;
    real RAK3172 YAML omits the TCXO entry.
    TODO(prompt-4): validate override keys against resolved parent (out of scope
    for the model; lives in the bundle resolver where the parent is known).
    """

    ref: ComponentRef = Field(
        description="Component ref of the contained part (e.g. chips/st/stm32wle5jc@1.0.0).",
    )
    role: str = Field(
        description="Role within the module (e.g. soc, antenna, flash, psram, balun, tcxo).",
    )
    qty: int = Field(
        default=1,
        ge=1,
        description="Number of instances of this part inside the module.",
    )


class FirmwareOption(Strict):
    """Pre-flashed firmware variant available from the vendor (e.g. AT-command stack)."""

    name: str = Field(description="Firmware variant name (e.g. rui3, open-stm32wlxx-source).")
    default: bool = Field(
        default=False,
        description="True if this is the variant shipped from the factory.",
    )
    at_baud: int | None = Field(
        default=None,
        description="Default AT-command UART baud rate (only meaningful for AT firmware).",
    )
    at_format: str | None = Field(
        default=None,
        description="UART format for AT mode (e.g. '8N1').",
    )
    repo: str | None = Field(
        default=None,
        description="Source repository URL or shorthand (e.g. github.com/RAKWireless/RUI_v3.x).",
    )


class Module(Identifiable):
    """An RF / SoM module exposing pads or pins, containing one or more chips."""

    kind: Literal["module"] = "module"

    vendor: str = Field(description="Vendor slug from Zephyr's vendor-prefixes.txt.")
    manufacturer_part_number: str = Field(description="Manufacturer P/N as printed on the module.")
    package: Package = Field(description="Physical package envelope.")
    electrical: Electrical = Field(description="Electrical specs.")
    pins: list[Pin] = Field(
        default_factory=list,
        description="Module pads/pins exposed externally.",
    )
    contains: list[ContainedPart] = Field(
        default_factory=list,
        description="Components physically integrated into this module.",
    )
    overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Field-by-field overrides applied on top of contained parts during inheritance resolution.",  # noqa: E501
    )
    # TODO(prompt-4) — bundle resolver semantics for `overrides`:
    #
    # 1. Merge precedence (top-level fields under `overrides`):
    #    - Lists merge by REPLACEMENT (child's list fully replaces parent's).
    #      No `merge: append / by_id` modes in MVP — keep the rule simple,
    #      add modes only when a real component needs them.
    #    - Dicts merge by DEEP-UPDATE (child's keys win, parent's other keys
    #      are preserved).
    #    - The `overrides` block is the most-specific layer; it is applied
    #      LAST, after the `inherits_from` chain has been resolved.
    #
    # 2. Override-key validation:
    #    Override keys MUST correspond to fields on the resolved parent
    #    model. An override key that names a field the parent does not
    #    have is rejected as `UnknownOverrideKey`. Catches typos at
    #    bundle-build time (the parent isn't known to the model alone, so
    #    the check has to live in the resolver).
    #
    # 3. AltFunction shorthand coercion:
    #    Inside `overrides.pins[].alt_functions`, authors may use shorthand
    #    string entries (`alt_functions: [gpio, uart_rx]`) instead of full
    #    AltFunction dicts. The resolver coerces each shorthand string by
    #    looking up the parent component's matching AltFunction (by
    #    `function` name) and copying it. Mixed shorthand-and-dict forms
    #    in one override list are allowed; explicit dict fields overlay
    #    parent fields per-key. A shorthand string that does not match any
    #    parent AltFunction is rejected as `MismatchedOverrideShorthand`.
    #    The on-disk bundle (dist/library.json) only ever contains the
    #    fully-realized AltFunction dicts — shorthand never escapes the
    #    YAML layer.
    firmware_options: list[FirmwareOption] = Field(
        default_factory=list,
        description="Pre-flashed firmware variants offered by the vendor (e.g. AT-command stacks).",
    )
    # rf_certifications moved to Package (site #14): the certs apply to the
    # physical package the FCC/CE silkscreen is printed on, not to the abstract
    # Module record.
    kicad: KicadRefs | None = Field(default=None)
    external_refs: ExternalRefs | None = Field(default=None)
    assets: AssetBundle | None = Field(default=None)
    inherits_from: list[ComponentRef] = Field(
        default_factory=list,
        description="Component refs this module inherits from (typically the SoC chip).",
    )
