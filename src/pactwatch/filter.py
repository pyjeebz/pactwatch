"""Per-consumer filtering — keep only changes that affect a consumer's endpoints."""

from __future__ import annotations

from pactwatch.classifier import ClassifiedChange
from pactwatch.graph import Consumer, endpoint_matches


def filter_for_consumer(
    changes: list[ClassifiedChange],
    consumer: Consumer,
    producer: str,
) -> list[ClassifiedChange]:
    """Filter classified changes to only those relevant to a specific consumer.

    A change is relevant if:
    1. The consumer uses the affected endpoint (exact or glob match), OR
    2. The change is global (security scheme changes affect everyone)

    Args:
        changes: Full list of classified changes from the diff.
        consumer: The consumer to filter for.
        producer: The producer name (to find the right dependency).

    Returns:
        Filtered list of ClassifiedChange objects relevant to this consumer.
    """
    # Get the endpoint patterns this consumer uses from this producer
    patterns: set[str] = set()
    for dep in consumer.consumes:
        if dep.producer == producer:
            patterns = set(dep.endpoints)
            break

    if not patterns:
        return []

    filtered: list[ClassifiedChange] = []
    for change in changes:
        if _is_relevant(change, patterns):
            filtered.append(change)

    return filtered


def _is_relevant(change: ClassifiedChange, patterns: set[str]) -> bool:
    """Determine if a classified change is relevant given a set of endpoint patterns."""
    # Global security changes affect all consumers
    if change.change.location == "security" and change.change.path in (
        "security",
        "securitySchemes",
    ):
        return True

    # Check if the change's endpoint matches any consumer pattern
    endpoint = change.path
    for pattern in patterns:
        if endpoint_matches(pattern, endpoint):
            return True

    return False
