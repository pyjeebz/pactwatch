"""PactWatch CLI -- Typer-based command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pactwatch.classifier import Severity, classify
from pactwatch.diff import diff_specs
from pactwatch.filter import filter_for_consumer
from pactwatch.formatters.json import format_check_json, format_json
from pactwatch.formatters.text import format_check_text, format_text
from pactwatch.graph import GraphLoadError, load_graph
from pactwatch.loader import SpecLoadError, load_spec

app = typer.Typer(
    name="pactwatch",
    help="OpenAPI breaking-change detector with consumer-graph awareness.",
    add_completion=False,
)
console = Console()


@app.command("diff")
def diff_cmd(
    old: Path = typer.Argument(..., help="Path to the old (base) OpenAPI spec."),
    new: Path = typer.Argument(..., help="Path to the new (head) OpenAPI spec."),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: 'text' or 'json'.",
    ),
) -> None:
    """Compare two OpenAPI specs and report classified changes.

    Exits with code 1 if any BREAKING changes are detected.
    """
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

    changes = diff_specs(old_spec, new_spec)
    classified = classify(changes)

    if format == "json":
        typer.echo(format_json(classified))
    else:
        format_text(classified, console=console)

    has_breaking = any(c.severity == Severity.BREAKING for c in classified)
    if has_breaking:
        raise typer.Exit(code=1)


@app.command("check")
def check_cmd(
    config: Path = typer.Option(
        ..., "--config", "-c", help="Path to pactwatch.yaml config file."
    ),
    producer: str = typer.Option(
        ..., "--producer", "-p", help="Name of the producer to check."
    ),
    old: Path = typer.Option(
        ..., "--old", help="Path to the old (base) OpenAPI spec."
    ),
    new: Path = typer.Option(
        ..., "--new", help="Path to the new (head) OpenAPI spec."
    ),
    consumer: Optional[str] = typer.Option(
        None, "--consumer", help="Check a single consumer (default: all)."
    ),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: 'text' or 'json'.",
    ),
) -> None:
    """Check per-consumer impact of a spec change using the consumer graph.

    Loads the consumer graph from pactwatch.yaml, diffs the old and new specs,
    then filters changes per consumer to show who is actually affected.

    Exits with code 1 if any consumer has BREAKING changes.
    """
    # Load graph
    try:
        graph = load_graph(config)
    except GraphLoadError as exc:
        console.print(f"[bold red]Error loading config:[/] {exc}")
        raise typer.Exit(code=2)

    if producer not in graph.producers:
        console.print(
            f"[bold red]Unknown producer:[/] {producer!r}. "
            f"Available: {', '.join(graph.producers.keys())}"
        )
        raise typer.Exit(code=2)

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

    # Determine which consumers to check
    if consumer:
        if consumer not in graph.consumers:
            console.print(
                f"[bold red]Unknown consumer:[/] {consumer!r}. "
                f"Available: {', '.join(graph.consumers.keys())}"
            )
            raise typer.Exit(code=2)
        consumers_to_check = [graph.consumers[consumer]]
    else:
        consumers_to_check = graph.consumers_of(producer)

    # Filter per consumer
    results: dict[str, list] = {}
    for c in consumers_to_check:
        filtered = filter_for_consumer(classified, c, producer)
        results[c.name] = filtered

    # Output
    if format == "json":
        typer.echo(format_check_json(producer, results))
    else:
        format_check_text(producer, results, console=console)

    # Exit code
    has_breaking = any(
        any(c.severity == Severity.BREAKING for c in changes_list)
        for changes_list in results.values()
    )
    if has_breaking:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
