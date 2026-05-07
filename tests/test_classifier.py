"""Tests for the classifier."""

from pathlib import Path

from breakwatch.classifier import ClassifiedChange, Severity, classify
from breakwatch.diff import diff_specs
from breakwatch.loader import load_spec

FIXTURES = Path(__file__).parent / "fixtures"


def _load_and_classify(name: str) -> list[ClassifiedChange]:
    old = load_spec(FIXTURES / f"{name}_old.yaml")
    new = load_spec(FIXTURES / f"{name}_new.yaml")
    changes = diff_specs(old, new)
    return classify(changes)


def _severities(classified: list[ClassifiedChange]) -> set[str]:
    return {c.severity.value for c in classified}


class TestBreakingRules:
    def test_removed_endpoint(self):
        result = _load_and_classify("01_removed_endpoint")
        breaking = [c for c in result if c.severity == Severity.BREAKING]
        assert len(breaking) == 1
        assert "DELETE /users/{id}" in breaking[0].message

    def test_removed_required_response_field(self):
        result = _load_and_classify("02_removed_response_field")
        breaking = [c for c in result if c.severity == Severity.BREAKING]
        assert len(breaking) == 1
        assert "email" in breaking[0].message

    def test_response_field_type_changed(self):
        result = _load_and_classify("03_type_change")
        breaking = [c for c in result if c.severity == Severity.BREAKING]
        assert len(breaking) == 1
        assert "age" in breaking[0].message

    def test_required_field_added_to_request(self):
        result = _load_and_classify("04_required_request_field_added")
        breaking = [c for c in result if c.severity == Severity.BREAKING]
        assert len(breaking) == 1
        assert "quantity" in breaking[0].message

    def test_status_code_removed(self):
        result = _load_and_classify("05_status_code_removed")
        breaking = [c for c in result if c.severity == Severity.BREAKING]
        assert len(breaking) == 1
        assert "404" in breaking[0].message

    def test_auth_scheme_changed(self):
        result = _load_and_classify("06_auth_scheme_changed")
        breaking = [c for c in result if c.severity == Severity.BREAKING]
        assert len(breaking) >= 1


class TestRiskyRules:
    def test_optional_to_required(self):
        result = _load_and_classify("07_optional_to_required")
        risky = [c for c in result if c.severity == Severity.RISKY]
        assert len(risky) == 1
        assert "nickname" in risky[0].message

    def test_made_nullable(self):
        result = _load_and_classify("08_made_nullable")
        risky = [c for c in result if c.severity == Severity.RISKY]
        assert len(risky) == 1
        assert "email" in risky[0].message

    def test_enum_removed(self):
        result = _load_and_classify("09_enum_removed")
        risky = [c for c in result if c.severity == Severity.RISKY]
        assert len(risky) == 1
        assert "cancelled" in risky[0].message


class TestSafeRules:
    def test_new_endpoint(self):
        result = _load_and_classify("10_new_endpoint")
        safe = [c for c in result if c.severity == Severity.SAFE]
        assert len(safe) == 1
        assert "POST /users" in safe[0].message

    def test_new_optional_field(self):
        result = _load_and_classify("11_new_optional_field")
        safe = [c for c in result if c.severity == Severity.SAFE]
        assert len(safe) == 1
        assert "gift_message" in safe[0].message


class TestMixedChanges:
    def test_mixed_has_all_severities(self):
        result = _load_and_classify("12_mixed_changes")
        severities = _severities(result)
        assert "BREAKING" in severities
        assert "SAFE" in severities

    def test_sorted_by_severity(self):
        result = _load_and_classify("12_mixed_changes")
        priority = {"BREAKING": 0, "RISKY": 1, "SAFE": 2}
        values = [priority[c.severity.value] for c in result]
        assert values == sorted(values), "Changes should be sorted BREAKING → RISKY → SAFE"


class TestClassifyEmpty:
    def test_no_changes(self):
        result = classify([])
        assert result == []
