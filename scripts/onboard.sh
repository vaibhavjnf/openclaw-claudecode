#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"

if [[ ! -x "$OPENCLAW_HOME/venv/bin/python" ]]; then
  echo "Missing virtualenv python at $OPENCLAW_HOME/venv/bin/python"
  exit 1
fi

"$OPENCLAW_HOME/venv/bin/python" -m app.onboarding_cli init
"$OPENCLAW_HOME/venv/bin/python" -m app.onboarding_cli doctor
