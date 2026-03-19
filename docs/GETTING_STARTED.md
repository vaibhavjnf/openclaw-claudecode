# Getting Started

## Prerequisites
- Ubuntu 22.04+
- Public VPS with SSH
- Telegram bot token from BotFather
- Claude Code installed and logged in once

## Fast Path

```bash
git clone https://github.com/<your-org-or-user>/openclaw-claudecode.git
cd openclaw-claudecode
chmod +x scripts/*.sh
./scripts/install.sh
```

Then run onboarding:

```bash
sudo -u openclaw /opt/openclaw/venv/bin/python -m app.onboarding_cli init
sudo -u openclaw /opt/openclaw/venv/bin/python -m app.onboarding_cli doctor
```

## First Telegram Test
1. Send `/status` to your bot.
2. Send a normal text message.
3. Attach to tmux: `sudo -u openclaw tmux attach -t openclaw`
4. Confirm your message appears in Claude runtime.

## Validate Services

```bash
sudo systemctl status openclaw-runtime openclaw-bridge openclaw-scheduler openclaw-watchdog --no-pager
```
