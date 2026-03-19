# FAQ

## Is this production-ready?
It is a production-minded MVP suitable for single-tenant VPS setups. Start here, then harden networking and secrets for your org.

## Why tmux instead of direct daemon process?
`tmux` gives durable interactive state, easy attach/detach, and operator visibility when debugging agent behavior live.

## Polling vs webhook?
Default is long polling for setup simplicity. Webhook mode is available via env variables when you want strict inbound latency and public HTTPS.

## Where is memory stored?
- Daily logs: `memory/daily/YYYY-MM-DD.md`
- Long term: `memory/long_term/*.md`
- Retrieval index: `memory/index/`

## How do I recover from crashes?
`systemd` auto-restarts services, and watchdog detects stale heartbeats/loops and triggers targeted restarts.

## Can multiple admins use the bot?
Yes. Add multiple comma-separated IDs in `AUTHORIZED_TELEGRAM_USER_IDS` and `ADMIN_CHAT_IDS`.

## Does this support multiple sessions?
The code is session-aware (`OPENCLAW_SESSION_NAME`) and can be extended to multiple named deployments.
