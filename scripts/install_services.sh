#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-/opt/openclaw}"

sudo cp "$OPENCLAW_HOME/services/openclaw-runtime.service" /etc/systemd/system/
sudo cp "$OPENCLAW_HOME/services/openclaw-bridge.service" /etc/systemd/system/
sudo cp "$OPENCLAW_HOME/services/openclaw-scheduler.service" /etc/systemd/system/
sudo cp "$OPENCLAW_HOME/services/openclaw-watchdog.service" /etc/systemd/system/
sudo cp "$OPENCLAW_HOME/services/openclaw.logrotate" /etc/logrotate.d/openclaw

sudo systemctl daemon-reload
sudo systemctl enable openclaw-runtime.service openclaw-bridge.service openclaw-scheduler.service openclaw-watchdog.service
echo "Services installed. Use: sudo systemctl start openclaw-runtime openclaw-bridge openclaw-scheduler openclaw-watchdog"
