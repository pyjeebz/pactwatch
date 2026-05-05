"""Rich-powered terminal formatter for classified changes."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pactwatch.classifier import ClassifiedChange, Severity


_SEVERITY_STYLES = {
    Severity.BREAKING: ("bold red", "[X]"),
    Severity.RISKY: ("bold yellow", "[!]"),
    Severity.SAFE: ("bold green", "[+]"),
}


def format_text(changes: list[ClassifiedChange], console: Console | None = None) -> None:
    """Print classified changes to the terminal using Rich formatting.

    Groups changes by severity (BREAKING → RISKY → SAFE) with color-coded
    output and a summary line.
    """
    console = console or Console()

    if not changes:
        console.print(Panel("No changes detected.", style="green"))
        return

    # Group by severity
    groups: dict[Severity, list[ClassifiedChange]] = {}
    for change in changes:
        groups.setdefault(change.severity, []).append(change)

    # Header
    console.print()
    console.print(
        Panel(
            Text("PactWatch - Change Report", style="bold white"),
            style="blue",
        )
    )
    console.print()

    # Render each severity group
    for severity in (Severity.BREAKING, Severity.RISKY, Severity.SAFE):
        group = groups.get(severity, [])
        if not group:
            continue

        style, icon = _SEVERITY_STYLES[severity]

        table = Table(
            title=f"{icon}  {severity.value} ({len(group)})",
            title_style=style,
            show_lines=True,
            expand=True,
        )
        table.add_column("Path", style="cyan", ratio=1)
        table.add_column("Change", ratio=2)

        for c in group:
            table.add_row(c.path, c.message)

        console.print(table)
        console.print()

    # Summary
    breaking = len(groups.get(Severity.BREAKING, []))
    risky = len(groups.get(Severity.RISKY, []))
    safe = len(groups.get(Severity.SAFE, []))

    summary = Text()
    summary.append(f"{breaking} breaking", style="bold red")
    summary.append(", ")
    summary.append(f"{risky} risky", style="bold yellow")
    summary.append(", ")
    summary.append(f"{safe} safe", style="bold green")
    summary.append(" changes detected.")

    console.print(Panel(summary, title="Summary", style="blue"))
    console.print()
