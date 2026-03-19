from __future__ import annotations

import asyncio
import logging

from app.logging_utils import setup_logging
from app.scheduler_engine import SchedulerEngine
from app.settings import Settings


async def _main() -> None:
    settings = Settings.load()
    logger = setup_logging(settings.paths.logs / "scheduler.log", settings.log_level)
    logger = logging.getLogger("openclaw")
    engine = SchedulerEngine(settings, logger)
    await engine.start()


if __name__ == "__main__":
    asyncio.run(_main())
