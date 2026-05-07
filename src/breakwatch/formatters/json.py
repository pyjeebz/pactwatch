"""JSON formatter for classified changes — designed for CI consumption."""

from __future__ import annotations

import json as _json

from breakwatch.classifier import ClassifiedChange, Severity


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


def format_check_json(
    producer: str,
    results: dict[str, list[ClassifiedChange]],
) -> str:
    """Return a JSON string representing per-consumer impact.

    Structure:
        {
            "producer": "api",
            "consumers": {
                "mobile-app": {
                    "summary": {"breaking": 1, "risky": 0, "safe": 0},
                    "changes": [...]
                }
            }
        }
    """
    consumers_output = {}
    for consumer_name, changes in sorted(results.items()):
        groups: dict[str, int] = {"breaking": 0, "risky": 0, "safe": 0}
        for c in changes:
            groups[c.severity.value.lower()] += 1

        consumers_output[consumer_name] = {
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

    output = {
        "producer": producer,
        "consumers": consumers_output,
    }

    return _json.dumps(output, indent=2)

