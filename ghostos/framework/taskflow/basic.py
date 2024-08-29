from typing import Optional, Dict, Any
from ghostos.core.ghosts import Taskflow, Operator
from ghostos.core.messages import MessageKind, Caller, DefaultMessageTypes, Role
from ghostos.framework.operators import (
    ObserveOperator,
    FinishOperator,
    FailOperator,
    WaitsOperator,
)
from ghostos.helpers import yaml_pretty_dump

__all__ = ['TaskflowBasicImpl']


class TaskflowBasicImpl(Taskflow):

    def __init__(self, caller: Optional[Caller] = None):
        self.caller = caller

    def awaits(self, *replies: MessageKind, log: str = "") -> Operator:
        return WaitsOperator(
            messages=list(replies),
            reason=log,
        )

    def observe(self, objects: Dict[str, Any], reason: str = "", instruction: str = "") -> Operator:
        observation = []
        if objects:
            values = {name: str(value) for name, value in objects.items()}
            content = yaml_pretty_dump(values)

            # 用什么协议没想明白, function ? tool? system ?
            if self.caller is None:
                content = "# observe values: \n" + content
                msg = DefaultMessageTypes.DEFAULT.new_system(
                    content=content,
                )
            else:
                # 使用 caller 协议, 把结果封装成 Function 或者 tool 类型的消息.
                role = Role.FUNCTION.value if self.caller.id is None else Role.TOOL.value
                msg = DefaultMessageTypes.DEFAULT.new(
                    content=content,
                    role=role,
                )
                msg.name = self.caller.name
                msg.ref_id = self.caller.id
            observation.append(msg)

        return ObserveOperator(
            observation=observation,
            reason=reason,
            instruction=instruction,
        )

    def finish(self, log: str, *response: MessageKind) -> Operator:
        return FinishOperator(
            messages=list(response),
            reason=log,
        )

    def fail(self, reason: str, *messages: MessageKind) -> Operator:
        return FailOperator(
            reason=reason,
            messages=list(messages),
        )
