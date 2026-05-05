# PactWatch

> Your microservices have a contract. PactWatch enforces it before merge.

An OpenAPI breaking-change detector that knows which downstream consumers will actually break.

## Installation

```bash
pip install pactwatch
```

## Quick Start

```bash
# Compare two OpenAPI specs
pactwatch diff old-spec.yaml new-spec.yaml

# JSON output for CI
pactwatch diff old-spec.yaml new-spec.yaml --format json
```

## License

Apache 2.0
