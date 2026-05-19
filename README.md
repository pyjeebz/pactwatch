# Breakwatch
> Your microservices have a contract. Breakwatch enforces it before merge.

An OpenAPI breaking-change detector that knows which downstream consumers will actually break. Most API diff tools tell you *what* changed. Breakwatch tells you *who cares*.

## Demo

![Breakwatch demo](demo.gif)

<sub>Also available as [MP4](demo.mp4) for sharing.</sub>

## The Problem

Team A changes their API. Team B's mobile app breaks in production. The spec diff showed "field removed" — but nobody connected it to Team B.

Breakwatch maintains a service-to-consumer graph (`breakwatch.yaml`). When a producer's spec changes, it classifies each change as **BREAKING**, **RISKY**, or **SAFE**, then filters the results per consumer. Same spec change, different verdict per team.

## How It Works

```
1. Diff    — structurally compare two OpenAPI 3.x specs
2. Classify — label each change: BREAKING / RISKY / SAFE
3. Filter  — check the consumer graph: who uses the affected endpoints?
```

## Installation

```bash
pip install breakwatch
```

## Quick Start

### Raw diff

Compare two specs and get classified changes:

```bash
# Rich terminal output
breakwatch diff old-spec.yaml new-spec.yaml

# JSON for CI
breakwatch diff old-spec.yaml new-spec.yaml --format json
```

### Per-consumer impact

Define your service topology in `breakwatch.yaml`:

```yaml
version: 1
producers:
  api:
    spec: ./services/api/openapi.yaml

consumers:
  mobile-app:
    consumes:
      - producer: api
        endpoints:
          - GET /users/{id}
          - POST /orders
  web-dashboard:
    consumes:
      - producer: api
        endpoints:
          - GET /users/{id}
          - GET /admin/*
```

Then check per-consumer impact:

```bash
# Check all consumers
breakwatch check -c breakwatch.yaml -p api --old old.yaml --new new.yaml

# Check a single consumer
breakwatch check -c breakwatch.yaml -p api --old old.yaml --new new.yaml --consumer mobile-app

# JSON for CI
breakwatch check -c breakwatch.yaml -p api --old old.yaml --new new.yaml -f json
```

### GitHub Action

Add to your workflow:

```yaml
name: API Contract Check
on: pull_request

jobs:
  breakwatch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: pyjeebz/breakwatch@v0.1.0
        with:
          config: breakwatch.yaml
          producer: api
          old-spec: services/api/openapi.yaml  # from base branch
          new-spec: services/api/openapi.yaml  # from PR branch
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

Breakwatch will:
- Post a PR comment showing per-consumer impact
- Set a commit status check (pass/fail)
- Exit with code 1 if breaking changes affect any consumer

## Classification Rules

### Breaking
| Change | Why |
|--------|-----|
| Endpoint removed | Consumers calling it will get 404s |
| Required response field removed | Consumers parsing it will crash |
| Response field type changed | Consumers deserializing it will get wrong types |
| New required request field | Existing client code won't send it |
| Status code removed | Consumers handling it will get unexpected responses |
| Auth scheme changed | Existing tokens/keys will stop working |

### Risky
| Change | Why |
|--------|-----|
| Optional field made required | Consumers not sending it may start failing |
| Field made nullable | Consumers not handling null may crash |
| Enum value removed | Consumers matching on it will miss cases |

### Safe
| Change | Why |
|--------|-----|
| New endpoint | Existing consumers unaffected |
| New optional request field | Old clients just don't send it |
| New response field | Old clients ignore extra fields |
| New enum value | Old clients still see their known values |
| Documentation changes | No runtime impact |

## CLI Reference

### `breakwatch diff`

```
breakwatch diff OLD NEW [--format text|json]
```

Compare two OpenAPI specs. Exits with code 1 if BREAKING changes found.

### `breakwatch check`

```
breakwatch check --config PATH --producer NAME --old PATH --new PATH
                [--consumer NAME] [--format text|json]
```

Check per-consumer impact using the consumer graph. Exits with code 1 if any consumer has BREAKING changes.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No breaking changes |
| 1 | Breaking changes detected |
| 2 | Input error (bad spec, bad config, unknown producer) |


See the [demo monorepo](examples/demo-monorepo/) for a working example with 3 services.

```bash
# Run the demo
breakwatch check \
  -c examples/demo-monorepo/breakwatch.yaml \
  -p user-api \
  --old examples/demo-monorepo/services/producer-api/openapi.yaml \
  --new examples/demo-monorepo/services/producer-api/openapi-breaking.yaml
```

## License

Apache 2.0
