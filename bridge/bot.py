from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.audit import AuditTrail
from app.logging_utils import setup_logging
from app.memory_store import InteractionEvent, MemoryStore
from app.retrieval import LexicalRetriever
from app.settings import Settings
from app.tmux_controller import TmuxController
from app.utils import read_json, run_cmd, touch_heartbeat, write_json

ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


@dataclass
class QueueItem:
    user_id: int
    chat_id: int
    text: str
    username: str


class TelegramBridge:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger("openclaw.bridge")
        self.audit = AuditTrail(self.settings.paths.logs / "audit.log")
        self.tmux = TmuxController(
            session_name=settings.session_name,
            pane_log_path=settings.paths.logs / "tmux-pane.log",
            logger=self.logger,
        )
        self.memory_store = MemoryStore(settings.paths.memory)
        self.retriever = LexicalRetriever(
            memory_store=self.memory_store,
            index_path=settings.paths.memory_index / "lexical_index.json",
        )
        self.queue: asyncio.Queue[QueueItem] = asyncio.Queue(maxsize=settings.queue_max_size)
        self.relay_offset_path = self.settings.paths.runtime / "relay_offset.json"
        self.bridge_heartbeat_path = self.settings.paths.runtime / "bridge_heartbeat.json"
        self.user_msg_times: dict[int, deque[float]] = defaultdict(deque)
        self.active_chat_ids: set[int] = set(self.settings.admin_chat_ids)
        self.worker_task: asyncio.Task | None = None
        self.relay_task: asyncio.Task | None = None
        self._app: Application | None = None

    def is_authorized(self, user_id: int) -> bool:
        return user_id in self.settings.authorized_user_ids

    def _rate_limited(self, user_id: int) -> bool:
        now = time.time()
        window = self.user_msg_times[user_id]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.settings.per_user_msgs_per_min:
            return True
        window.append(now)
        return False

    def _sanitize(self, text: str) -> str:
        text = text.replace("\x00", "")
        text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
        return text.strip()[: self.settings.message_max_chars]

    def _build_injected_prompt(self, user_text: str, snippets: list[str]) -> str:
        context_lines = snippets or ["(no memory hits)"]
        context = "\n".join(f"- {line}" for line in context_lines)
        return f"Context:\n{context}\n\nUser:\n{user_text}"

    async def _send_safe(self, chat_id: int, text: str) -> None:
        if not self._app:
            return
        if not text.strip():
            return
        chunk_size = max(500, self.settings.relay_chunk_chars)
        for i in range(0, len(text), chunk_size):
            await self._app.bot.send_message(chat_id=chat_id, text=text[i : i + chunk_size])

    async def _reject_unauthorized(self, update: Update) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        self.audit.log("unauthorized_attempt", {"user_id": user_id})
        if update.effective_chat:
            await self._send_safe(update.effective_chat.id, "Unauthorized.")

    async def _require_auth(self, update: Update) -> tuple[bool, int, int]:
        if not update.effective_user or not update.effective_chat:
            return False, 0, 0
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if not self.is_authorized(user_id):
            await self._reject_unauthorized(update)
            return False, user_id, chat_id
        return True, user_id, chat_id

    async def on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        ok, user_id, chat_id = await self._require_auth(update)
        if not ok:
            return
        username = update.effective_user.username or "unknown"
        if self._rate_limited(user_id):
            await self._send_safe(chat_id, "Rate limit exceeded. Please wait a moment.")
            return
        text = self._sanitize(update.message.text or "")
        if not text:
            return
        if self.queue.full():
            await self._send_safe(chat_id, "Bridge queue is full. Please retry shortly.")
            self.audit.log("queue_rejected", {"user_id": user_id, "chat_id": chat_id})
            return
        await self.queue.put(QueueItem(user_id=user_id, chat_id=chat_id, text=text, username=username))
        self.active_chat_ids.add(chat_id)
        self.audit.log("message_queued", {"user_id": user_id, "chat_id": chat_id, "size": self.queue.qsize()})

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ok, _user_id, chat_id = await self._require_auth(update)
        if not ok:
            return
        tmux_state = "up" if self.tmux.has_session() else "down"
        units = {
            "runtime": self.settings.service_runtime_name,
            "bridge": self.settings.service_bridge_name,
            "scheduler": self.settings.service_scheduler_name,
        }
        lines = [f"tmux({self.settings.session_name}): {tmux_state}", f"queue_size: {self.queue.qsize()}"]
        for alias, unit in units.items():
            result = run_cmd(["systemctl", "is-active", unit], timeout=8)
            state = result.stdout.strip() or "unknown"
            lines.append(f"{alias}: {state}")
        await self._send_safe(chat_id, "\n".join(lines))

    async def cmd_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ok, user_id, chat_id = await self._require_auth(update)
        if not ok:
            return
        if not context.args:
            await self._send_safe(chat_id, "Usage: /restart runtime|bridge|scheduler")
            return
        arg = context.args[0].lower()
        mapping = {
            "runtime": self.settings.service_runtime_name,
            "bridge": self.settings.service_bridge_name,
            "scheduler": self.settings.service_scheduler_name,
        }
        unit = mapping.get(arg)
        if not unit:
            await self._send_safe(chat_id, "Unknown target.")
            return
        result = run_cmd(["systemctl", "restart", unit], timeout=20)
        self.audit.log("manual_restart", {"user_id": user_id, "unit": unit, "rc": result.returncode})
        if result.returncode == 0:
            await self._send_safe(chat_id, f"Restarted {unit}")
        else:
            await self._send_safe(chat_id, f"Failed to restart {unit}: {result.stderr[-200:]}")

    async def cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ok, _user_id, chat_id = await self._require_auth(update)
        if not ok:
            return
        if not context.args:
            await self._send_safe(chat_id, "Usage: /memory <query>")
            return
        query = self._sanitize(" ".join(context.args))
        results = self.retriever.search(query=query, k=self.settings.retrieval_top_k)
        if not results:
            await self._send_safe(chat_id, "No memory hits.")
            return
        lines = []
        for idx, item in enumerate(results, start=1):
            lines.append(f"{idx}. {Path(item.path).name} ({item.score:.2f})\n{item.snippet[:220]}")
        await self._send_safe(chat_id, "\n\n".join(lines))

    async def cmd_tail(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ok, _user_id, chat_id = await self._require_auth(update)
        if not ok:
            return
        lines = 80
        if context.args:
            try:
                lines = max(20, min(400, int(context.args[0])))
            except ValueError:
                lines = 80
        output = self.tmux.capture_recent(lines=lines)
        if not output.strip():
            output = "(no tmux output)"
        await self._send_safe(chat_id, output[-self.settings.relay_chunk_chars :])

    async def cmd_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ok, _user_id, chat_id = await self._require_auth(update)
        if not ok:
            return
        tasks = read_json(self.settings.paths.config / "tasks.json", default=[]) or []
        if not tasks:
            await self._send_safe(chat_id, "No tasks configured.")
            return
        lines = [
            f"{t.get('id')} | {'on' if t.get('enabled', True) else 'off'} | {t.get('cron')} | {t.get('name')}"
            for t in tasks
        ]
        await self._send_safe(chat_id, "\n".join(lines))

    async def cmd_loops(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ok, _user_id, chat_id = await self._require_auth(update)
        if not ok:
            return
        loops = read_json(self.settings.paths.config / "loops.json", default=[]) or []
        if not loops:
            await self._send_safe(chat_id, "No loops configured.")
            return
        lines = [
            f"{loop_item.get('id')} | {'on' if loop_item.get('enabled', True) else 'off'} | every {loop_item.get('interval_sec')}s | {loop_item.get('name')}"
            for loop_item in loops
        ]
        await self._send_safe(chat_id, "\n".join(lines))

    async def cmd_promote(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ok, user_id, chat_id = await self._require_auth(update)
        if not ok:
            return
        if not context.args:
            await self._send_safe(
                chat_id,
                "Usage: /promote [profile.md|knowledge.md|projects.md|learnings.md] <fact>",
            )
            return
        args = context.args
        target = "learnings.md"
        if args[0].endswith(".md") and len(args) > 1:
            target = args[0]
            args = args[1:]
        fact = self._sanitize(" ".join(args))
        path = self.memory_store.promote_fact(fact, target_file=target)
        self.audit.log("memory_promote", {"by": user_id, "target": str(path), "fact": fact})
        await self._send_safe(chat_id, f"Promoted to {path.name}")

    async def _queue_worker(self) -> None:
        while True:
            item = await self.queue.get()
            try:
                results = self.retriever.search(
                    query=item.text, k=self.settings.retrieval_top_k, scopes=["daily", "long_term"]
                )
                snippets = [f"{Path(r.path).name}: {r.snippet[:180]}" for r in results]
                injected = self._build_injected_prompt(item.text, snippets)
                ok = self.tmux.send_keys(injected)
                if ok:
                    event = InteractionEvent(
                        source="telegram",
                        user_id=item.user_id,
                        chat_id=item.chat_id,
                        user_text=item.text,
                        injected_text=injected,
                        retrieved_snippets=snippets,
                    )
                    self.memory_store.log_interaction(event)
                else:
                    await self._send_safe(item.chat_id, "tmux session unavailable.")
                self.audit.log(
                    "message_injected",
                    {"user_id": item.user_id, "chat_id": item.chat_id, "ok": ok, "hits": len(results)},
                )
            finally:
                self.queue.task_done()
                touch_heartbeat(self.bridge_heartbeat_path, {"queue": self.queue.qsize()})

    def _read_new_tmux_text(self) -> str:
        path = self.settings.paths.logs / "tmux-pane.log"
        if not path.exists():
            return ""
        state = read_json(self.relay_offset_path, default={"offset": 0}) or {"offset": 0}
        offset = int(state.get("offset", 0))
        size = path.stat().st_size
        if offset > size:
            offset = 0
        with path.open("rb") as f:
            f.seek(offset)
            data = f.read()
            offset = f.tell()
        write_json(self.relay_offset_path, {"offset": offset})
        return data.decode("utf-8", errors="replace")

    def _clean_relay_text(self, raw: str) -> str:
        cleaned = ANSI_RE.sub("", raw)
        out_lines = []
        for line in cleaned.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(("Context:", "User:", "- (no memory hits)")):
                continue
            out_lines.append(line)
        return "\n".join(out_lines).strip()

    async def _relay_worker(self) -> None:
        while True:
            await asyncio.sleep(self.settings.relay_poll_interval_sec)
            raw = self._read_new_tmux_text()
            if not raw:
                touch_heartbeat(self.bridge_heartbeat_path, {"queue": self.queue.qsize()})
                continue
            text = self._clean_relay_text(raw)
            if not text:
                continue
            self.memory_store.log_assistant_output(text)
            for line in text.splitlines():
                if "#promote" in line.lower():
                    fact = re.sub(r"(?i)#promote", "", line).strip(" -:")
                    if fact:
                        target = self.memory_store.promote_fact(fact, target_file="learnings.md")
                        self.audit.log("auto_promote", {"fact": fact, "target": str(target)})
            for chat_id in list(self.active_chat_ids):
                try:
                    await self._send_safe(chat_id, text)
                except Exception as exc:
                    self.logger.warning("relay send failed to %s: %s", chat_id, exc)
            touch_heartbeat(self.bridge_heartbeat_path, {"queue": self.queue.qsize()})

    async def _post_init(self, app: Application) -> None:
        self._app = app
        self.worker_task = asyncio.create_task(self._queue_worker(), name="queue_worker")
        self.relay_task = asyncio.create_task(self._relay_worker(), name="relay_worker")
        touch_heartbeat(self.bridge_heartbeat_path, {"queue": 0})

    async def _post_shutdown(self, app: Application) -> None:
        for task in [self.worker_task, self.relay_task]:
            if task:
                task.cancel()
        await asyncio.gather(*(t for t in [self.worker_task, self.relay_task] if t), return_exceptions=True)

    def build_application(self) -> Application:
        if not self.settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
        app = (
            Application.builder()
            .token(self.settings.telegram_bot_token)
            .post_init(self._post_init)
            .post_shutdown(self._post_shutdown)
            .build()
        )

        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("restart", self.cmd_restart))
        app.add_handler(CommandHandler("memory", self.cmd_memory))
        app.add_handler(CommandHandler("tail", self.cmd_tail))
        app.add_handler(CommandHandler("tasks", self.cmd_tasks))
        app.add_handler(CommandHandler("loops", self.cmd_loops))
        app.add_handler(CommandHandler("promote", self.cmd_promote))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_text))
        return app

    def run(self) -> None:
        app = self.build_application()
        if self.settings.telegram_webhook_url:
            webhook_url = (
                self.settings.telegram_webhook_url.rstrip("/")
                + "/"
                + self.settings.telegram_bot_token
            )
            app.run_webhook(
                listen="0.0.0.0",
                port=8080,
                url_path=self.settings.telegram_bot_token,
                webhook_url=webhook_url,
                secret_token=self.settings.telegram_webhook_secret or None,
                drop_pending_updates=True,
            )
            return
        app.run_polling(
            drop_pending_updates=True,
            poll_interval=0.0,
            timeout=self.settings.telegram_poll_timeout,
            close_loop=False,
        )


def main() -> None:
    settings = Settings.load()
    setup_logging(settings.paths.logs / "bridge.log", settings.log_level)
    bridge = TelegramBridge(settings)
    bridge.run()


if __name__ == "__main__":
    main()
