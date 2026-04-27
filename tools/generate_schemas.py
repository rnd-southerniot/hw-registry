"""Generate JSON Schemas from Pydantic models.

Walks the six component-kind models and emits ``schemas/<kind>.schema.json``
with stable key ordering and a CC-BY-4.0 SPDX header. Schemas are derived
artifacts — never hand-edited; CI fails the PR if ``schemas/`` drifts from
the models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from pydantic_models import Board, Chip, Connector, Driver, Module, Sensor

KIND_MODELS: dict[str, type] = {
    "board": Board,
    "module": Module,
    "chip": Chip,
    "sensor": Sensor,
    "connector": Connector,
    "driver": Driver,
}

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "schemas"

SPDX_HEADER = "SPDX-License-Identifier: CC-BY-4.0"


def build_schema(model: type) -> dict[str, Any]:
    """Return the validation-mode JSON Schema for *model* with an SPDX header injected."""
    schema = model.model_json_schema(mode="validation")
    return {"$comment": SPDX_HEADER, **schema}


def write_schema(target: Path, schema: dict[str, Any]) -> None:
    """Write *schema* to *target* with sort_keys + 2-space indent for diff stability."""
    target.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


@click.command()
@click.option(
    "--out",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_OUT,
    show_default=True,
    help="Output directory for generated schemas.",
)
def main(out: Path) -> None:
    """Generate schemas/<kind>.schema.json for every component kind."""
    out.mkdir(parents=True, exist_ok=True)
    for kind, model in KIND_MODELS.items():
        schema = build_schema(model)
        target = out / f"{kind}.schema.json"
        write_schema(target, schema)
        rel = target.relative_to(REPO_ROOT) if target.is_relative_to(REPO_ROOT) else target
        click.echo(f"wrote {rel}")


if __name__ == "__main__":
    main()
