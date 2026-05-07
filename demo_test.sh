#!/usr/bin/env bash
# ============================================================
# PactWatch Demo Test Script
# Exercises both CLI commands against the demo-monorepo fixtures
# ============================================================

set -euo pipefail

DEMO="examples/demo-monorepo"
OLD="$DEMO/services/producer-api/openapi.yaml"
NEW="$DEMO/services/producer-api/openapi-breaking.yaml"
CONFIG="$DEMO/pactwatch.yaml"

echo "============================================"
echo "  PactWatch — Demo Test Script"
echo "============================================"
echo

# ----------------------------------------------------------
# 1. Run the unit / integration test suite
# ----------------------------------------------------------
echo ">>> 1. Running pytest suite..."
echo "--------------------------------------------"
python -m pytest tests/ -v --tb=short
echo
echo "All tests passed."
echo

# ----------------------------------------------------------
# 2. pactwatch diff  (text output)
# ----------------------------------------------------------
echo ">>> 2. pactwatch diff (text format)"
echo "--------------------------------------------"
pactwatch diff "$OLD" "$NEW" --format text || true
echo

# ----------------------------------------------------------
# 3. pactwatch diff  (JSON output)
# ----------------------------------------------------------
echo ">>> 3. pactwatch diff (JSON format)"
echo "--------------------------------------------"
pactwatch diff "$OLD" "$NEW" --format json || true
echo

# ----------------------------------------------------------
# 4. pactwatch check — all consumers (text)
# ----------------------------------------------------------
echo ">>> 4. pactwatch check — all consumers (text)"
echo "--------------------------------------------"
pactwatch check \
  --config "$CONFIG" \
  --producer user-api \
  --old "$OLD" \
  --new "$NEW" \
  --format text || true
echo

# ----------------------------------------------------------
# 5. pactwatch check — single consumer (mobile-app)
# ----------------------------------------------------------
echo ">>> 5. pactwatch check — single consumer: mobile-app"
echo "--------------------------------------------"
pactwatch check \
  --config "$CONFIG" \
  --producer user-api \
  --old "$OLD" \
  --new "$NEW" \
  --consumer mobile-app \
  --format text || true
echo

# ----------------------------------------------------------
# 6. pactwatch check — single consumer (web-dashboard)
# ----------------------------------------------------------
echo ">>> 6. pactwatch check — single consumer: web-dashboard"
echo "--------------------------------------------"
pactwatch check \
  --config "$CONFIG" \
  --producer user-api \
  --old "$OLD" \
  --new "$NEW" \
  --consumer web-dashboard \
  --format text || true
echo

# ----------------------------------------------------------
# 7. pactwatch check — JSON output
# ----------------------------------------------------------
echo ">>> 7. pactwatch check — all consumers (JSON)"
echo "--------------------------------------------"
pactwatch check \
  --config "$CONFIG" \
  --producer user-api \
  --old "$OLD" \
  --new "$NEW" \
  --format json || true
echo

echo "============================================"
echo "  Demo complete."
echo "============================================"
