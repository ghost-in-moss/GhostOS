from typing import Optional

from ghostos.core.ghosts import Operator, Ghost


class FakeOperator(Operator):

    def __init__(self, info: str, *args, **kwargs):
        self.info = info
        self.args = args
        self.kwargs = kwargs

    def run(self, g: "Ghost") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        return None

    def __repr__(self):
        return f"FakeOperator('{self.info}', args={self.args}, kwargs={self.kwargs})"
