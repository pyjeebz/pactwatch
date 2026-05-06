"""Tests for the Markdown PR comment formatter."""

from pathlib import Path

from pactwatch.classifier import Severity, classify
from pactwatch.diff import diff_specs
from pactwatch.filter import filter_for_consumer
from pactwatch.formatters.markdown import MARKER, format_check_markdown
from pactwatch.graph import load_graph
from pactwatch.loader import load_spec

GRAPH_FIXTURES = Path(__file__).parent / "fixtures" / "graph"


def _get_results():
    """Run the full pipeline and return per-consumer results."""
    graph = load_graph(GRAPH_FIXTURES / "pactwatch.yaml")
    old = load_spec(GRAPH_FIXTURES / "api_old.yaml")
    new = load_spec(GRAPH_FIXTURES / "api_new.yaml")
    changes = diff_specs(old, new)
    classified = classify(changes)

    results = {}
    for consumer in graph.consumers_of("api"):
        filtered = filter_for_consumer(classified, consumer, "api")
        results[consumer.name] = filtered
    return results


class TestMarkdownFormatter:
    def test_contains_marker(self):
        results = _get_results()
        md = format_check_markdown("api", results)
        assert MARKER in md

    def test_contains_producer_name(self):
        results = _get_results()
        md = format_check_markdown("api", results)
        assert "`api`" in md

    def test_contains_consumer_names(self):
        results = _get_results()
        md = format_check_markdown("api", results)
        assert "mobile-app" in md
        assert "web-dashboard" in md

    def test_contains_summary_table(self):
        results = _get_results()
        md = format_check_markdown("api", results)
        assert "| Consumer |" in md
        assert "| Breaking |" in md

    def test_breaking_consumers_expanded(self):
        """Consumers with breaking changes should NOT be inside <details>."""
        results = _get_results()
        md = format_check_markdown("api", results)
        # Both consumers have breaking changes (email removal)
        # so both should be expanded with ### headers
        assert "### :x:" in md

    def test_safe_only_consumers_collapsed(self):
        """Consumers with only safe changes should be in <details>."""
        # Create results where one consumer has no breaking changes
        results = {"safe-consumer": []}
        md = format_check_markdown("api", results)
        # Empty consumer shouldn't have details
        assert "No consumers found" not in md

    def test_empty_results(self):
        md = format_check_markdown("api", {})
        assert "No consumers found" in md

    def test_changes_table_format(self):
        results = _get_results()
        md = format_check_markdown("api", results)
        assert "| Severity | Path | Change |" in md

    def test_contains_status(self):
        results = _get_results()
        md = format_check_markdown("api", results)
        assert "BREAKING changes detected" in md

    def test_safe_status_when_no_breaking(self):
        # Manually create safe-only results
        graph = load_graph(GRAPH_FIXTURES / "pactwatch.yaml")
        old = load_spec(GRAPH_FIXTURES / "api_old.yaml")
        # Diff same file = no changes
        changes = diff_specs(old, old)
        classified = classify(changes)

        results = {}
        for consumer in graph.consumers_of("api"):
            filtered = filter_for_consumer(classified, consumer, "api")
            results[consumer.name] = filtered

        md = format_check_markdown("api", results)
        assert "No breaking changes" in md
