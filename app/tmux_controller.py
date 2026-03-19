from __future__ import annotations

import logging
from pathlib import Path

from app.utils import run_cmd


class TmuxController:
    def __init__(self, session_name: str, pane_log_path: Path, logger: logging.Logger):
        self.session_name = session_name
        self.pane_log_path = pane_log_path
        self.logger = logger

    def has_session(self) -> bool:
        result = run_cmd(["tmux", "has-session", "-t", self.session_name], timeout=5)
        return result.returncode == 0

    def ensure_session(self, claude_cmd: str) -> None:
        if not self.has_session():
            self.logger.info("Creating tmux session %s", self.session_name)
            run_cmd(
                ["tmux", "new-session", "-d", "-s", self.session_name, claude_cmd],
                timeout=10,
            )
        self.enable_pipe_pane()

    def enable_pipe_pane(self) -> None:
        self.pane_log_path.parent.mkdir(parents=True, exist_ok=True)
        pipe_cmd = f"cat >> {self.pane_log_path}"
        run_cmd(
            [
                "tmux",
                "pipe-pane",
                "-o",
                "-t",
                f"{self.session_name}:0.0",
                pipe_cmd,
            ],
            timeout=10,
        )

    def send_keys(self, text: str) -> bool:
        if not self.has_session():
            self.logger.warning("tmux session missing: %s", self.session_name)
            return False
        # Send line-by-line so multiline prompts preserve formatting.
        lines = text.splitlines() or [text]
        for idx, line in enumerate(lines):
            run_cmd(
                ["tmux", "send-keys", "-t", self.session_name, "-l", "--", line],
                timeout=5,
            )
            if idx < len(lines) - 1:
                run_cmd(["tmux", "send-keys", "-t", self.session_name, "C-m"], timeout=5)
        run_cmd(["tmux", "send-keys", "-t", self.session_name, "C-m"], timeout=5)
        return True

    def capture_recent(self, lines: int = 80) -> str:
        result = run_cmd(
            [
                "tmux",
                "capture-pane",
                "-p",
                "-S",
                f"-{max(lines, 10)}",
                "-t",
                f"{self.session_name}:0.0",
            ],
            timeout=10,
        )
        if result.returncode != 0:
            return ""
        return result.stdout
