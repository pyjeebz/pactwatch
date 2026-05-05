"""JSON formatter for classified changes — designed for CI consumption."""

from __future__ import annotations

import json as _json

from pactwatch.classifier import ClassifiedChange, Severity


def format_json(changes: list[ClassifiedChange]) -> str:
    """Return a JSON string representing the classified changes.

    Structure:
        {
            "summary": {"breaking": N, "risky": N, "safe": N},
            "changes": [
                {
                    "severity": "BREAKING",
                    "message": "...",
                    "path": "...",
                    "detail": { ... }
                }
            ]
        }
    """
    groups: dict[str, int] = {"breaking": 0, "risky": 0, "safe": 0}
    for c in changes:
        groups[c.severity.value.lower()] += 1

    output = {
        "summary": groups,
        "changes": [
            {
                "severity": c.severity.value,
                "message": c.message,
                "path": c.path,
                "detail": _sanitize_detail(c.change.detail),
            }
            for c in changes
        ],
    }

    return _json.dumps(output, indent=2)


def _sanitize_detail(detail: dict) -> dict:
    """Ensure all detail values are JSON-serializable."""
    sanitized = {}
    for key, value in detail.items():
        if isinstance(value, set):
            sanitized[key] = sorted(value)
        elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized
