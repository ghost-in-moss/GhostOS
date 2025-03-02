from ghostos.contracts.logger import LoggerItf


def get_logger() -> LoggerItf:
    """
    :return: LoggerItf ghostos facade logger
    """
    from ghostos.bootstrap import get_container
    return get_container().force_fetch(LoggerItf)
