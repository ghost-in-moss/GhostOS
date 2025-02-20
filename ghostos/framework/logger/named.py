from typing import Optional, Type

from ghostos_container import Provider, Container
from ghostos.contracts.logger import LoggerItf, get_ghostos_logger
from ghostos.contracts.workspace import Workspace
from os.path import join
import logging
from logging.handlers import TimedRotatingFileHandler

__all__ = ['DefaultLoggerProvider']


class DefaultLoggerProvider(Provider[LoggerItf]):
    """
    basic logger
    todo: make logger configurable
    """

    def singleton(self) -> bool:
        return False

    def contract(self) -> Type[LoggerItf]:
        return LoggerItf

    def factory(self, con: Container) -> Optional[LoggerItf]:
        logging.captureWarnings(True)
        ws = con.force_fetch(Workspace)
        logger = get_ghostos_logger()
        if not logger.hasHandlers():
            path = ws.runtime().abspath()
            logfile = join(path, "logs/ghostos.log")
            handler = TimedRotatingFileHandler(
                logfile,
                when="midnight",
                interval=1,
                backupCount=10
            )
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        return logger
