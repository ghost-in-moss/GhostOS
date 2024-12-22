from typing import Dict, Any
from ghostos.core.ghosts import Taskflow, Operator
from ghostos.core.messages import MessageType
from ghostos.framework.operators import (
    ThinkOperator,
    FinishOperator,
    FailOperator,
    WaitsOperator,
)
from ghostos.helpers import yaml_pretty_dump

__all__ = ['TaskflowBasicImpl']


class TaskflowBasicImpl(Taskflow):

    def awaits(self, reply: str = "", log: str = "") -> Operator:
        return WaitsOperator(
            messages=list(reply),
            reason=log,
        )

    def observe(self, objects: Dict[str, Any], reason: str = "", instruction: str = "") -> Operator:
        observation = []
        if objects:
            values = {name: str(value) for name, value in objects.items()}
            content = yaml_pretty_dump(values)

            # 用什么协议没想明白, function ? tool? system ?
            content = "observe values: \n" + content
            msg = MessageType.DEFAULT.new_system(
                content=content,
            )
            observation.append(msg)

        return ThinkOperator(
            observation=observation,
            reason=reason,
            instruction=instruction,
        )

    def finish(self, log: str, response: str) -> Operator:
        return FinishOperator(
            messages=list(response),
            reason=log,
        )

    def think(self, instruction: str = "") -> Operator:
        return ThinkOperator(
            reason="",
            observation=[],
            instruction=instruction,
        )

    def fail(self, reason: str, reply: str) -> Operator:
        return FailOperator(
            reason=reason,
            messages=list(reply),
        )
