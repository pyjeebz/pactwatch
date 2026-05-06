"""Tests for per-consumer filtering."""

from pathlib import Path

from pactwatch.classifier import Severity, classify
from pactwatch.diff import diff_specs
from pactwatch.filter import filter_for_consumer
from pactwatch.graph import load_graph
from pactwatch.loader import load_spec

GRAPH_FIXTURES = Path(__file__).parent / "fixtures" / "graph"


def _load_and_classify(old_path: str, new_path: str):
    old = load_spec(GRAPH_FIXTURES / old_path)
    new = load_spec(GRAPH_FIXTURES / new_path)
    changes = diff_specs(old, new)
    return classify(changes)


class TestFilterForConsumer:
    """Test filtering with the api producer specs."""

    def setup_method(self):
        self.graph = load_graph(GRAPH_FIXTURES / "pactwatch.yaml")
        self.classified = _load_and_classify("api_old.yaml", "api_new.yaml")

    def test_mobile_app_gets_relevant_changes(self):
        """mobile-app uses GET /users/{id} and POST /orders."""
        mobile = self.graph.consumers["mobile-app"]
        filtered = filter_for_consumer(self.classified, mobile, "api")

        paths = {c.path for c in filtered}
        # Should include changes to GET /users/{id} and POST /orders
        assert "GET /users/{id}" in paths

    def test_mobile_app_excludes_irrelevant_changes(self):
        """mobile-app does NOT use DELETE /users/{id} or GET /admin/settings."""
        mobile = self.graph.consumers["mobile-app"]
        filtered = filter_for_consumer(self.classified, mobile, "api")

        paths = {c.path for c in filtered}
        # DELETE /users was removed, but mobile-app doesn't use it
        assert "DELETE /users/{id}" not in paths
        # /internal/metrics changes shouldn't appear
        assert "GET /internal/metrics" not in paths

    def test_web_dashboard_gets_relevant_changes(self):
        """web-dashboard uses GET /users/{id} and GET /admin/settings."""
        web = self.graph.consumers["web-dashboard"]
        filtered = filter_for_consumer(self.classified, web, "api")

        paths = {c.path for c in filtered}
        assert "GET /users/{id}" in paths

    def test_web_dashboard_excludes_orders(self):
        """web-dashboard does NOT use POST /orders."""
        web = self.graph.consumers["web-dashboard"]
        filtered = filter_for_consumer(self.classified, web, "api")

        paths = {c.path for c in filtered}
        assert "POST /orders" not in paths

    def test_mobile_sees_breaking_on_users(self):
        """email field removed from GET /users response -- breaking for mobile."""
        mobile = self.graph.consumers["mobile-app"]
        filtered = filter_for_consumer(self.classified, mobile, "api")

        breaking = [c for c in filtered if c.severity == Severity.BREAKING]
        assert len(breaking) >= 1
        # Should have the email removal
        messages = " ".join(c.message for c in breaking)
        assert "email" in messages

    def test_empty_for_no_matching_producer(self):
        """If consumer doesn't use this producer, return empty."""
        web = self.graph.consumers["web-dashboard"]
        # web-dashboard doesn't consume payments
        filtered = filter_for_consumer(self.classified, web, "payments")
        assert filtered == []


class TestFilterPayments:
    """Test filtering with the payments producer specs."""

    def test_mobile_sees_breaking_payment_change(self):
        graph = load_graph(GRAPH_FIXTURES / "pactwatch.yaml")
        classified = _load_and_classify("payments_old.yaml", "payments_new.yaml")

        mobile = graph.consumers["mobile-app"]
        filtered = filter_for_consumer(classified, mobile, "payments")

        breaking = [c for c in filtered if c.severity == Severity.BREAKING]
        assert len(breaking) >= 1
        messages = " ".join(c.message for c in breaking)
        assert "idempotency_key" in messages


class TestFilterGlob:
    """Test glob matching in consumer endpoint patterns."""

    def test_glob_matches_admin_endpoints(self):
        graph = load_graph(GRAPH_FIXTURES / "pactwatch_glob.yaml")
        classified = _load_and_classify("api_old.yaml", "api_new.yaml")

        admin = graph.consumers["admin-dashboard"]
        filtered = filter_for_consumer(classified, admin, "api")

        paths = {c.path for c in filtered}
        # GET /admin/* should match changes to GET /admin/settings
        assert "GET /admin/settings" in paths
        # Should NOT match non-admin endpoints
        assert "GET /users/{id}" not in paths
        assert "POST /orders" not in paths
