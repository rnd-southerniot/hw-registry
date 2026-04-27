"""hw-registry bundle builder."""

from .build import assemble_bundle, build, discover, main, resolve
from .errors import (
    BuilderError,
    ComponentValidationError,
    InheritanceCycleError,
    MismatchedOverrideShorthand,
    UnknownOverrideKey,
    UnresolvedRefError,
)

__all__ = [
    "BuilderError",
    "ComponentValidationError",
    "InheritanceCycleError",
    "MismatchedOverrideShorthand",
    "UnknownOverrideKey",
    "UnresolvedRefError",
    "assemble_bundle",
    "build",
    "discover",
    "main",
    "resolve",
]
