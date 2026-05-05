"""Tests for the diff engine."""

from pathlib import Path

from pactwatch.diff import Change, diff_specs
from pactwatch.loader import load_spec

FIXTURES = Path(__file__).parent / "fixtures"


def _load_pair(name: str) -> tuple[dict, dict]:
    old = load_spec(FIXTURES / f"{name}_old.yaml")
    new = load_spec(FIXTURES / f"{name}_new.yaml")
    return old, new


def _find(changes: list[Change], **kwargs) -> list[Change]:
    """Filter changes matching all given field values."""
    result = []
    for c in changes:
        if all(getattr(c, k, None) == v for k, v in kwargs.items()):
            result.append(c)
    return result


class TestDiffRemovedEndpoint:
    def test_detects_removed_endpoint(self):
        old, new = _load_pair("01_removed_endpoint")
        changes = diff_specs(old, new)
        removed = _find(changes, change_type="removed", location="paths")
        assert len(removed) == 1
        assert removed[0].path == "DELETE /users/{id}"


class TestDiffRemovedResponseField:
    def test_detects_removed_required_field(self):
        old, new = _load_pair("02_removed_response_field")
        changes = diff_specs(old, new)
        removed = _find(changes, change_type="removed", location="schemas")
        assert len(removed) == 1
        assert removed[0].field == "email"
        assert removed[0].detail["was_required"] is True


class TestDiffTypeChange:
    def test_detects_type_change(self):
        old, new = _load_pair("03_type_change")
        changes = diff_specs(old, new)
        modified = _find(changes, change_type="modified", location="schemas")
        type_changes = [c for c in modified if c.detail.get("attribute") == "type"]
        assert len(type_changes) == 1
        assert type_changes[0].field == "age"
        assert type_changes[0].detail["old_value"] == "integer"
        assert type_changes[0].detail["new_value"] == "string"


class TestDiffRequiredRequestField:
    def test_detects_new_required_request_field(self):
        old, new = _load_pair("04_required_request_field_added")
        changes = diff_specs(old, new)
        added = _find(changes, change_type="added", location="schemas")
        required_added = [c for c in added if c.detail.get("is_required")]
        assert len(required_added) == 1
        assert required_added[0].field == "quantity"


class TestDiffStatusCodeRemoved:
    def test_detects_removed_status_code(self):
        old, new = _load_pair("05_status_code_removed")
        changes = diff_specs(old, new)
        removed = _find(changes, change_type="removed", location="responses")
        assert len(removed) == 1
        assert removed[0].detail["status_code"] == "404"


class TestDiffAuthScheme:
    def test_detects_auth_scheme_change(self):
        old, new = _load_pair("06_auth_scheme_changed")
        changes = diff_specs(old, new)
        security_changes = [c for c in changes if c.location == "security"]
        # BearerAuth removed, ApiKeyAuth added, top-level security modified
        assert len(security_changes) >= 2


class TestDiffOptionalToRequired:
    def test_detects_optional_to_required(self):
        old, new = _load_pair("07_optional_to_required")
        changes = diff_specs(old, new)
        req_changes = [c for c in changes
                       if c.detail.get("attribute") == "required"
                       and c.location == "schemas"]
        assert len(req_changes) == 1
        assert req_changes[0].field == "nickname"
        assert req_changes[0].detail["old_value"] is False
        assert req_changes[0].detail["new_value"] is True


class TestDiffMadeNullable:
    def test_detects_nullable_change(self):
        old, new = _load_pair("08_made_nullable")
        changes = diff_specs(old, new)
        nullable = [c for c in changes if c.detail.get("attribute") == "nullable"]
        assert len(nullable) == 1
        assert nullable[0].field == "email"
        assert nullable[0].detail["new_value"] is True


class TestDiffEnumRemoved:
    def test_detects_removed_enum_value(self):
        old, new = _load_pair("09_enum_removed")
        changes = diff_specs(old, new)
        enum_changes = [c for c in changes if c.detail.get("attribute") == "enum_removed"]
        assert len(enum_changes) == 1
        assert "cancelled" in enum_changes[0].detail["removed_values"]


class TestDiffNewEndpoint:
    def test_detects_new_endpoint(self):
        old, new = _load_pair("10_new_endpoint")
        changes = diff_specs(old, new)
        added = _find(changes, change_type="added", location="paths")
        assert len(added) == 1
        assert added[0].path == "POST /users"


class TestDiffNewOptionalField:
    def test_detects_new_optional_field(self):
        old, new = _load_pair("11_new_optional_field")
        changes = diff_specs(old, new)
        added = _find(changes, change_type="added", location="schemas")
        assert len(added) == 1
        assert added[0].field == "gift_message"
        assert added[0].detail["is_required"] is False


class TestDiffMixed:
    def test_mixed_changes(self):
        old, new = _load_pair("12_mixed_changes")
        changes = diff_specs(old, new)
        # Should have multiple change types
        change_types = {c.change_type for c in changes}
        assert "added" in change_types
        assert "removed" in change_types
        assert "modified" in change_types
        # Should be a non-trivial number of changes
        assert len(changes) >= 4
