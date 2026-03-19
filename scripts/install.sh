#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"
OPENCLAW_USER="${OPENCLAW_USER:-openclaw}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/8] Installing OS packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip tmux logrotate curl git

echo "[2/8] Ensuring service user..."
if ! id -u "$OPENCLAW_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /bin/bash "$OPENCLAW_USER"
fi

echo "[3/8] Syncing files to $OPENCLAW_HOME ..."
sudo mkdir -p "$OPENCLAW_HOME"
sudo rsync -a --delete \
  --exclude ".git" \
  --exclude "venv" \
  --exclude "__pycache__" \
  --exclude "logs/*.log" \
  --exclude "runtime/*.json" \
  "$REPO_DIR"/ "$OPENCLAW_HOME"/

echo "[4/8] Preparing env..."
if [[ ! -f "$OPENCLAW_HOME/.env" ]]; then
  sudo cp "$OPENCLAW_HOME/.env.example" "$OPENCLAW_HOME/.env"
fi

echo "[5/8] Creating Python virtualenv..."
if [[ ! -d "$OPENCLAW_HOME/venv" ]]; then
  sudo python3 -m venv "$OPENCLAW_HOME/venv"
fi
sudo "$OPENCLAW_HOME/venv/bin/pip" install --upgrade pip
sudo "$OPENCLAW_HOME/venv/bin/pip" install -r "$OPENCLAW_HOME/requirements.txt"

echo "[6/8] Installing systemd units + logrotate..."
sudo cp "$OPENCLAW_HOME/services/openclaw-runtime.service" /etc/systemd/system/
sudo cp "$OPENCLAW_HOME/services/openclaw-bridge.service" /etc/systemd/system/
sudo cp "$OPENCLAW_HOME/services/openclaw-scheduler.service" /etc/systemd/system/
sudo cp "$OPENCLAW_HOME/services/openclaw-watchdog.service" /etc/systemd/system/
sudo cp "$OPENCLAW_HOME/services/openclaw.logrotate" /etc/logrotate.d/openclaw
sudo systemctl daemon-reload

echo "[7/8] Fixing ownership..."
sudo chown -R "$OPENCLAW_USER:$OPENCLAW_USER" "$OPENCLAW_HOME"

echo "[8/8] Enabling and starting services..."
sudo systemctl enable openclaw-runtime.service openclaw-bridge.service openclaw-scheduler.service openclaw-watchdog.service
sudo systemctl restart openclaw-runtime.service openclaw-bridge.service openclaw-scheduler.service openclaw-watchdog.service

echo
echo "Install complete."
echo "Next:"
echo "  1) Edit $OPENCLAW_HOME/.env"
echo "  2) Run onboarding:"
echo "     sudo -u $OPENCLAW_USER $OPENCLAW_HOME/venv/bin/python -m app.onboarding_cli init"
echo "     sudo -u $OPENCLAW_USER $OPENCLAW_HOME/venv/bin/python -m app.onboarding_cli doctor"
echo "  3) Check status:"
echo "     sudo systemctl status openclaw-runtime openclaw-bridge openclaw-scheduler openclaw-watchdog --no-pager"
