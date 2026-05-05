"""Tests for the CLI."""

from pathlib import Path

from typer.testing import CliRunner

from pactwatch.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


class TestDiffCommand:
    def test_breaking_exits_1(self):
        result = runner.invoke(app, [
            str(FIXTURES / "01_removed_endpoint_old.yaml"),
            str(FIXTURES / "01_removed_endpoint_new.yaml"),
        ])
        assert result.exit_code == 1

    def test_safe_exits_0(self):
        result = runner.invoke(app, [
            str(FIXTURES / "10_new_endpoint_old.yaml"),
            str(FIXTURES / "10_new_endpoint_new.yaml"),
        ])
        assert result.exit_code == 0

    def test_text_format(self):
        result = runner.invoke(app, [
            str(FIXTURES / "01_removed_endpoint_old.yaml"),
            str(FIXTURES / "01_removed_endpoint_new.yaml"),
            "--format", "text",
        ])
        assert "BREAKING" in result.output or "breaking" in result.output

    def test_json_format(self):
        result = runner.invoke(app, [
            str(FIXTURES / "12_mixed_changes_old.yaml"),
            str(FIXTURES / "12_mixed_changes_new.yaml"),
            "--format", "json",
        ])
        import json
        data = json.loads(result.output)
        assert "summary" in data
        assert "changes" in data
        assert data["summary"]["breaking"] >= 1

    def test_invalid_spec_exits_2(self):
        result = runner.invoke(app, [
            str(FIXTURES / "nonexistent.yaml"),
            str(FIXTURES / "01_removed_endpoint_new.yaml"),
        ])
        assert result.exit_code == 2

    def test_no_changes(self):
        """Same file compared to itself should produce 0 exit code."""
        result = runner.invoke(app, [
            str(FIXTURES / "01_removed_endpoint_old.yaml"),
            str(FIXTURES / "01_removed_endpoint_old.yaml"),
        ])
        assert result.exit_code == 0
