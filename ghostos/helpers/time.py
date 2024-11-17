from typing import Tuple
import time

__all__ = ['Timeleft']


class Timeleft:

    def __init__(self, timeout: float):
        self.timeout = timeout
        self.start = time.time()

    def left(self) -> float:
        passed = self.passed()
        timeleft = self.timeout - passed
        return timeleft

    def alive(self) -> bool:
        return self.timeout <= 0 or self.passed() < self.timeout

    def passed(self) -> float:
        now = time.time()
        return now - self.start
