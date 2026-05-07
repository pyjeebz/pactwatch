"""Markdown formatter for GitHub PR comments."""

from __future__ import annotations

from breakwatch.classifier import ClassifiedChange, Severity

MARKER = "<!-- breakwatch-report -->"


def format_check_markdown(
    producer: str,
    results: dict[str, list[ClassifiedChange]],
) -> str:
    """Return a GitHub-flavored Markdown report for a PR comment.

    Consumers with breaking changes are shown expanded.
    Safe-only consumers are wrapped in a collapsible <details> block.

    Args:
        producer: The producer name.
        results: Per-consumer classified changes.

    Returns:
        A Markdown string ready for posting as a PR comment.
    """
    lines: list[str] = [MARKER, ""]

    # Determine overall status
    has_breaking = any(
        any(c.severity == Severity.BREAKING for c in changes)
        for changes in results.values()
    )
    status = "BREAKING changes detected" if has_breaking else "No breaking changes"
    status_icon = "X" if has_breaking else "check"

    lines.append("## Breakwatch - API Change Report")
    lines.append("")
    lines.append(
        f"**Producer**: `{producer}` | "
        f"**Status**: :{status_icon}: {status}"
    )
    lines.append("")

    if not results:
        lines.append("No consumers found for this producer.")
        return "\n".join(lines)

    # Summary table
    lines.append("### Summary")
    lines.append("")
    lines.append("| Consumer | Breaking | Risky | Safe | Status |")
    lines.append("|----------|----------|-------|------|--------|")

    for name in sorted(results.keys()):
        changes = results[name]
        counts = _count_severities(changes)
        if counts["breaking"] > 0:
            status_cell = ":x: Breaking"
        elif counts["risky"] > 0:
            status_cell = ":warning: Risky"
        elif changes:
            status_cell = ":white_check_mark: Safe"
        else:
            status_cell = ":white_check_mark: No impact"
        lines.append(
            f"| {name} | {counts['breaking']} | {counts['risky']} "
            f"| {counts['safe']} | {status_cell} |"
        )

    lines.append("")

    # Per-consumer details
    for name in sorted(results.keys()):
        changes = results[name]
        consumer_breaking = any(c.severity == Severity.BREAKING for c in changes)

        if not changes:
            continue

        counts = _count_severities(changes)
        summary_text = _summary_text(counts)

        if consumer_breaking:
            # Expanded — breaking consumers are shown in full
            lines.append(f"### :x: {name}")
            lines.append("")
            lines.append(_changes_table(changes))
            lines.append("")
        else:
            # Collapsed — safe/risky consumers
            lines.append(
                f"<details>\n<summary><strong>{name}</strong> ({summary_text})</summary>\n"
            )
            lines.append(_changes_table(changes))
            lines.append("\n</details>")
            lines.append("")

    return "\n".join(lines)


def _count_severities(changes: list[ClassifiedChange]) -> dict[str, int]:
    """Count changes by severity."""
    counts = {"breaking": 0, "risky": 0, "safe": 0}
    for c in changes:
        counts[c.severity.value.lower()] += 1
    return counts


def _summary_text(counts: dict[str, int]) -> str:
    """Build a short summary like '1 breaking, 2 safe'."""
    parts = []
    if counts["breaking"]:
        parts.append(f"{counts['breaking']} breaking")
    if counts["risky"]:
        parts.append(f"{counts['risky']} risky")
    if counts["safe"]:
        parts.append(f"{counts['safe']} safe")
    return ", ".join(parts) if parts else "no changes"


def _changes_table(changes: list[ClassifiedChange]) -> str:
    """Build a Markdown table of changes."""
    lines = [
        "| Severity | Path | Change |",
        "|----------|------|--------|",
    ]
    for c in changes:
        severity_label = {
            Severity.BREAKING: ":x: BREAKING",
            Severity.RISKY: ":warning: RISKY",
            Severity.SAFE: ":white_check_mark: SAFE",
        }[c.severity]
        lines.append(f"| {severity_label} | `{c.path}` | {c.message} |")
    return "\n".join(lines)
