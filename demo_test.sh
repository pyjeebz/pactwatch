#!/usr/bin/env bash
# ============================================================
# Breakwatch Demo Test Script
# Exercises both CLI commands against the demo-monorepo fixtures
# ============================================================

set -euo pipefail

DEMO="examples/demo-monorepo"
OLD="$DEMO/services/producer-api/openapi.yaml"
NEW="$DEMO/services/producer-api/openapi-breaking.yaml"
CONFIG="$DEMO/breakwatch.yaml"

echo "============================================"
echo "  Breakwatch — Demo Test Script"
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
# 2. breakwatch diff  (text output)
# ----------------------------------------------------------
echo ">>> 2. breakwatch diff (text format)"
echo "--------------------------------------------"
breakwatch diff "$OLD" "$NEW" --format text || true
echo

# ----------------------------------------------------------
# 3. breakwatch diff  (JSON output)
# ----------------------------------------------------------
echo ">>> 3. breakwatch diff (JSON format)"
echo "--------------------------------------------"
breakwatch diff "$OLD" "$NEW" --format json || true
echo

# ----------------------------------------------------------
# 4. breakwatch check — all consumers (text)
# ----------------------------------------------------------
echo ">>> 4. breakwatch check — all consumers (text)"
echo "--------------------------------------------"
breakwatch check \
  --config "$CONFIG" \
  --producer user-api \
  --old "$OLD" \
  --new "$NEW" \
  --format text || true
echo

# ----------------------------------------------------------
# 5. breakwatch check — single consumer (mobile-app)
# ----------------------------------------------------------
echo ">>> 5. breakwatch check — single consumer: mobile-app"
echo "--------------------------------------------"
breakwatch check \
  --config "$CONFIG" \
  --producer user-api \
  --old "$OLD" \
  --new "$NEW" \
  --consumer mobile-app \
  --format text || true
echo

# ----------------------------------------------------------
# 6. breakwatch check — single consumer (web-dashboard)
# ----------------------------------------------------------
echo ">>> 6. breakwatch check — single consumer: web-dashboard"
echo "--------------------------------------------"
breakwatch check \
  --config "$CONFIG" \
  --producer user-api \
  --old "$OLD" \
  --new "$NEW" \
  --consumer web-dashboard \
  --format text || true
echo

# ----------------------------------------------------------
# 7. breakwatch check — JSON output
# ----------------------------------------------------------
echo ">>> 7. breakwatch check — all consumers (JSON)"
echo "--------------------------------------------"
breakwatch check \
  --config "$CONFIG" \
  --producer user-api \
  --old "$OLD" \
  --new "$NEW" \
  --format json || true
echo

echo "============================================"
echo "  Demo complete."
echo "============================================"
