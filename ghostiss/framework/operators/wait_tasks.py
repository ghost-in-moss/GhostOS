from typing import Optional

from ghostiss.core.ghosts import Operator, Ghost


class WaitOnTasks(Operator):

    def __init__(self, *thoughts):
        self.thoughts = thoughts

    def run(self, g: "Ghost") -> Optional["Operator"]:
        g.utils().create_child_tasks(True, *self.thoughts)
        return None

    def destroy(self) -> None:
        del self.thoughts
