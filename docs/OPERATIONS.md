# Operations

## Service Commands

```bash
sudo systemctl start openclaw-runtime openclaw-bridge openclaw-scheduler openclaw-watchdog
sudo systemctl stop openclaw-watchdog openclaw-scheduler openclaw-bridge openclaw-runtime
sudo systemctl restart openclaw-runtime openclaw-bridge openclaw-scheduler openclaw-watchdog
sudo systemctl status openclaw-runtime openclaw-bridge openclaw-scheduler openclaw-watchdog --no-pager
```

## Log Inspection

```bash
journalctl -u openclaw-bridge -f
journalctl -u openclaw-watchdog -f
tail -f /opt/openclaw/logs/audit.log
tail -f /opt/openclaw/logs/tmux-pane.log
```

## Common Recovery Steps
1. Restart bridge if Telegram is not responding.
2. Verify `tmux has-session -t openclaw`.
3. Run onboarding doctor for dependency/token checks.
4. Review `logs/audit.log` for blocked user IDs or restart events.

## Release Packaging

```bash
chmod +x scripts/package_release.sh
./scripts/package_release.sh v0.1.0
ls -lh dist/
```
