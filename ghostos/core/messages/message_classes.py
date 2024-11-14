from typing import Optional, Dict, List, Iterable, Any, Union
from typing_extensions import Self

from ghostos.contracts.variables import Variables
from ghostos.container import Container
from ghostos.prompter import get_defined_prompt
from .message import Message, MessageClass, MessageType, CallerOutput, MessageKind, Role
from pydantic import BaseModel, Field

__all__ = ["VariableMessage", "CallerOutput", "MessageKindParser"]


class VariableMessage(MessageClass, BaseModel):
    """
    变量类型消息.
    """

    __message_type__ = MessageType.VARIABLE.value

    role: str = Field(default="", description="who send the message")
    name: Optional[str] = Field(None, description="who send the message")

    attrs: Variables.Var = Field(
        description="variable pointer info"
    )
    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="payload type key to payload item. payload shall be a strong-typed dict"
    )

    def to_message(self) -> Message:
        message = Message.new_tail(
            type_=MessageType.VARIABLE.value,
            content="",
            role=self.role,
            name=self.name,
            attrs=self.attrs.model_dump(),
        )
        message.payloads = self.payloads
        return message

    @classmethod
    def from_message(cls, message: Message) -> Optional[Self]:
        if message.type != MessageType.VARIABLE.value:
            return None

        obj = cls(
            role=message.role,
            name=message.name,
            attrs=message.attrs,
            payloads=message.payloads,
        )
        return obj

    def to_openai_param(self, container: Optional[Container]) -> List[Dict]:
        content = f"""variable message:
vid: {self.attrs.vid} 
type: {self.attrs.type}
desc: {self.attrs.desc}
"""
        if container and container.bound(Variables):
            variables = container.force_fetch(Variables)
            v = variables.load(self.attrs.vid)
            prompt = get_defined_prompt(v)
            if prompt:
                content += f"\nmore information:\n```\n{prompt}\n```"

        return [dict(
            content=content,
            role=self.role,
            name=self.name,
        )]


class MessageKindParser:
    """
    middleware that parse weak MessageKind into Message chunks
    """

    def __init__(
            self,
            variables: Variables,
            *,
            name: Optional[str] = None,
            role: str = Role.ASSISTANT.value,
            ref_id: Optional[str] = None,
    ) -> None:
        self.variables = variables
        self.role = role
        self.ref_id = ref_id
        self.name = name

    def parse(self, messages: Iterable[Union[MessageKind, Any]]) -> Iterable[Message]:
        for item in messages:
            if isinstance(item, Message):
                yield self._with_ref(item)
            if isinstance(item, MessageClass):
                msg = item.to_message()
                yield self._with_ref(msg)
            if isinstance(item, str):
                if not item:
                    # exclude empty message
                    continue
                msg = Message.new_tail(content=item, role=self.role)
                yield self._with_ref(msg)
            else:
                var = self.variables.save(item)
                vm = VariableMessage(
                    name=self.name,
                    role=self.role,
                    attrs=var.model_dump(),
                )
                yield vm.to_message()

    def _with_ref(self, item: Message) -> Message:
        if self.ref_id is not None:
            item.ref_id = self.ref_id
        if not item.role and self.role:
            item.role = self.role
        if not item.name and self.name:
            item.name = self.name
        return item
