#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"
if [[ -f "$OPENCLAW_HOME/.env" ]]; then
  # shellcheck disable=SC1090
  source "$OPENCLAW_HOME/.env"
fi

SESSION="${OPENCLAW_SESSION_NAME:-openclaw}"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "up"
  exit 0
fi
echo "down"
exit 1
