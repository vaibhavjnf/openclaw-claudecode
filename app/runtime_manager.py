from __future__ import annotations

import logging
import time

from app.settings import Settings
from app.tmux_controller import TmuxController
from app.utils import touch_heartbeat


class RuntimeManager:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger.getChild("runtime")
        self.tmux = TmuxController(
            session_name=settings.session_name,
            pane_log_path=settings.paths.logs / "tmux-pane.log",
            logger=self.logger,
        )
        self.heartbeat = self.settings.paths.runtime / "runtime_heartbeat.json"

    def start(self) -> None:
        self.logger.info("Runtime manager started for session %s", self.settings.session_name)
        while True:
            self.tmux.ensure_session(self.settings.claude_cmd)
            touch_heartbeat(self.heartbeat, {"session": self.settings.session_name})
            time.sleep(5)
