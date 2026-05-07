"""Classifier — assign severity labels to raw Changes from the diff engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from breakwatch.diff import Change


class Severity(str, Enum):
    """Severity level for a classified API change."""
    BREAKING = "BREAKING"
    RISKY = "RISKY"
    SAFE = "SAFE"


@dataclass
class ClassifiedChange:
    """A Change with an assigned severity and human-readable message."""
    severity: Severity
    message: str
    path: str
    change: Change


def classify(changes: list[Change]) -> list[ClassifiedChange]:
    """Classify a list of raw Changes into severity-labelled ClassifiedChanges.

    Rules are applied in priority order: BREAKING > RISKY > SAFE.
    Every change gets exactly one classification.
    """
    classified: list[ClassifiedChange] = []

    for change in changes:
        result = _apply_rules(change)
        if result:
            classified.append(result)

    # Sort: BREAKING first, then RISKY, then SAFE
    priority = {Severity.BREAKING: 0, Severity.RISKY: 1, Severity.SAFE: 2}
    classified.sort(key=lambda c: priority[c.severity])

    return classified


# ---------------------------------------------------------------------------
# Rule dispatcher
# ---------------------------------------------------------------------------

_RULES: list[callable] = []


def _rule(fn):
    """Decorator to register a classification rule."""
    _RULES.append(fn)
    return fn


def _apply_rules(change: Change) -> ClassifiedChange | None:
    """Try each rule in priority order; return the first match."""
    for rule in _RULES:
        result = rule(change)
        if result is not None:
            return result
    return None


# ---------------------------------------------------------------------------
# BREAKING rules
# ---------------------------------------------------------------------------

@_rule
def _removed_endpoint(change: Change) -> ClassifiedChange | None:
    if change.change_type == "removed" and change.location == "paths":
        return ClassifiedChange(
            severity=Severity.BREAKING,
            message=f"Removed endpoint: {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _removed_required_response_field(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "removed"
            and change.location == "schemas"
            and change.detail.get("context") == "response"
            and change.detail.get("was_required", False)):
        return ClassifiedChange(
            severity=Severity.BREAKING,
            message=f"Removed required response field '{change.field}' from {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _response_field_type_changed(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "modified"
            and change.location == "schemas"
            and change.detail.get("context") == "response"
            and change.detail.get("attribute") == "type"):
        old = change.detail.get("old_value")
        new = change.detail.get("new_value")
        return ClassifiedChange(
            severity=Severity.BREAKING,
            message=f"Type changed on response field '{change.field}': {old} -> {new} in {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _required_field_added_to_request(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "added"
            and change.location == "schemas"
            and change.detail.get("context") == "request"
            and change.detail.get("is_required", False)):
        return ClassifiedChange(
            severity=Severity.BREAKING,
            message=f"New required request field '{change.field}' added to {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _status_code_removed(change: Change) -> ClassifiedChange | None:
    if change.change_type == "removed" and change.location == "responses":
        code = change.detail.get("status_code", change.field)
        return ClassifiedChange(
            severity=Severity.BREAKING,
            message=f"Status code {code} removed from {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _auth_scheme_changed(change: Change) -> ClassifiedChange | None:
    if change.location == "security" and change.change_type in ("removed", "modified"):
        if change.field:
            msg = f"Security scheme '{change.field}' {change.change_type}"
        else:
            msg = f"Security requirements {change.change_type} on {change.path}"
        return ClassifiedChange(
            severity=Severity.BREAKING,
            message=msg,
            path=change.path,
            change=change,
        )
    return None


# ---------------------------------------------------------------------------
# RISKY rules
# ---------------------------------------------------------------------------

@_rule
def _optional_response_field_made_required(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "modified"
            and change.location == "schemas"
            and change.detail.get("context") == "response"
            and change.detail.get("attribute") == "required"
            and change.detail.get("old_value") is False
            and change.detail.get("new_value") is True):
        return ClassifiedChange(
            severity=Severity.RISKY,
            message=f"Response field '{change.field}' changed from optional to required in {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _response_field_made_nullable(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "modified"
            and change.location == "schemas"
            and change.detail.get("context") == "response"
            and change.detail.get("attribute") == "nullable"
            and change.detail.get("old_value") is False
            and change.detail.get("new_value") is True):
        return ClassifiedChange(
            severity=Severity.RISKY,
            message=f"Response field '{change.field}' made nullable in {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _enum_value_removed_from_response(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "modified"
            and change.location == "schemas"
            and change.detail.get("context") == "response"
            and change.detail.get("attribute") == "enum_removed"):
        removed = change.detail.get("removed_values", [])
        return ClassifiedChange(
            severity=Severity.RISKY,
            message=f"Enum values {removed} removed from response field '{change.field}' in {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _default_value_changed(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "modified"
            and change.location == "schemas"
            and change.detail.get("context") == "request"
            and change.detail.get("attribute") == "default"):
        old = change.detail.get("old_value")
        new = change.detail.get("new_value")
        return ClassifiedChange(
            severity=Severity.RISKY,
            message=f"Default value changed on request field '{change.field}': {old!r} -> {new!r} in {change.path}",
            path=change.path,
            change=change,
        )
    return None


# ---------------------------------------------------------------------------
# SAFE rules
# ---------------------------------------------------------------------------

@_rule
def _new_endpoint(change: Change) -> ClassifiedChange | None:
    if change.change_type == "added" and change.location == "paths":
        return ClassifiedChange(
            severity=Severity.SAFE,
            message=f"New endpoint: {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _new_optional_request_field(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "added"
            and change.location == "schemas"
            and change.detail.get("context") == "request"
            and not change.detail.get("is_required", False)):
        return ClassifiedChange(
            severity=Severity.SAFE,
            message=f"New optional request field '{change.field}' added to {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _new_enum_value(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "modified"
            and change.location == "schemas"
            and change.detail.get("attribute") == "enum_added"):
        added = change.detail.get("added_values", [])
        return ClassifiedChange(
            severity=Severity.SAFE,
            message=f"New enum values {added} added to field '{change.field}' in {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _new_response_field(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "added"
            and change.location == "schemas"
            and change.detail.get("context") == "response"):
        return ClassifiedChange(
            severity=Severity.SAFE,
            message=f"New response field '{change.field}' added to {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _description_changed(change: Change) -> ClassifiedChange | None:
    if (change.change_type == "modified"
            and change.location == "paths"
            and change.field in ("description", "summary")):
        return ClassifiedChange(
            severity=Severity.SAFE,
            message=f"Description/summary changed on {change.path}",
            path=change.path,
            change=change,
        )
    return None


# Catch-all for anything that slips through
@_rule
def _removed_optional_response_field(change: Change) -> ClassifiedChange | None:
    """Removed optional response field — risky but not strictly breaking."""
    if (change.change_type == "removed"
            and change.location == "schemas"
            and change.detail.get("context") == "response"
            and not change.detail.get("was_required", False)):
        return ClassifiedChange(
            severity=Severity.RISKY,
            message=f"Removed optional response field '{change.field}' from {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _new_security_scheme(change: Change) -> ClassifiedChange | None:
    if change.location == "security" and change.change_type == "added":
        return ClassifiedChange(
            severity=Severity.SAFE,
            message=f"New security scheme added: {change.field or change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _added_response_code(change: Change) -> ClassifiedChange | None:
    if change.change_type == "added" and change.location == "responses":
        code = change.detail.get("status_code", change.field)
        return ClassifiedChange(
            severity=Severity.SAFE,
            message=f"New response status code {code} added to {change.path}",
            path=change.path,
            change=change,
        )
    return None


@_rule
def _fallback(change: Change) -> ClassifiedChange | None:
    """Catch-all for unclassified changes."""
    return ClassifiedChange(
        severity=Severity.RISKY,
        message=f"Unclassified change: {change.change_type} {change.location} at {change.path}",
        path=change.path,
        change=change,
    )
