from typing import Tuple
import time

__all__ = ['Timeleft']


class Timeleft:

    def __init__(self, timeout: float):
        self.timeout = timeout
        self.start = time.time()

    def left(self) -> float:
        if self.timeout <= 0.0:
            return 0.0
        now = time.time()
        timeleft = self.timeout - (now - self.start)
        return timeleft
