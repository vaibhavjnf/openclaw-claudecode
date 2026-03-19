from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path) -> None:
    """Load a .env file without overriding existing env vars."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def _parse_int_set(raw: str | None) -> set[int]:
    if not raw:
        return set()
    out: set[int] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            out.add(int(token))
        except ValueError:
            continue
    return out


def _parse_chat_set(raw: str | None, fallback_users: set[int]) -> set[int]:
    parsed = _parse_int_set(raw)
    return parsed or set(fallback_users)


def _parse_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(raw: str | None, default: int) -> int:
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def ensure_dirs(paths: Iterable[Path]) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class AppPaths:
    home: Path
    logs: Path
    config: Path
    memory: Path
    memory_daily: Path
    memory_long_term: Path
    memory_index: Path
    runtime: Path

    @classmethod
    def from_home(cls, home: Path) -> AppPaths:
        return cls(
            home=home,
            logs=home / "logs",
            config=home / "config",
            memory=home / "memory",
            memory_daily=home / "memory" / "daily",
            memory_long_term=home / "memory" / "long_term",
            memory_index=home / "memory" / "index",
            runtime=home / "runtime",
        )


@dataclass(frozen=True)
class Settings:
    paths: AppPaths
    session_name: str
    claude_cmd: str
    telegram_bot_token: str
    authorized_user_ids: set[int]
    admin_chat_ids: set[int]
    telegram_webhook_url: str
    telegram_webhook_secret: str
    telegram_poll_timeout: int
    message_max_chars: int
    queue_max_size: int
    per_user_msgs_per_min: int
    relay_chunk_chars: int
    relay_poll_interval_sec: float
    bridge_heartbeat_stale_sec: int
    scheduler_heartbeat_stale_sec: int
    watchdog_interval_sec: int
    retrieval_top_k: int
    log_level: str
    service_runtime_name: str
    service_bridge_name: str
    service_scheduler_name: str

    @classmethod
    def load(cls) -> Settings:
        home = Path(os.getenv("OPENCLAW_HOME", "/opt/openclaw")).resolve()
        load_dotenv(home / ".env")
        paths = AppPaths.from_home(home)
        ensure_dirs(
            [
                paths.logs,
                paths.config,
                paths.memory,
                paths.memory_daily,
                paths.memory_long_term,
                paths.memory_index,
                paths.runtime,
            ]
        )
        config_users: set[int] = set()
        auth_file = paths.config / "authorized_users.json"
        if auth_file.exists():
            try:
                data = json.loads(auth_file.read_text(encoding="utf-8"))
                config_users = {int(v) for v in data.get("authorized_user_ids", [])}
            except (json.JSONDecodeError, ValueError, TypeError):
                config_users = set()
        users = _parse_int_set(os.getenv("AUTHORIZED_TELEGRAM_USER_IDS")) | config_users
        return cls(
            paths=paths,
            session_name=os.getenv("OPENCLAW_SESSION_NAME", "openclaw"),
            claude_cmd=os.getenv("CLAUDE_CMD", "claude"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            authorized_user_ids=users,
            admin_chat_ids=_parse_chat_set(os.getenv("ADMIN_CHAT_IDS"), users),
            telegram_webhook_url=os.getenv("TELEGRAM_WEBHOOK_URL", "").strip(),
            telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip(),
            telegram_poll_timeout=_parse_int(os.getenv("TELEGRAM_POLL_TIMEOUT"), 2),
            message_max_chars=_parse_int(os.getenv("MESSAGE_MAX_CHARS"), 3000),
            queue_max_size=_parse_int(os.getenv("COMMAND_QUEUE_MAX_SIZE"), 100),
            per_user_msgs_per_min=_parse_int(os.getenv("PER_USER_MSGS_PER_MIN"), 12),
            relay_chunk_chars=_parse_int(os.getenv("RELAY_CHUNK_CHARS"), 3500),
            relay_poll_interval_sec=float(os.getenv("RELAY_POLL_INTERVAL_SEC", "0.5")),
            bridge_heartbeat_stale_sec=_parse_int(
                os.getenv("BRIDGE_HEARTBEAT_STALE_SEC"), 120
            ),
            scheduler_heartbeat_stale_sec=_parse_int(
                os.getenv("SCHEDULER_HEARTBEAT_STALE_SEC"), 180
            ),
            watchdog_interval_sec=_parse_int(os.getenv("WATCHDOG_INTERVAL_SEC"), 15),
            retrieval_top_k=_parse_int(os.getenv("RETRIEVAL_TOP_K"), 5),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            service_runtime_name=os.getenv(
                "RUNTIME_SERVICE_NAME", "openclaw-runtime.service"
            ),
            service_bridge_name=os.getenv(
                "BRIDGE_SERVICE_NAME", "openclaw-bridge.service"
            ),
            service_scheduler_name=os.getenv(
                "SCHEDULER_SERVICE_NAME", "openclaw-scheduler.service"
            ),
        )
