from typing import Optional, Type

from ghostos.container import Provider, Container
from ghostos.contracts.logger import LoggerItf, LoggerAdapter
from ghostos.contracts.workspace import Workspace
from os.path import join
import logging
from logging.handlers import RotatingFileHandler

__all__ = ['NamedLoggerProvider']


class NamedLoggerProvider(Provider[LoggerItf]):
    """
    basic logger
    """

    def __init__(
            self,
            logger_name: str = "ghostos",
    ):
        self.logger_name = logger_name

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[LoggerItf]:
        return LoggerItf

    def factory(self, con: Container) -> Optional[LoggerItf]:
        logging.captureWarnings(True)
        ws = con.force_fetch(Workspace)
        logger = logging.getLogger(self.logger_name)
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
        wrapped = LoggerAdapter(logger, extra={})
        return wrapped
