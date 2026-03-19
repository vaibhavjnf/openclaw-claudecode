from __future__ import annotations

import logging

from app.logging_utils import setup_logging
from app.runtime_manager import RuntimeManager
from app.settings import Settings


def main() -> None:
    settings = Settings.load()
    setup_logging(settings.paths.logs / "runtime.log", settings.log_level)
    logger = logging.getLogger("openclaw")
    manager = RuntimeManager(settings, logger)
    manager.start()


if __name__ == "__main__":
    main()
