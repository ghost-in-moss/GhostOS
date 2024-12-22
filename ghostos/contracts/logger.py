import logging
from abc import abstractmethod
from logging.config import dictConfig
from logging import getLogger, LoggerAdapter, Logger
from typing import Protocol, Optional, Union
from os import path
import yaml

__all__ = [
    'LoggerItf', 'config_logging', 'get_logger', 'get_console_logger', 'get_debug_logger',
    'wrap_logger', 'LoggerAdapter', 'get_ghostos_logger', 'FakeLogger',
]


class LoggerItf(Protocol):
    """
    """

    @abstractmethod
    def debug(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'DEBUG'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.debug("Houston, we have a %s", "thorny problem", exc_info=True)
        """
        pass

    @abstractmethod
    def info(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'INFO'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.debug("Houston, we have a %s", "notable problem", exc_info=True)
        """
        pass

    @abstractmethod
    def warning(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'WARNING'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.warning("Houston, we have a %s", "bit of a problem", exc_info=True)
        """
        pass

    @abstractmethod
    def error(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'ERROR'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.error("Houston, we have a %s", "major problem", exc_info=True)
        """
        pass

    @abstractmethod
    def exception(self, msg, *args, exc_info=True, **kwargs):
        """
        Convenience method for logging an ERROR with exception information.
        """
        pass

    @abstractmethod
    def critical(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'CRITICAL'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.critical("Houston, we have a %s", "major disaster", exc_info=True)
        """
        pass

    @abstractmethod
    def log(self, level, msg, *args, **kwargs):
        """
        Log 'msg % args' with the integer severity 'level'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.log(level, "We have a %s", "mysterious problem", exc_info=True)
        """
        pass


def get_logger(name: Optional[str] = None, extra: Optional[dict] = None) -> LoggerItf:
    return LoggerAdapter(getLogger(name), extra=extra)


def wrap_logger(logger: LoggerItf, extra: dict) -> LoggerItf:
    if isinstance(logger, LoggerAdapter) or isinstance(logger, Logger):
        return LoggerAdapter(logger, extra)
    return logger


def config_logging(conf_path: str) -> None:
    """
    configurate logging by yaml config
    :param conf_path: absolute path of yaml config file
    """
    if not path.exists(conf_path):
        return

    with open(conf_path) as f:
        content = f.read()
    data = yaml.safe_load(content)
    dictConfig(data)


def get_console_logger(
        name: str = "__ghostos_console__",
        extra: Optional[dict] = None,
        debug: bool = False,
) -> LoggerItf:
    logger = getLogger(name)
    if not logger.hasHandlers():
        _console_handler = logging.StreamHandler()
        _console_formatter = PleshakovFormatter()
        _console_handler.setFormatter(_console_formatter)
        logger.addHandler(_console_handler)

    if debug:
        logger.setLevel(logging.DEBUG)
    return LoggerAdapter(logger, extra=extra)


def get_ghostos_logger(extra: Optional[dict] = None) -> Union[LoggerAdapter, Logger]:
    logger = getLogger("ghostos")
    if extra:
        return LoggerAdapter(logger, extra)
    return logger


def get_debug_logger(
        name: str = "__ghostos_debug__",
        extra: Optional[dict] = None,
) -> LoggerItf:
    logger = getLogger(name)
    if not logger.hasHandlers():
        _debug_file_handler = logging.FileHandler("debug.log", mode="a")
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)",
        )
        _debug_file_handler.setFormatter(formatter)
        _debug_file_handler.setLevel(logging.DEBUG)
        logger.addHandler(_debug_file_handler)
    logger.setLevel(logging.DEBUG)
    return LoggerAdapter(logger, extra=extra)


class PleshakovFormatter(logging.Formatter):
    # copy from
    # https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
    grey = "\x1b[37;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    green = "\x1b[32;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class FakeLogger(LoggerItf):
    def debug(self, msg, *args, **kwargs):
        pass

    def info(self, msg, *args, **kwargs):
        pass

    def warning(self, msg, *args, **kwargs):
        pass

    def error(self, msg, *args, **kwargs):
        pass

    def exception(self, msg, *args, exc_info=True, **kwargs):
        pass

    def critical(self, msg, *args, **kwargs):
        pass

    def log(self, level, msg, *args, **kwargs):
        pass


if __name__ == '__main__':
    get_console_logger().debug("hello world")
    get_console_logger().info("hello world")
    get_console_logger().error("hello world")
    get_console_logger().warning("hello world")
    get_console_logger().critical("hello world")
    get_debug_logger().debug("debug")
    get_debug_logger().info("debug")
    get_debug_logger().error("debug")
    get_debug_logger().critical("debug")
