from abc import abstractmethod
from logging.config import dictConfig
from typing import Protocol
import yaml

__all__ = ['LoggerItf', 'config_logging']


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
    def log(self, level, msg, *args, **kwargs):
        """
        Log 'msg % args' with the integer severity 'level'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.log(level, "We have a %s", "mysterious problem", exc_info=True)
        """
        pass


def config_logging(conf_path: str) -> None:
    """
    configurate logging by yaml config
    :param conf_path: absolute path of yaml config file
    """
    with open(conf_path) as f:
        content = f.read()
    data = yaml.safe_load(content)
    dictConfig(data)
