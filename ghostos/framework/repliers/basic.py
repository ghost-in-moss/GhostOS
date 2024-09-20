from typing import Optional, Dict, Any

from ghostos.core.ghosts import Operator
from ghostos.core.ghosts.schedulers import Replier
from ghostos.core.messages import Role
from ghostos.core.session import Task
from ghostos.framework.operators import WaitsOperator, ThinkOperator, FinishOperator
from ghostos.helpers import yaml_pretty_dump


class ReplierImpl(Replier):

    def __init__(self, task: Task, event_from_task: Optional[str] = None):
        callback_task_id = task.parent
        if event_from_task and event_from_task != task.task_id:
            callback_task_id = event_from_task
        self.callback_task_id = callback_task_id

    def finish(self, reply: str) -> Operator:
        if not reply:
            raise AttributeError(f'finish reply shall not be empty ')
        return FinishOperator(
            reason="",
            messages=[reply],
        )

    def reply(self, content: str) -> Operator:
        if not content:
            raise ValueError("reply Content cannot be empty")
        return WaitsOperator(
            reason="",
            messages=[content],
            callback_task_id=self.callback_task_id,
        )

    def ask_clarification(self, question: str) -> Operator:
        if not question:
            raise ValueError("ask clarification question cannot be empty")
        return WaitsOperator(
            reason="",
            messages=[question],
            callback_task_id=self.callback_task_id,
        )

    def fail(self, reply: str) -> Operator:
        if not reply:
            raise ValueError("fail reply cannot be empty")
        return WaitsOperator(
            reason="",
            messages=[reply],
            callback_task_id=self.callback_task_id,
        )

    def think(self, observations: Optional[Dict[str, Any]] = None, instruction: str = "") -> Operator:
        messages = []
        if observations:
            values = {name: str(value) for name, value in observations.items()}
            content = yaml_pretty_dump(values)

            # 用什么协议没想明白, function ? tool? system ?
            content = "# observe values: \n" + content
            msg = Role.new_assistant_system(
                content=content,
            )
            messages.append(msg)

        return ThinkOperator(
            observation=messages,
            reason="",
            instruction=instruction,
        )
