from abc import ABC, abstractmethod
from logging import LoggerAdapter, Logger, getLogger
from typing import Union, Dict

__all__ = ['LoggerItf', 'LoggerAdapter', 'LoggerType', 'LoggerWrapper']


class LoggerItf(ABC):
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

        logger.info("Houston, we have a %s", "notable problem", exc_info=True)
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
    def fatal(self, msg, *args, **kwargs):
        """
        Don't use this method, use critical() instead.
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

    @abstractmethod
    def with_trace(self, trace: Dict) -> "LoggerItf":
        pass


LoggerType = Union[LoggerAdapter, Logger]


class LoggerWrapper(LoggerItf):

    def __init__(self, logger: LoggerType):
        self.logger = logger

    def debug(self, msg, *args, **kwargs):
        return self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        return self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        return self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        return self.logger.error(msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        return self.logger.exception(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        return self.logger.critical(msg, *args, **kwargs)

    def fatal(self, msg, *args, **kwargs):
        return self.logger.fatal(msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        return self.logger.log(level, msg, *args, **kwargs)

    def with_trace(self, trace: Dict) -> "LoggerItf":
        # todo: add trace
        return LoggerWrapper(LoggerAdapter(self.logger, extra=dict(trace=trace)))


def get_logger(logger_name: str) -> LoggerItf:
    return LoggerWrapper(getLogger(logger_name))
