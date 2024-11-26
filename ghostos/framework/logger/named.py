from typing import Optional, Type

from ghostos.container import Provider, Container
from ghostos.contracts.logger import LoggerItf, LoggerAdapter, get_ghostos_logger
from ghostos.contracts.workspace import Workspace
from os.path import join
import logging
from logging.handlers import RotatingFileHandler

__all__ = ['DefaultLoggerProvider']


class DefaultLoggerProvider(Provider[LoggerItf]):
    """
    basic logger
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
            handler = RotatingFileHandler(logfile, mode="a")
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        return logger
