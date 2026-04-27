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
    """An ``overrides.pins[].alt_functions`` entry has the wrong structural type.

    Raised only for entries that are neither a string nor a dict — i.e.
    YAML-shape bugs (an int, a list-of-list, etc.). A shorthand string
    that does not match any parent ``AltFunction`` is NOT this error
    case: modules legitimately extend their parent's function vocabulary
    (vendor-specific firmware functions, e.g. RAK3172's RUI3 AT-firmware
    on pins the underlying STM32WLE5JC has no concept of). Unmatched
    shorthand emits ``AltFunctionShorthandWarning`` and coerces to a
    minimum-info ``{function: <name>}`` entry.
    """


class AltFunctionShorthandWarning(UserWarning):
    """Emitted when an ``overrides.pins[].alt_functions`` shorthand string
    does not match any AltFunction defined on the resolved parent.

    Not an error: modules legitimately extend their parent's function
    vocabulary. The warning surfaces typos in CI logs for human review;
    a typo PR shows the warning, the reviewer says "did you mean
    uart_rx?", author fixes, warning goes away. Filterable via standard
    Python warnings filters (``-W ignore::tools.builder.errors.AltFunctionShorthandWarning``).
    """
