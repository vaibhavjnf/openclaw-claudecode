from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from croniter import croniter

from app.audit import AuditTrail
from app.settings import Settings
from app.utils import read_json, run_shell, touch_heartbeat, utc_ts, write_json


@dataclass
class CronTask:
    id: str
    name: str
    cron: str
    command: str
    timeout_sec: int
    enabled: bool


@dataclass
class LoopTask:
    id: str
    name: str
    interval_sec: int
    command: str
    max_silence_sec: int
    enabled: bool


class SchedulerEngine:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger.getChild("scheduler")
        self.audit = AuditTrail(self.settings.paths.logs / "audit.log")
        self.tasks_path = self.settings.paths.config / "tasks.json"
        self.loops_path = self.settings.paths.config / "loops.json"
        self.state_path = self.settings.paths.runtime / "scheduler_state.json"
        self.scheduler_heartbeat_path = self.settings.paths.runtime / "scheduler_heartbeat.json"
        self.loop_heartbeats_path = self.settings.paths.runtime / "loop_heartbeats.json"
        self._task_next_run: dict[str, float] = {}
        self._loop_next_run: dict[str, float] = {}
        self._loop_heartbeats: dict[str, float] = {}
        self._running_jobs: set[str] = set()

    def load_configs(self) -> tuple[list[CronTask], list[LoopTask]]:
        tasks_raw = read_json(self.tasks_path, default=[]) or []
        loops_raw = read_json(self.loops_path, default=[]) or []
        tasks: list[CronTask] = []
        loops: list[LoopTask] = []

        for t in tasks_raw:
            try:
                tasks.append(
                    CronTask(
                        id=str(t["id"]),
                        name=str(t.get("name", t["id"])),
                        cron=str(t["cron"]),
                        command=str(t["command"]),
                        timeout_sec=int(t.get("timeout_sec", 120)),
                        enabled=bool(t.get("enabled", True)),
                    )
                )
            except (KeyError, ValueError, TypeError):
                self.logger.warning("Skipping invalid task entry: %s", t)
        for loop_item in loops_raw:
            try:
                loops.append(
                    LoopTask(
                        id=str(loop_item["id"]),
                        name=str(loop_item.get("name", loop_item["id"])),
                        interval_sec=max(5, int(loop_item["interval_sec"])),
                        command=str(loop_item["command"]),
                        max_silence_sec=max(30, int(loop_item.get("max_silence_sec", 180))),
                        enabled=bool(loop_item.get("enabled", True)),
                    )
                )
            except (KeyError, ValueError, TypeError):
                self.logger.warning("Skipping invalid loop entry: %s", loop_item)

        return tasks, loops

    def _compute_next_cron(self, expr: str, base_ts: float | None = None) -> float:
        base = datetime.fromtimestamp(base_ts or utc_ts(), tz=UTC)
        return croniter(expr, base).get_next(datetime).timestamp()

    def rehydrate(self, tasks: list[CronTask], loops: list[LoopTask]) -> None:
        now = utc_ts()
        state = read_json(self.state_path, default={}) or {}
        task_state = state.get("tasks", {})
        loop_state = state.get("loops", {})

        for task in tasks:
            if not task.enabled:
                continue
            candidate = float(task_state.get(task.id, {}).get("next_run", 0))
            if candidate <= now:
                candidate = self._compute_next_cron(task.cron, base_ts=now)
            self._task_next_run[task.id] = candidate

        for loop in loops:
            if not loop.enabled:
                continue
            candidate = float(loop_state.get(loop.id, {}).get("next_run", 0))
            if candidate <= now:
                candidate = now + loop.interval_sec
            self._loop_next_run[loop.id] = candidate
            last_hb = float(loop_state.get(loop.id, {}).get("last_heartbeat", now))
            self._loop_heartbeats[loop.id] = last_hb

        self._flush_state(tasks, loops)

    def _flush_state(self, tasks: list[CronTask], loops: list[LoopTask]) -> None:
        task_map = {t.id: t for t in tasks}
        loop_map = {loop_item.id: loop_item for loop_item in loops}
        state: dict[str, Any] = {"tasks": {}, "loops": {}, "updated_ts": utc_ts()}
        for task_id, next_run in self._task_next_run.items():
            if task_id not in task_map:
                continue
            state["tasks"][task_id] = {
                "name": task_map[task_id].name,
                "next_run": next_run,
            }
        for loop_id, next_run in self._loop_next_run.items():
            if loop_id not in loop_map:
                continue
            state["loops"][loop_id] = {
                "name": loop_map[loop_id].name,
                "next_run": next_run,
                "last_heartbeat": self._loop_heartbeats.get(loop_id, 0),
                "max_silence_sec": loop_map[loop_id].max_silence_sec,
            }
        write_json(self.state_path, state)
        write_json(self.loop_heartbeats_path, self._loop_heartbeats)

    async def _run_job(self, job_id: str, command: str, timeout_sec: int, kind: str) -> None:
        if job_id in self._running_jobs:
            self.logger.info("Skipping %s %s because it is already running", kind, job_id)
            return
        self._running_jobs.add(job_id)
        self.audit.log("job_start", {"job_id": job_id, "kind": kind, "command": command})
        code, stdout, stderr = await run_shell(command, timeout=timeout_sec)
        if kind == "loop":
            self._loop_heartbeats[job_id] = utc_ts()
        payload = {
            "job_id": job_id,
            "kind": kind,
            "exit_code": code,
            "stdout_tail": stdout[-500:],
            "stderr_tail": stderr[-500:],
        }
        self.audit.log("job_end", payload)
        if code != 0:
            self.logger.warning("%s %s exited with %s", kind, job_id, code)
        self._running_jobs.discard(job_id)

    async def start(self) -> None:
        self.logger.info("Scheduler starting")
        while True:
            tasks, loops = self.load_configs()
            if not self._task_next_run and not self._loop_next_run:
                self.rehydrate(tasks, loops)

            now = utc_ts()
            for task in tasks:
                if not task.enabled:
                    continue
                next_run = self._task_next_run.get(task.id)
                if next_run is None:
                    next_run = self._compute_next_cron(task.cron, base_ts=now)
                    self._task_next_run[task.id] = next_run
                if now >= next_run:
                    asyncio.create_task(
                        self._run_job(task.id, task.command, task.timeout_sec, "task")
                    )
                    self._task_next_run[task.id] = self._compute_next_cron(
                        task.cron, base_ts=now + 1
                    )

            for loop in loops:
                if not loop.enabled:
                    continue
                next_run = self._loop_next_run.get(loop.id)
                if next_run is None:
                    next_run = now + loop.interval_sec
                    self._loop_next_run[loop.id] = next_run
                if now >= next_run:
                    asyncio.create_task(
                        self._run_job(loop.id, loop.command, loop.max_silence_sec, "loop")
                    )
                    self._loop_next_run[loop.id] = now + loop.interval_sec

            self._flush_state(tasks, loops)
            touch_heartbeat(self.scheduler_heartbeat_path)
            await asyncio.sleep(1)
