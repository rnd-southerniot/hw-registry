"""Base class, shared enums, and regex constants for every component kind."""

from datetime import date as _date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# Full SemVer 2.0 — accepts prerelease and build identifiers (e.g. 1.0.0-rc.1).
SEMVER_REGEX = (
    r"^\d+\.\d+\.\d+"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

# Component slug — three lowercase path segments (kind / vendor / part).
# Path segment is plural ("boards/...") to match the directory layout under
# library/. The `kind` field is singular ("board"); the regex admits either.
COMPONENT_ID_REGEX = r"^[a-z]+/[a-z0-9-]+/[a-z0-9-]+$"

# Component reference — slug with optional @semver suffix.
COMPONENT_REF_REGEX = (
    r"^[a-z]+/[a-z0-9-]+/[a-z0-9-]+"
    r"(?:@\d+\.\d+\.\d+"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)?$"
)

Kind = Literal["board", "module", "chip", "sensor", "connector", "driver"]
Lifecycle = Literal["preview", "active", "deprecated", "end-of-life"]
TestedStatus = Literal["experimental", "stable", "production-tested", "stub"]


class Strict(BaseModel):
    """Base config for every model in the registry. Forbids unknown YAML keys."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        frozen=False,
        populate_by_name=False,
    )


class Tested(Strict):
    """POC sign-off record. Required on every component."""

    status: TestedStatus = Field(description="POC verification status.")
    by: str = Field(description="Engineer who signed off (email or GitHub handle).")
    date: _date = Field(description="Sign-off date in ISO 8601 format (YYYY-MM-DD).")
    evidence: str | None = Field(
        default=None,
        description="POC evidence — repo URL, photo path, or short note. Required by PR template for production-tested.",  # noqa: E501
    )


class Identifiable(Strict):
    """Common metadata header for every component kind."""

    api_version: Literal["hwreg/v1"] = Field(
        alias="apiVersion",
        description="Schema API version. Pinned to hwreg/v1; bumping requires a v2 migration.",
    )
    kind: Kind = Field(description="Component kind. Determines which model validates this YAML.")
    id: Annotated[str, Field(pattern=COMPONENT_ID_REGEX)] = Field(
        description="Slug kind/vendor/part. MUST equal the relative path under library/ minus .yaml."  # noqa: E501
    )
    revision: Annotated[str, Field(pattern=SEMVER_REGEX)] = Field(
        description="Component revision in SemVer 2.0. MAJOR=pin/electrical break, MINOR=behavior, PATCH=errata.",  # noqa: E501
    )
    summary: str = Field(
        max_length=120,
        description="One-line human description (≤ 120 characters).",
    )
    tested: Tested = Field(description="POC sign-off record.")
    lifecycle: Lifecycle = Field(
        description="Lifecycle stage. Drives deprecation surfacing for downstream consumers.",
    )
    code_owner: str | None = Field(
        default=None,
        description="GitHub team or handle responsible for this component.",
    )
