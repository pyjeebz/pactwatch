"""Tests for the consumer graph loader."""

from pathlib import Path

import pytest

from pactwatch.graph import (
    ConsumerGraph,
    GraphLoadError,
    endpoint_matches,
    load_graph,
)

GRAPH_FIXTURES = Path(__file__).parent / "fixtures" / "graph"


class TestLoadGraph:
    def test_loads_valid_config(self):
        graph = load_graph(GRAPH_FIXTURES / "pactwatch.yaml")
        assert "api" in graph.producers
        assert "payments" in graph.producers
        assert "mobile-app" in graph.consumers
        assert "web-dashboard" in graph.consumers

    def test_producer_spec_paths(self):
        graph = load_graph(GRAPH_FIXTURES / "pactwatch.yaml")
        assert graph.producers["api"].spec_path == Path("./api_old.yaml")

    def test_consumer_dependencies(self):
        graph = load_graph(GRAPH_FIXTURES / "pactwatch.yaml")
        mobile = graph.consumers["mobile-app"]
        assert len(mobile.consumes) == 2
        producer_names = {dep.producer for dep in mobile.consumes}
        assert producer_names == {"api", "payments"}

    def test_error_on_missing_file(self):
        with pytest.raises(GraphLoadError, match="not found"):
            load_graph(GRAPH_FIXTURES / "nonexistent.yaml")

    def test_error_on_invalid_consumer_ref(self):
        with pytest.raises(GraphLoadError, match="unknown producer"):
            load_graph(GRAPH_FIXTURES / "invalid_consumer_ref.yaml")


class TestConsumerGraph:
    @pytest.fixture
    def graph(self):
        return load_graph(GRAPH_FIXTURES / "pactwatch.yaml")

    def test_consumers_of_api(self, graph):
        consumers = graph.consumers_of("api")
        names = {c.name for c in consumers}
        assert names == {"mobile-app", "web-dashboard"}

    def test_consumers_of_payments(self, graph):
        consumers = graph.consumers_of("payments")
        names = {c.name for c in consumers}
        assert names == {"mobile-app"}

    def test_consumers_of_unknown(self, graph):
        consumers = graph.consumers_of("nonexistent")
        assert consumers == []

    def test_endpoints_for_mobile_api(self, graph):
        endpoints = graph.endpoints_for("mobile-app", "api")
        assert "GET /users/{id}" in endpoints
        assert "POST /orders" in endpoints

    def test_endpoints_for_web_api(self, graph):
        endpoints = graph.endpoints_for("web-dashboard", "api")
        assert "GET /users/{id}" in endpoints
        assert "GET /admin/settings" in endpoints

    def test_endpoints_for_unknown_consumer(self, graph):
        endpoints = graph.endpoints_for("nonexistent", "api")
        assert endpoints == set()

    def test_resolve_spec_path(self, graph):
        resolved = graph.resolve_spec_path("api")
        assert resolved == GRAPH_FIXTURES / "api_old.yaml"


class TestEndpointMatches:
    def test_exact_match(self):
        assert endpoint_matches("GET /users/{id}", "GET /users/{id}")

    def test_no_match_different_method(self):
        assert not endpoint_matches("POST /users/{id}", "GET /users/{id}")

    def test_no_match_different_path(self):
        assert not endpoint_matches("GET /users/{id}", "GET /orders")

    def test_glob_matches_one_segment(self):
        assert endpoint_matches("GET /admin/*", "GET /admin/settings")

    def test_glob_matches_deep_path(self):
        assert endpoint_matches("GET /admin/*", "GET /admin/users/123")

    def test_glob_no_match_different_prefix(self):
        assert not endpoint_matches("GET /admin/*", "GET /users/{id}")

    def test_glob_no_match_different_method(self):
        assert not endpoint_matches("POST /admin/*", "GET /admin/settings")
