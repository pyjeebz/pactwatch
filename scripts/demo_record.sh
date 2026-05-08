#!/usr/bin/env bash
# ============================================================
# Breakwatch — asciinema recording driver
#
# A paced, narrative walkthrough designed to be recorded with
# asciinema. Unlike demo_test.sh (functional integration test),
# this script simulates typing and pauses between scenes so the
# resulting recording reads like a deliberate demo.
#
# Recording (from repo root):
#   asciinema rec -c "scripts/demo_record.sh" demo.cast
#
# Convert to GIF (requires `agg`):
#   agg --theme monokai --font-size 16 demo.cast demo.gif
#
# Convert to MP4 (requires ffmpeg):
#   ffmpeg -i demo.gif -movflags faststart -pix_fmt yuv420p \
#     -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" demo.mp4
#
# Tweak pacing with env vars:
#   TYPE_DELAY=0.04  (per-char typing delay; 0 = instant)
#   PAUSE_SHORT=1    (between commands)
#   PAUSE_LONG=2.5   (after key results — "the magic moments")
#   FAST=1           (skip all pacing — use for dry runs)
# ============================================================

set -euo pipefail

# ---- Pacing configuration --------------------------------------------------
TYPE_DELAY="${TYPE_DELAY:-0.04}"
PAUSE_SHORT="${PAUSE_SHORT:-1.0}"
PAUSE_LONG="${PAUSE_LONG:-2.5}"
PAUSE_SCENE="${PAUSE_SCENE:-1.5}"

if [[ "${FAST:-}" == "1" ]]; then
  TYPE_DELAY=0
  PAUSE_SHORT=0
  PAUSE_LONG=0
  PAUSE_SCENE=0
fi

# ---- Demo paths ------------------------------------------------------------
DEMO="examples/demo-monorepo"
OLD="$DEMO/services/producer-api/openapi.yaml"
NEW="$DEMO/services/producer-api/openapi-breaking.yaml"
CONFIG="$DEMO/breakwatch.yaml"

# ---- Colors (ANSI; survive into the .cast recording) -----------------------
BOLD=$'\033[1m'
DIM=$'\033[2m'
CYAN=$'\033[36m'
PURPLE=$'\033[35m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
RESET=$'\033[0m'

# ---- Helpers ---------------------------------------------------------------

# Print a fake shell prompt + simulated typing of a command, then run it.
# The visible prompt mimics a clean PS1: "$ " in green.
type_cmd() {
  local cmd="$1"
  printf "%s$ %s" "$GREEN" "$RESET"
  if [[ "$TYPE_DELAY" == "0" ]]; then
    printf "%s\n" "$cmd"
  else
    local i
    for (( i=0; i<${#cmd}; i++ )); do
      printf "%s" "${cmd:$i:1}"
      sleep "$TYPE_DELAY"
    done
    printf "\n"
  fi
  sleep "$PAUSE_SHORT"
  eval "$cmd" || true
}

scene() {
  local title="$1"
  printf "\n%s%s── %s ──%s\n\n" "$BOLD" "$PURPLE" "$title" "$RESET"
  sleep "$PAUSE_SCENE"
}

note() {
  printf "%s# %s%s\n" "$DIM" "$1" "$RESET"
  sleep "$PAUSE_SHORT"
}

pause_long() { sleep "$PAUSE_LONG"; }

# ============================================================================
# Title card
# ============================================================================
clear
cat <<'BANNER'
   ╔══════════════════════════════════════════════════════════════╗
   ║                                                              ║
   ║    Breakwatch — see who breaks before you ship.              ║
   ║                                                              ║
   ║    OpenAPI breaking-change detector that knows which         ║
   ║    downstream consumers will actually break.                 ║
   ║                                                              ║
   ╚══════════════════════════════════════════════════════════════╝
BANNER
sleep "$PAUSE_LONG"

# ============================================================================
# Scene 1 — The setup
# ============================================================================
scene "1. The setup: a monorepo with one producer and two consumers"

note "Here's our config — it tells Breakwatch which endpoints each consumer uses."
type_cmd "cat $CONFIG"
pause_long

# ============================================================================
# Scene 2 — The naive diff
# ============================================================================
scene "2. A plain spec diff tells you WHAT changed…"

note "Compare the old spec to the new (breaking) spec."
type_cmd "breakwatch diff $OLD $NEW --format text"
pause_long

note "Useful — but it doesn't tell you who actually breaks."

# ============================================================================
# Scene 3 — The differentiator
# ============================================================================
scene "3. …but 'check' tells you WHO breaks."

type_cmd "breakwatch check --config $CONFIG --producer user-api --old $OLD --new $NEW --format text"
pause_long

note "Each consumer is scored against ONLY the endpoints they consume."

# ============================================================================
# Scene 4 — Drill down on one consumer
# ============================================================================
scene "4. Drill down on a single consumer"

type_cmd "breakwatch check --config $CONFIG --producer user-api --old $OLD --new $NEW --consumer mobile-app --format text"
pause_long

# ============================================================================
# Scene 5 — Markdown output (the CI use case)
# ============================================================================
scene "5. Markdown output — drop straight into a PR comment"

type_cmd "breakwatch check --config $CONFIG --producer user-api --old $OLD --new $NEW --format markdown"
pause_long

note "This is exactly what the GitHub Action posts on every pull request."

# ============================================================================
# Closing card
# ============================================================================
sleep "$PAUSE_SCENE"
clear
cat <<'CLOSING'
   ╔══════════════════════════════════════════════════════════════╗
   ║                                                              ║
   ║    Ship breaking changes with confidence.                    ║
   ║                                                              ║
   ║    pip install breakwatch                                    ║
   ║    github.com/pyjeebz/breakwatch                             ║
   ║    GitHub Marketplace: pyjeebz/breakwatch@v0.1.1             ║
   ║                                                              ║
   ╚══════════════════════════════════════════════════════════════╝
CLOSING
sleep "$PAUSE_LONG"
