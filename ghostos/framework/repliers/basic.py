from typing import Optional, Dict, Any

from ghostos.core.ghosts import Operator
from ghostos.core.ghosts.schedulers import Replier
from ghostos.core.messages import Role
from ghostos.framework.operators import WaitsOperator, ThinkOperator
from ghostos.helpers import yaml_pretty_dump


class ReplierImpl(Replier):

    def __init__(self, callback_task_id: Optional[str] = None):
        self.callback_task_id = callback_task_id

    def reply(self, content: str) -> Operator:
        return WaitsOperator(
            reason="",
            messages=[content],
            callback_task_id=self.callback_task_id,
        )

    def ask_clarification(self, question: str) -> Operator:
        return WaitsOperator(
            reason="",
            messages=[question],
            callback_task_id=self.callback_task_id,
        )

    def fail(self, reply: str) -> Operator:
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
