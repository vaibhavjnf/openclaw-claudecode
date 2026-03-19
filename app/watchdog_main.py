from __future__ import annotations

import logging

from app.logging_utils import setup_logging
from app.settings import Settings
from app.watchdog import Watchdog


def main() -> None:
    settings = Settings.load()
    setup_logging(settings.paths.logs / "watchdog.log", settings.log_level)
    logger = logging.getLogger("openclaw")
    watchdog = Watchdog(settings, logger)
    watchdog.run_forever()


if __name__ == "__main__":
    main()
