from typing import Optional, Type

from ghostos.container import Provider, Container
from ghostos.contracts.logger import LoggerItf, LoggerWrapper
from os.path import join
import logging

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
        origin = logging.getLogger(self.logger_name)
        adapter = LoggerWrapper(origin)
        return adapter
