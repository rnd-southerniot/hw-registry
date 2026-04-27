"""Diagnostic dataclass shared across rules / SARIF emitter / CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Diagnostic:
    """A single conflict-checker finding.

    ``locations`` is a list of structured location records; each entry
    carries at least ``component_instance`` and may carry ``pin`` and/or
    ``bus``. SARIF mapping pulls fields from this dict.
    """

    id: str
    severity: Severity
    message: str
    rule: str
    locations: list[dict[str, str]] = field(default_factory=list)
    help_uri: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "severity": self.severity,
            "message": self.message,
            "rule": self.rule,
            "locations": list(self.locations),
        }
        if self.help_uri is not None:
            d["help_uri"] = self.help_uri
        return d
