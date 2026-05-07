# Breakwatch — Production Usage Guide

> How to use Breakwatch with real APIs in a real codebase.

---

## Prerequisites

- Python 3.11+
- Your API specs are already in OpenAPI 3.x format (YAML or JSON)
- Your specs live in version control (git)

```bash
pip install breakwatch
```

---

## Step 1: Understand your service topology

Before writing any config, map out your services:

- **Who produces APIs?** (backend services that own OpenAPI specs)
- **Who consumes them?** (frontends, mobile apps, other services)
- **Which endpoints does each consumer actually call?**

Example: you have an `orders-api` that three services depend on:

```
checkout-service  --> POST /orders, GET /orders/{id}
mobile-app        --> GET /orders/{id}, GET /orders/{id}/tracking
admin-dashboard   --> GET /orders, PUT /orders/{id}/status, DELETE /orders/{id}
```

If you don't know which endpoints each consumer uses, check:
- API gateway logs (which paths does each client hit?)
- Client SDKs (what endpoints do the generated clients call?)
- Frontend/mobile code (grep for API paths)

---

## Step 2: Write your `breakwatch.yaml`

Create this file in your repo root (or wherever makes sense):

```yaml
version: 1

producers:
  orders-api:
    spec: ./services/orders-api/openapi.yaml
  users-api:
    spec: ./services/users-api/openapi.yaml

consumers:
  checkout-service:
    consumes:
      - producer: orders-api
        endpoints:
          - POST /orders
          - GET /orders/{id}

  mobile-app:
    consumes:
      - producer: orders-api
        endpoints:
          - GET /orders/{id}
          - GET /orders/{id}/tracking
      - producer: users-api
        endpoints:
          - GET /users/{id}
          - POST /users

  admin-dashboard:
    consumes:
      - producer: orders-api
        endpoints:
          - GET /orders
          - PUT /orders/{id}/status
          - DELETE /orders/{id}
      - producer: users-api
        endpoints:
          - GET /users
          - GET /admin/*
```

### Tips for writing endpoints

- Use the exact method + path from your OpenAPI spec: `GET /users/{id}`
- Path parameters stay as-is: `{id}`, `{orderId}`, etc.
- Use wildcards for prefix matching: `GET /admin/*` matches everything under `/admin/`
- You don't need to list every endpoint — just the ones each consumer actually uses

### Where to put the file

- **Monorepo**: repo root, next to your services
- **Multi-repo**: in a shared config repo, or in the producer's repo
- **Per-team**: each team can maintain their own consumer declarations

---

## Step 3: Run Breakwatch locally

### Quick diff (no graph)

Compare any two versions of a spec:

```bash
# Compare current spec to a modified version
breakwatch diff openapi.yaml openapi-new.yaml

# Compare current branch to main
git show main:services/orders-api/openapi.yaml > /tmp/old-spec.yaml
breakwatch diff /tmp/old-spec.yaml services/orders-api/openapi.yaml

# JSON output for scripting
breakwatch diff old.yaml new.yaml --format json
```

### Per-consumer impact check

```bash
# Check all consumers of a producer
breakwatch check \
  --config breakwatch.yaml \
  --producer orders-api \
  --old /tmp/old-spec.yaml \
  --new services/orders-api/openapi.yaml

# Check a single consumer
breakwatch check \
  --config breakwatch.yaml \
  --producer orders-api \
  --consumer mobile-app \
  --old /tmp/old-spec.yaml \
  --new services/orders-api/openapi.yaml

# JSON for CI pipelines
breakwatch check \
  --config breakwatch.yaml \
  --producer orders-api \
  --old /tmp/old-spec.yaml \
  --new services/orders-api/openapi.yaml \
  --format json
```

---

## Step 4: Add to CI

### Option A: GitHub Action (recommended)

Add to `.github/workflows/breakwatch.yml`:

```yaml
name: API Contract Check
on:
  pull_request:
    paths:
      - 'services/orders-api/openapi.yaml'
      - 'services/users-api/openapi.yaml'

jobs:
  breakwatch:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout PR branch
        uses: actions/checkout@v4

      - name: Get base branch spec
        run: |
          git fetch origin ${{ github.base_ref }}
          git show origin/${{ github.base_ref }}:services/orders-api/openapi.yaml > /tmp/old-spec.yaml

      - name: Run Breakwatch
        uses: pyjeebz/breakwatch@v1
        with:
          config: breakwatch.yaml
          producer: orders-api
          old-spec: /tmp/old-spec.yaml
          new-spec: services/orders-api/openapi.yaml
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

This will:
- Run on every PR that modifies an OpenAPI spec
- Post a comment on the PR showing per-consumer impact
- Block merge if breaking changes affect any consumer

### Option B: Generic CI (GitLab, CircleCI, Jenkins, etc.)

```bash
pip install breakwatch

# Get the old spec from the base branch
git show origin/main:services/orders-api/openapi.yaml > /tmp/old-spec.yaml

# Run check — exits 1 if breaking
breakwatch check \
  --config breakwatch.yaml \
  --producer orders-api \
  --old /tmp/old-spec.yaml \
  --new services/orders-api/openapi.yaml \
  --format json

# The exit code does the work:
# 0 = no breaking changes (CI passes)
# 1 = breaking changes (CI fails)
# 2 = config/spec error
```

### Multiple producers in one pipeline

If you have multiple API specs that could change in one PR:

```yaml
jobs:
  breakwatch-orders:
    runs-on: ubuntu-latest
    steps:
      # ... checkout + fetch base ...
      - uses: pyjeebz/breakwatch@v1
        with:
          config: breakwatch.yaml
          producer: orders-api
          old-spec: /tmp/orders-old.yaml
          new-spec: services/orders-api/openapi.yaml

  breakwatch-users:
    runs-on: ubuntu-latest
    steps:
      # ... checkout + fetch base ...
      - uses: pyjeebz/breakwatch@v1
        with:
          config: breakwatch.yaml
          producer: users-api
          old-spec: /tmp/users-old.yaml
          new-spec: services/users-api/openapi.yaml
```

---

## Step 5: Maintain the graph

The `breakwatch.yaml` file needs to stay current as your services evolve:

### When to update

- **New consumer added**: add a `consumers` entry with the endpoints they use
- **Consumer starts using a new endpoint**: add it to their `endpoints` list
- **Consumer stops using an endpoint**: remove it from their list
- **New producer added**: add a `producers` entry with the spec path
- **Service decommissioned**: remove the consumer/producer entry

### Who owns it

- **Option 1: centralized** — one team (platform/infra) maintains the whole file
- **Option 2: distributed** — each team adds their own consumer entry via PR
- **Option 3: generated** — extract endpoint usage from API gateway logs or client code (advanced)

### Validation

Breakwatch validates the config on every run:
- References to unknown producers are caught immediately
- Missing required fields produce clear error messages
- You can validate the config without running a diff:

```bash
python -c "from breakwatch.graph import load_graph; load_graph('breakwatch.yaml'); print('valid')"
```

---

## Real-world examples

### Example 1: Stripe-style API versioning

If your API is versioned and you publish OpenAPI specs per version:

```bash
# Compare v2024-01 to v2024-06
breakwatch diff specs/v2024-01.yaml specs/v2024-06.yaml
```

### Example 2: Monorepo with shared specs

```
monorepo/
  breakwatch.yaml
  services/
    user-api/openapi.yaml
    billing-api/openapi.yaml
    notification-api/openapi.yaml
  apps/
    web/         # consumes user-api, billing-api
    mobile/      # consumes user-api
    admin/       # consumes all three
```

```yaml
version: 1
producers:
  user-api:
    spec: ./services/user-api/openapi.yaml
  billing-api:
    spec: ./services/billing-api/openapi.yaml
  notification-api:
    spec: ./services/notification-api/openapi.yaml

consumers:
  web:
    consumes:
      - producer: user-api
        endpoints:
          - GET /users/{id}
          - PUT /users/{id}
      - producer: billing-api
        endpoints:
          - GET /invoices
          - POST /payments

  mobile:
    consumes:
      - producer: user-api
        endpoints:
          - GET /users/{id}

  admin:
    consumes:
      - producer: user-api
        endpoints:
          - GET /users
          - GET /users/{id}
          - DELETE /users/{id}
      - producer: billing-api
        endpoints:
          - GET /invoices
          - GET /invoices/{id}
          - POST /refunds
      - producer: notification-api
        endpoints:
          - GET /templates
          - POST /send
```

### Example 3: Multi-repo setup

If each service is in its own repo, put `breakwatch.yaml` in the producer repo and have consumers declare their dependencies there:

```yaml
# In the user-api repo
version: 1
producers:
  user-api:
    spec: ./openapi.yaml

consumers:
  # these are external services — they told us what they use
  mobile-app:
    consumes:
      - producer: user-api
        endpoints:
          - GET /users/{id}
          - POST /users
  payment-service:
    consumes:
      - producer: user-api
        endpoints:
          - GET /users/{id}/billing
```

---

## Understanding the output

### Exit codes

| Code | Meaning | CI result |
|------|---------|-----------|
| 0 | No breaking changes for any consumer | Pass |
| 1 | Breaking changes detected | Fail |
| 2 | Config or spec error | Error |

### Severity labels

| Label | What it means | Should you block merge? |
|-------|---------------|------------------------|
| **BREAKING** | Will cause consumer code to fail without updates | Yes |
| **RISKY** | Might cause issues depending on how consumers implemented | Review carefully |
| **SAFE** | Backwards compatible, no consumer impact | No |

### Reading the JSON output

```json
{
  "producer": "orders-api",
  "consumers": {
    "mobile-app": {
      "summary": { "breaking": 0, "risky": 0, "safe": 1 },
      "changes": [
        {
          "severity": "SAFE",
          "message": "New optional request field 'note' added to POST /orders",
          "path": "POST /orders",
          "detail": { ... }
        }
      ]
    },
    "checkout-service": {
      "summary": { "breaking": 1, "risky": 0, "safe": 0 },
      "changes": [
        {
          "severity": "BREAKING",
          "message": "Removed required response field 'tracking_url' from GET /orders/{id}",
          "path": "GET /orders/{id}",
          "detail": { ... }
        }
      ]
    }
  }
}
```

---

## Troubleshooting

### "Unsupported OpenAPI version"
Breakwatch requires OpenAPI 3.x. If your specs are Swagger 2.0, convert them first:
```bash
npx swagger2openapi your-spec.yaml > openapi3-spec.yaml
```

### "$ref resolution errors"
Breakwatch resolves all `$ref` pointers automatically. If you get resolution errors, check that:
- All referenced files exist at the relative paths
- No circular `$ref` chains exist
- External URLs in `$ref` are accessible

### "Unknown producer" error
The producer name in `breakwatch check --producer X` must match a key in `breakwatch.yaml`'s `producers` section. Check for typos.

### Consumer sees no changes
If a consumer's endpoint list doesn't match the endpoints that changed, they'll see an empty report. This is correct — those changes don't affect them. Double-check the endpoint patterns in `breakwatch.yaml` match your actual API paths.
