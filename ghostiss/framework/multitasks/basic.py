from typing import Dict

from ghostiss.core.ghosts import MultiTask, Operator, Thought, Ghost
from ghostiss.core.messages import MessageKind


# from ghostiss.framework.operators.wait_tasks import


class MultiTaskBasicImpl(MultiTask):

    def wait_on_tasks(self, *thoughts: Thought) -> Operator:
        pass

    def run_tasks(self, *thoughts: Thought) -> Dict[str, str]:
        pass

    def send_task(self, task_name: str, *messages: MessageKind) -> None:
        pass

    def cancel_task(self, name: str, reason: str) -> None:
        pass
