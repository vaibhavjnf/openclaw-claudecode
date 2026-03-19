# UX Review (Zoomed-Out)

## What works well
- Single-command installer lowers time-to-first-message.
- Onboarding CLI reduces manual `.env` errors.
- Telegram admin commands make remote ops simple on mobile.
- tmux attach keeps operator trust high during incidents.

## Friction points
- First-time Claude Code auth remains manual.
- Watchdog currently runs as root for service restarts.
- Auto relay may include noisy terminal output depending on prompt style.

## Improvements queued
1. Add optional structured output mode for cleaner Telegram relay.
2. Add `openclaw` CLI wrapper command (`openclaw status`, `openclaw doctor`).
3. Add installer preflight that detects missing `claude` login state explicitly.
4. Add webhook reverse-proxy templates (Caddy/Nginx) with health checks.
5. Add a tiny web dashboard for status + logs + loop state.
