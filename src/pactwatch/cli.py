"""PactWatch CLI — Typer-based command-line interface."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from pactwatch.classifier import Severity, classify
from pactwatch.diff import diff_specs
from pactwatch.formatters.json import format_json
from pactwatch.formatters.text import format_text
from pactwatch.loader import SpecLoadError, load_spec

app = typer.Typer(
    name="pactwatch",
    help="OpenAPI breaking-change detector with consumer-graph awareness.",
    add_completion=False,
)
console = Console()


@app.command()
def diff(
    old: Path = typer.Argument(..., help="Path to the old (base) OpenAPI spec."),
    new: Path = typer.Argument(..., help="Path to the new (head) OpenAPI spec."),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: 'text' for Rich terminal output, 'json' for structured JSON.",
    ),
) -> None:
    """Compare two OpenAPI specs and report classified changes.

    Exits with code 1 if any BREAKING changes are detected.
    """
    # Load specs
    try:
        old_spec = load_spec(old)
    except SpecLoadError as exc:
        console.print(f"[bold red]Error loading old spec:[/] {exc}")
        raise typer.Exit(code=2)

    try:
        new_spec = load_spec(new)
    except SpecLoadError as exc:
        console.print(f"[bold red]Error loading new spec:[/] {exc}")
        raise typer.Exit(code=2)

    # Diff and classify
    changes = diff_specs(old_spec, new_spec)
    classified = classify(changes)

    # Output
    if format == "json":
        typer.echo(format_json(classified))
    else:
        format_text(classified, console=console)

    # Exit code
    has_breaking = any(c.severity == Severity.BREAKING for c in classified)
    if has_breaking:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
