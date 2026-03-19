#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"
if [[ -f "$OPENCLAW_HOME/.env" ]]; then
  # shellcheck disable=SC1090
  source "$OPENCLAW_HOME/.env"
fi

SESSION="${OPENCLAW_SESSION_NAME:-openclaw}"
MESSAGE="${*:-}"
if [[ -z "$MESSAGE" ]]; then
  echo "Usage: $0 \"message text\""
  exit 1
fi

tmux send-keys -t "$SESSION" -l -- "$MESSAGE"
tmux send-keys -t "$SESSION" C-m
echo "sent"
