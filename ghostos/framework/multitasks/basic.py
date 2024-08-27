from typing import Dict

from ghostos.core.ghosts import MultiTask, Operator, Thought, Ghost
from ghostos.core.session import Session
from ghostos.core.messages import MessageKind
from ghostos.framework.operators import WaitOnTasksOperator



class MultiTaskBasicImpl(MultiTask):

    def __init__(self, session: Session):
        self._session = session

    def wait_on_tasks(self, *thoughts: Thought) -> Operator:
        return WaitOnTasksOperator(

        )

    def run_tasks(self, *thoughts: Thought) -> Dict[str, str]:
        pass

    def send_task(self, task_name: str, *messages: MessageKind) -> None:
        pass

    def cancel_task(self, name: str, reason: str) -> None:
        pass
