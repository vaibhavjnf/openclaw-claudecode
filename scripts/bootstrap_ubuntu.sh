#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"
OPENCLAW_USER="${OPENCLAW_USER:-openclaw}"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip tmux logrotate curl

if ! id -u "$OPENCLAW_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /bin/bash "$OPENCLAW_USER"
fi

sudo mkdir -p "$OPENCLAW_HOME"
sudo chown -R "$OPENCLAW_USER:$OPENCLAW_USER" "$OPENCLAW_HOME"

echo "Bootstrap complete."
