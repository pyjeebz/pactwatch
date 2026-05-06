"""Tests for the CLI."""

from pathlib import Path

from typer.testing import CliRunner

from pactwatch.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
GRAPH_FIXTURES = FIXTURES / "graph"
runner = CliRunner()


class TestDiffCommand:
    """Phase 1 diff command — now as an explicit subcommand."""

    def test_breaking_exits_1(self):
        result = runner.invoke(app, [
            "diff",
            str(FIXTURES / "01_removed_endpoint_old.yaml"),
            str(FIXTURES / "01_removed_endpoint_new.yaml"),
        ])
        assert result.exit_code == 1

    def test_safe_exits_0(self):
        result = runner.invoke(app, [
            "diff",
            str(FIXTURES / "10_new_endpoint_old.yaml"),
            str(FIXTURES / "10_new_endpoint_new.yaml"),
        ])
        assert result.exit_code == 0

    def test_text_format(self):
        result = runner.invoke(app, [
            "diff",
            str(FIXTURES / "01_removed_endpoint_old.yaml"),
            str(FIXTURES / "01_removed_endpoint_new.yaml"),
            "--format", "text",
        ])
        assert "BREAKING" in result.output or "breaking" in result.output

    def test_json_format(self):
        result = runner.invoke(app, [
            "diff",
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
            "diff",
            str(FIXTURES / "nonexistent.yaml"),
            str(FIXTURES / "01_removed_endpoint_new.yaml"),
        ])
        assert result.exit_code == 2

    def test_no_changes(self):
        result = runner.invoke(app, [
            "diff",
            str(FIXTURES / "01_removed_endpoint_old.yaml"),
            str(FIXTURES / "01_removed_endpoint_old.yaml"),
        ])
        assert result.exit_code == 0


class TestCheckCommand:
    """Phase 2 check command — per-consumer impact analysis."""

    def test_check_all_consumers_text(self):
        result = runner.invoke(app, [
            "check",
            "--config", str(GRAPH_FIXTURES / "pactwatch.yaml"),
            "--producer", "api",
            "--old", str(GRAPH_FIXTURES / "api_old.yaml"),
            "--new", str(GRAPH_FIXTURES / "api_new.yaml"),
        ])
        # Should show both consumers
        assert "mobile-app" in result.output
        assert "web-dashboard" in result.output

    def test_check_single_consumer(self):
        result = runner.invoke(app, [
            "check",
            "--config", str(GRAPH_FIXTURES / "pactwatch.yaml"),
            "--producer", "api",
            "--old", str(GRAPH_FIXTURES / "api_old.yaml"),
            "--new", str(GRAPH_FIXTURES / "api_new.yaml"),
            "--consumer", "mobile-app",
        ])
        assert "mobile-app" in result.output

    def test_check_json_format(self):
        result = runner.invoke(app, [
            "check",
            "--config", str(GRAPH_FIXTURES / "pactwatch.yaml"),
            "--producer", "api",
            "--old", str(GRAPH_FIXTURES / "api_old.yaml"),
            "--new", str(GRAPH_FIXTURES / "api_new.yaml"),
            "--format", "json",
        ])
        import json
        data = json.loads(result.output)
        assert data["producer"] == "api"
        assert "mobile-app" in data["consumers"]
        assert "web-dashboard" in data["consumers"]

    def test_check_exits_1_on_breaking(self):
        result = runner.invoke(app, [
            "check",
            "--config", str(GRAPH_FIXTURES / "pactwatch.yaml"),
            "--producer", "api",
            "--old", str(GRAPH_FIXTURES / "api_old.yaml"),
            "--new", str(GRAPH_FIXTURES / "api_new.yaml"),
        ])
        # email removal is breaking for consumers of GET /users/{id}
        assert result.exit_code == 1

    def test_check_unknown_producer_exits_2(self):
        result = runner.invoke(app, [
            "check",
            "--config", str(GRAPH_FIXTURES / "pactwatch.yaml"),
            "--producer", "nonexistent",
            "--old", str(GRAPH_FIXTURES / "api_old.yaml"),
            "--new", str(GRAPH_FIXTURES / "api_new.yaml"),
        ])
        assert result.exit_code == 2

    def test_check_unknown_consumer_exits_2(self):
        result = runner.invoke(app, [
            "check",
            "--config", str(GRAPH_FIXTURES / "pactwatch.yaml"),
            "--producer", "api",
            "--old", str(GRAPH_FIXTURES / "api_old.yaml"),
            "--new", str(GRAPH_FIXTURES / "api_new.yaml"),
            "--consumer", "nonexistent",
        ])
        assert result.exit_code == 2
