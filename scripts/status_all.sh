#!/usr/bin/env bash
set -euo pipefail

echo "== systemd =="
systemctl --no-pager --full status openclaw-runtime.service openclaw-bridge.service openclaw-scheduler.service openclaw-watchdog.service || true
echo
echo "== tmux =="
tmux ls || true
