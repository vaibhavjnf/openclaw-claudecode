from __future__ import annotations

import logging
import time
from pathlib import Path

from app.audit import AuditTrail
from app.settings import Settings
from app.tmux_controller import TmuxController
from app.utils import read_json, run_cmd, utc_ts


class Watchdog:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger.getChild("watchdog")
        self.audit = AuditTrail(self.settings.paths.logs / "audit.log")
        self.tmux = TmuxController(
            session_name=settings.session_name,
            pane_log_path=settings.paths.logs / "tmux-pane.log",
            logger=self.logger,
        )
        self.runtime_hb = settings.paths.runtime / "runtime_heartbeat.json"
        self.bridge_hb = settings.paths.runtime / "bridge_heartbeat.json"
        self.scheduler_hb = settings.paths.runtime / "scheduler_heartbeat.json"
        self.loop_hb = settings.paths.runtime / "loop_heartbeats.json"
        self.loops_config = settings.paths.config / "loops.json"
        self.watchdog_hb = settings.paths.runtime / "watchdog_heartbeat.json"

    def _heartbeat_age(self, path: Path) -> float:
        data = read_json(path, default={}) or {}
        ts = float(data.get("ts", 0))
        if ts <= 0:
            return float("inf")
        return utc_ts() - ts

    def _restart(self, unit: str, reason: str) -> None:
        result = run_cmd(["systemctl", "restart", unit], timeout=20)
        payload = {
            "unit": unit,
            "reason": reason,
            "code": result.returncode,
            "stderr": result.stderr[-300:],
        }
        self.audit.log("watchdog_restart", payload)
        if result.returncode == 0:
            self.logger.warning("Restarted %s (%s)", unit, reason)
        else:
            self.logger.error("Failed to restart %s: %s", unit, result.stderr.strip())

    def _check_loop_silence(self) -> None:
        loops = read_json(self.loops_config, default=[]) or []
        beats = read_json(self.loop_hb, default={}) or {}
        now = utc_ts()
        for loop in loops:
            if not loop.get("enabled", True):
                continue
            loop_id = str(loop.get("id", ""))
            if not loop_id:
                continue
            last = float(beats.get(loop_id, 0))
            max_silence = int(loop.get("max_silence_sec", 180))
            if last <= 0 or now - last > max_silence:
                self._restart(self.settings.service_scheduler_name, f"loop_stale:{loop_id}")
                break

    def run_forever(self) -> None:
        self.logger.info("Watchdog started")
        while True:
            if not self.tmux.has_session():
                self._restart(self.settings.service_runtime_name, "missing_tmux_session")

            if self._heartbeat_age(self.bridge_hb) > self.settings.bridge_heartbeat_stale_sec:
                self._restart(self.settings.service_bridge_name, "bridge_heartbeat_stale")

            if (
                self._heartbeat_age(self.scheduler_hb)
                > self.settings.scheduler_heartbeat_stale_sec
            ):
                self._restart(self.settings.service_scheduler_name, "scheduler_heartbeat_stale")

            self._check_loop_silence()
            self.watchdog_hb.write_text(
                f'{{"ts": {utc_ts():.3f}}}',
                encoding="utf-8",
            )
            time.sleep(self.settings.watchdog_interval_sec)
