from typing import Optional
from ghostiss.core.ghosts import Taskflow, Operator
from ghostiss.core.messages import MessageKind, Caller, DefaultMessageTypes, Role
from ghostiss.framework.operators import (
    AwaitsOperator,
    ObserveOperator,
    FinishOperator,
    FailOperator,
)
from ghostiss.helpers import yaml_pretty_dump


class TaskflowBasicImpl(Taskflow):

    def __init__(self, caller: Optional[Caller] = None):
        self.caller = caller

    def awaits(self, *replies: MessageKind, log: str = "") -> Operator:
        return AwaitsOperator(
            replies=list(replies),
            log=log,
        )

    def observe(self, *messages: MessageKind, **kwargs) -> Operator:
        observation = list(messages)
        if kwargs:
            values = {name: str(value) for name, value in kwargs.items()}
            content = yaml_pretty_dump(values)

            if self.caller is None:
                content = "# observe values: \n" + content
                msg = DefaultMessageTypes.DEFAULT.new(
                    content=content,
                    role=Role.SYSTEM.value,
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
            log="",
        )

    def finish(self, status: str, *response: MessageKind) -> Operator:
        return FinishOperator(
            messages=list(response),
            log=status,
        )

    def fail(self, reason: str, *messages: MessageKind) -> Operator:
        return FailOperator(
            reason=reason,
            messages=list(messages),
        )
