"""SARIF 2.1.0 emitter for the pin-conflict checker.

Produces a single ``run`` against a single ``tool`` (name "hwlib-conflicts"),
with each ``Diagnostic`` mapped to a ``Result``. Severity mapping:

    error → error
    warning → warning
    info → note

The output is portable: ``physicalLocation.artifactLocation.uri`` is set
to the system YAML path (relative or absolute as supplied), with
``uriBaseId = "%SRCROOT%"`` so consumers know the path is repo-relative.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .diagnostic import Diagnostic, Severity

TOOL_NAME = "hwlib-conflicts"
TOOL_VERSION = "0.1.0"
TOOL_INFORMATION_URI = "https://github.com/rnd-southerniot/hw-registry"

_SARIF_LEVEL: dict[Severity, str] = {
    "error": "error",
    "warning": "warning",
    "info": "note",
}


def to_sarif(diagnostics: list[Diagnostic], system_yaml: Path) -> dict[str, Any]:
    """Build a SARIF 2.1.0 ``sarifLog`` object."""
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "version": TOOL_VERSION,
                        "informationUri": TOOL_INFORMATION_URI,
                        "rules": _emit_rules(diagnostics),
                    }
                },
                "originalUriBaseIds": {
                    "%SRCROOT%": {"uri": "./", "description": {"text": "Repository root"}},
                },
                "results": [_to_sarif_result(d, system_yaml) for d in diagnostics],
            }
        ],
    }


def _emit_rules(diagnostics: list[Diagnostic]) -> list[dict[str, Any]]:
    """Emit a deduplicated list of rule descriptors referenced by the results."""
    seen: dict[str, dict[str, Any]] = {}
    for d in diagnostics:
        if d.id in seen:
            continue
        rule_descriptor: dict[str, Any] = {
            "id": d.id,
            "name": d.rule,
            "shortDescription": {"text": d.message[:120]},
        }
        if d.help_uri is not None:
            rule_descriptor["helpUri"] = d.help_uri
        seen[d.id] = rule_descriptor
    return sorted(seen.values(), key=lambda r: r["id"])


def _to_sarif_result(d: Diagnostic, system_yaml: Path) -> dict[str, Any]:
    """Convert a single ``Diagnostic`` to a SARIF ``result`` object."""
    result: dict[str, Any] = {
        "ruleId": d.id,
        "level": _SARIF_LEVEL[d.severity],
        "message": {"text": d.message},
        "locations": [_artifact_location(system_yaml)],
    }
    if d.locations:
        # Per-component logical locations supplement the artifact location.
        result["properties"] = {"locations": list(d.locations)}
    return result


def _artifact_location(system_yaml: Path) -> dict[str, Any]:
    return {
        "physicalLocation": {
            "artifactLocation": {
                "uri": str(system_yaml).replace("\\", "/"),
                "uriBaseId": "%SRCROOT%",
            },
        },
    }
