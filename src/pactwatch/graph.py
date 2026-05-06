"""Consumer graph — load and query pactwatch.yaml."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class GraphLoadError(Exception):
    """Raised when a pactwatch.yaml file cannot be loaded or is invalid."""


@dataclass
class Producer:
    """A service that owns an OpenAPI spec."""
    name: str
    spec_path: Path


@dataclass
class ConsumerDependency:
    """A single producer dependency declared by a consumer."""
    producer: str
    endpoints: list[str]


@dataclass
class Consumer:
    """A service that consumes one or more producer APIs."""
    name: str
    consumes: list[ConsumerDependency]


@dataclass
class ConsumerGraph:
    """The full service-to-consumer graph parsed from pactwatch.yaml."""
    producers: dict[str, Producer] = field(default_factory=dict)
    consumers: dict[str, Consumer] = field(default_factory=dict)
    _config_dir: Path = field(default_factory=lambda: Path("."))

    def consumers_of(self, producer: str) -> list[Consumer]:
        """Return all consumers that depend on the given producer."""
        return [
            c for c in self.consumers.values()
            if any(dep.producer == producer for dep in c.consumes)
        ]

    def endpoints_for(self, consumer_name: str, producer: str) -> set[str]:
        """Return the set of endpoint patterns a consumer uses from a producer."""
        consumer = self.consumers.get(consumer_name)
        if not consumer:
            return set()
        for dep in consumer.consumes:
            if dep.producer == producer:
                return set(dep.endpoints)
        return set()

    def resolve_spec_path(self, producer: str) -> Path:
        """Resolve a producer's spec path relative to the config file directory."""
        p = self.producers.get(producer)
        if not p:
            raise GraphLoadError(f"Unknown producer: {producer!r}")
        return self._config_dir / p.spec_path


def load_graph(path: Path | str) -> ConsumerGraph:
    """Load and validate a pactwatch.yaml consumer graph config.

    Args:
        path: Path to the pactwatch.yaml file.

    Returns:
        A validated ConsumerGraph.

    Raises:
        GraphLoadError: If the file is missing, malformed, or references are invalid.
    """
    path = Path(path)

    if not path.exists():
        raise GraphLoadError(f"Config file not found: {path}")

    if not path.is_file():
        raise GraphLoadError(f"Not a file: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise GraphLoadError(f"Failed to parse config: {exc}") from exc

    if not isinstance(raw, dict):
        raise GraphLoadError("Config must be a YAML mapping")

    # Version check
    version = raw.get("version")
    if version != 1:
        raise GraphLoadError(
            f"Unsupported config version: {version!r}. Expected 1."
        )

    # Parse producers
    raw_producers = raw.get("producers", {})
    if not isinstance(raw_producers, dict):
        raise GraphLoadError("'producers' must be a mapping")

    producers: dict[str, Producer] = {}
    for name, config in raw_producers.items():
        if not isinstance(config, dict) or "spec" not in config:
            raise GraphLoadError(
                f"Producer '{name}' must have a 'spec' field"
            )
        producers[name] = Producer(
            name=name,
            spec_path=Path(config["spec"]),
        )

    # Parse consumers
    raw_consumers = raw.get("consumers", {})
    if not isinstance(raw_consumers, dict):
        raise GraphLoadError("'consumers' must be a mapping")

    consumers: dict[str, Consumer] = {}
    for name, config in raw_consumers.items():
        if not isinstance(config, dict) or "consumes" not in config:
            raise GraphLoadError(
                f"Consumer '{name}' must have a 'consumes' field"
            )

        deps: list[ConsumerDependency] = []
        for dep_raw in config["consumes"]:
            if not isinstance(dep_raw, dict):
                raise GraphLoadError(
                    f"Consumer '{name}': each dependency must be a mapping"
                )

            producer_ref = dep_raw.get("producer")
            if not producer_ref:
                raise GraphLoadError(
                    f"Consumer '{name}': dependency missing 'producer' field"
                )

            if producer_ref not in producers:
                raise GraphLoadError(
                    f"Consumer '{name}' references unknown producer: "
                    f"{producer_ref!r}"
                )

            endpoints = dep_raw.get("endpoints", [])
            if not isinstance(endpoints, list):
                raise GraphLoadError(
                    f"Consumer '{name}': 'endpoints' must be a list"
                )

            deps.append(ConsumerDependency(
                producer=producer_ref,
                endpoints=endpoints,
            ))

        consumers[name] = Consumer(name=name, consumes=deps)

    return ConsumerGraph(
        producers=producers,
        consumers=consumers,
        _config_dir=path.parent,
    )


def endpoint_matches(pattern: str, endpoint: str) -> bool:
    """Check if an endpoint matches a consumer's endpoint pattern.

    Supports exact match and greedy glob with *.
    'GET /admin/*' matches 'GET /admin/users' and 'GET /admin/users/123'.

    Args:
        pattern: The pattern from the consumer config (e.g. 'GET /admin/*').
        endpoint: The actual endpoint (e.g. 'GET /admin/users/123').

    Returns:
        True if the endpoint matches the pattern.
    """
    # Exact match (fast path)
    if pattern == endpoint:
        return True

    # Split into method + path
    pattern_parts = pattern.split(" ", 1)
    endpoint_parts = endpoint.split(" ", 1)

    if len(pattern_parts) != 2 or len(endpoint_parts) != 2:
        return False

    pattern_method, pattern_path = pattern_parts
    endpoint_method, endpoint_path = endpoint_parts

    # Methods must match
    if pattern_method.upper() != endpoint_method.upper():
        return False

    # Use fnmatch for glob — but fnmatch treats * as single-segment by default,
    # so we convert /admin/* to /admin/** behavior by using a custom check.
    if "*" in pattern_path:
        # Greedy: /admin/* matches /admin/anything/at/any/depth
        prefix = pattern_path.split("*")[0]
        return endpoint_path.startswith(prefix)

    return pattern_path == endpoint_path
