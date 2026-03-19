# Security Notes

## Secrets
- Store secrets only in `/opt/openclaw/.env`.
- Never commit `.env` or real token values.
- Restrict file permissions: `chmod 600 /opt/openclaw/.env`.

## Telegram Access Control
- `AUTHORIZED_TELEGRAM_USER_IDS` limits who can send commands/messages.
- Unauthorized attempts are logged to `logs/audit.log`.

## Webhook Mode
- If using webhook, set `TELEGRAM_WEBHOOK_SECRET`.
- Enforce HTTPS and validate `X-Telegram-Bot-Api-Secret-Token`.

## Least Privilege
- Runtime, bridge, scheduler run as `openclaw` user.
- Watchdog runs as root only to restart systemd units.

## Hardening Checklist
1. Lock SSH (`PermitRootLogin no`, keys only).
2. Enable firewall (`ufw allow OpenSSH`, allow only required app ports).
3. Keep Ubuntu security updates enabled.
4. Monitor `audit.log` and journal entries.
