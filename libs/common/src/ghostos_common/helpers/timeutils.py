from datetime import datetime
import time

__all__ = ['Timeleft', 'timestamp_datetime', 'timestamp', 'timestamp_ms']


class Timeleft:

    def __init__(self, timeout: float):
        self.timeout = timeout
        self.start = time.time()

    def left(self) -> float:
        passed = self.passed()
        timeleft = self.timeout - passed
        return timeleft if timeleft > 0 else 0

    def alive(self) -> bool:
        return self.timeout <= 0 or self.passed() < self.timeout

    def passed(self) -> float:
        now = time.time()
        return round(now - self.start, 4)


def timestamp_datetime() -> datetime:
    return datetime.fromtimestamp(int(time.time()))


def timestamp() -> int:
    return int(round(time.time(), 0))


def timestamp_ms() -> float:
    return round(time.time(), 4)
