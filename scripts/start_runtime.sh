#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"
if [[ -f "$OPENCLAW_HOME/.env" ]]; then
  # shellcheck disable=SC1090
  source "$OPENCLAW_HOME/.env"
fi

SESSION="${OPENCLAW_SESSION_NAME:-openclaw}"
CLAUDE_CMD="${CLAUDE_CMD:-claude}"
LOG_FILE="$OPENCLAW_HOME/logs/tmux-pane.log"

mkdir -p "$OPENCLAW_HOME/logs" "$OPENCLAW_HOME/runtime" "$OPENCLAW_HOME/memory/daily" "$OPENCLAW_HOME/memory/index" "$OPENCLAW_HOME/memory/long_term"
touch "$LOG_FILE"

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION" "$CLAUDE_CMD"
fi

tmux pipe-pane -o -t "${SESSION}:0.0" "cat >> $LOG_FILE"
echo "Runtime ready in tmux session: $SESSION"
