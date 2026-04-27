"""Named exceptions raised by the bundle builder.

Each is a real class (not a generic ``ValueError``) so the conflict checker
(Prompt 5) and the MCP server (Prompt 6) can catch them by name and convert
them into SARIF / structured tool errors. Reserve raw ``ValueError`` for
genuinely unexpected programming bugs.
"""

from __future__ import annotations

from pathlib import Path


class BuilderError(Exception):
    """Base for all builder-emitted errors."""


class ComponentValidationError(BuilderError):
    """A YAML failed Pydantic validation. Carries the file path for context."""

    def __init__(self, path: Path, original: object) -> None:
        self.path = path
        self.original = original
        super().__init__(f"{path}: {original}")


class InheritanceCycleError(BuilderError):
    """An ``inherits_from`` chain contains a cycle."""


class UnresolvedRefError(BuilderError):
    """A ref (``inherits_from`` / ``contains[].ref`` / etc.) does not point at any YAML."""


class UnknownOverrideKey(BuilderError):
    """An ``overrides`` key does not name a field on the resolved parent model."""


class MismatchedOverrideShorthand(BuilderError):
    """An ``overrides.pins[].alt_functions`` entry could not be coerced.

    Raised only for entries that are neither a string (handled by the
    soft-fallback path) nor a dict — i.e. structural type errors. A
    shorthand string that does not match any parent ``AltFunction`` is
    handled by the soft-fallback policy and does NOT raise this error;
    see the resolver docstring for the policy decision.
    """
