#!/usr/bin/env bash
#
# run_demo.sh — Institutional Memory Agent, end to end.
#
# Provisions a fresh agent + memory store, then runs all three sessions:
#   1. baseline (round1 docs)            -> writes memory
#   2. update   (round2 docs contradict) -> reconciles + updates memory
#   3. "what have you learned?" (no docs) -> answers purely from memory
# Finally dumps the memory store so you can see what it remembered.
#
# Usage:
#   ./run_demo.sh
#
set -euo pipefail

# Always run from the script's own directory.
cd "$(dirname "$0")"

# Prefer the project venv if it exists; fall back to whatever `python` is on PATH.
if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python"
fi

# Load ANTHROPIC_API_KEY from .env (the session scripts don't read .env themselves).
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set. Put it in .env or export it." >&2
  exit 1
fi

step() { printf '\n========================================\n%s\n========================================\n' "$1"; }

step "0/4  Provisioning agent + environment + fresh memory store"
"$PYTHON" create_agent.py

step "1/4  Session 1 — baseline (round1 docs)"
"$PYTHON" run_session_1.py

step "2/4  Session 2 — update (round2 docs contradict round1)"
"$PYTHON" run_session_2.py

step "3/4  Session 3 — 'what have you learned?' (no docs, memory only)"
"$PYTHON" run_session_3.py

step "4/4  Final memory store contents"
"$PYTHON" inspect_memory.py --full

step "Done. Compare the answers:"
echo "  cat outputs/session1.txt outputs/session2.txt outputs/session3.txt"
