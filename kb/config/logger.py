import sys
from loguru import logger
from config.settings import settings


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.LOG_LEVEL, colorize=True)


__all__ = ["logger", "setup_logging"]
