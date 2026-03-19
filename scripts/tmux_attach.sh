#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"
if [[ -f "$OPENCLAW_HOME/.env" ]]; then
  # shellcheck disable=SC1090
  source "$OPENCLAW_HOME/.env"
fi

SESSION="${OPENCLAW_SESSION_NAME:-openclaw}"
exec tmux attach -t "$SESSION"
