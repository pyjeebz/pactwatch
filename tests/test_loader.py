"""Tests for the spec loader."""

from pathlib import Path

import pytest

from pactwatch.loader import SpecLoadError, load_spec

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadSpec:
    """Test loading and validating OpenAPI specs."""

    def test_loads_valid_yaml(self):
        spec = load_spec(FIXTURES / "01_removed_endpoint_old.yaml")
        assert spec["openapi"] == "3.0.3"
        assert "/users/{id}" in spec["paths"]

    def test_resolves_paths(self):
        spec = load_spec(FIXTURES / "02_removed_response_field_old.yaml")
        schema = spec["paths"]["/users/{id}"]["get"]["responses"]["200"]
        content = schema["content"]["application/json"]["schema"]
        assert "id" in content["properties"]
        assert "email" in content["properties"]

    def test_error_on_missing_file(self):
        with pytest.raises(SpecLoadError, match="not found"):
            load_spec(FIXTURES / "nonexistent.yaml")

    def test_error_on_directory(self):
        with pytest.raises(SpecLoadError, match="Not a file"):
            load_spec(FIXTURES)

    def test_loads_multiple_fixtures(self):
        """Smoke test — every fixture file should load successfully."""
        for path in sorted(FIXTURES.glob("*.yaml")):
            spec = load_spec(path)
            assert spec["openapi"].startswith("3."), f"Failed for {path.name}"
