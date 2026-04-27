"""``hwlib-check-conflicts`` CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

import click

from .diagnostic import Diagnostic
from .errors import ConflictsError
from .graph import build_graph
from .loader import DEFAULT_BUNDLE, load_system
from .rules import run_all
from .sarif import to_sarif

OutputFormat = Literal["text", "json", "sarif"]


@click.command()
@click.argument(
    "system_yaml",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--bundle",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_BUNDLE,
    show_default=True,
    help="Path to library.sqlite (build with `make bundle` first).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "sarif"]),
    default="text",
    show_default=True,
    help="Diagnostic output format.",
)
def main(system_yaml: Path, bundle: Path, output_format: OutputFormat) -> None:
    """Validate a system YAML against the bundled component registry.

    Exit codes:
      0  no errors (warnings are tolerated)
      1  one or more error-severity diagnostics
      2  load / usage error
    """
    try:
        system = load_system(system_yaml, bundle_db=bundle)
    except ConflictsError as e:
        click.echo(f"error: {e}", err=True)
        sys.exit(2)

    graph = build_graph(system)
    diagnostics = run_all(graph, system)

    if output_format == "text":
        _emit_text(diagnostics, system_yaml)
    elif output_format == "json":
        click.echo(json.dumps([d.to_dict() for d in diagnostics], indent=2, sort_keys=True))
    elif output_format == "sarif":
        click.echo(json.dumps(to_sarif(diagnostics, system_yaml), indent=2, sort_keys=True))

    error_count = sum(1 for d in diagnostics if d.severity == "error")
    sys.exit(1 if error_count > 0 else 0)


def _emit_text(diagnostics: list[Diagnostic], system_yaml: Path) -> None:
    """Compiler-style output: ``<file>: <severity>: [RULE_ID] <message>``."""
    if not diagnostics:
        click.echo(f"{system_yaml}: ok  (0 errors, 0 warnings)")
        return

    error_count = sum(1 for d in diagnostics if d.severity == "error")
    warn_count = sum(1 for d in diagnostics if d.severity == "warning")
    info_count = sum(1 for d in diagnostics if d.severity == "info")

    for d in diagnostics:
        click.echo(
            f"{system_yaml}: {d.severity}: [{d.id}] {d.message}", err=(d.severity == "error")
        )

    summary = f"{system_yaml}: {error_count} error(s), {warn_count} warning(s), {info_count} info"
    click.echo(summary, err=(error_count > 0))


if __name__ == "__main__":
    main()
