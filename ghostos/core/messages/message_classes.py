import base64
from typing import Optional, Dict, List, Iterable, Any, Union
from typing_extensions import Self, Literal

from ghostos.contracts.variables import Variables
from ghostos.contracts.assets import FileInfo
from ghostos.container import Container
from ghostos.prompter import get_defined_prompt
from .message import Message, MessageClass, MessageType, FunctionOutput, MessageKind, Role, FunctionCaller
from ghostos.helpers import uuid
from pydantic import BaseModel, Field

__all__ = [
    "VariableMessage",
    "FunctionCallMessage",
    "FunctionCallOutputMessage",
    "FunctionOutput",
    "ImageAssetMessage",
    "AudioMessage",
    "MessageKindParser",
]

FunctionCallOutputMessage = FunctionOutput


class FunctionCallMessage(MessageClass, BaseModel):
    __message_type__ = MessageType.FUNCTION_CALL.value

    msg_id: str = Field(default_factory=uuid, description="message id")
    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="payload type key to payload item. payload shall be a strong-typed dict"
    )
    role: str = Field(default="", description="who send the message")
    caller: FunctionCaller

    def to_message(self) -> Message:
        return Message.new_tail(
            type_=self.__message_type__,
            msg_id=self.msg_id,
            role=self.role,
            name=self.caller.name,
            call_id=self.caller.id,
            content=self.caller.arguments,
        )

    @classmethod
    def from_message(cls, message: Message) -> Optional[Self]:
        if message.type != cls.__message_type__:
            return None
        return cls(
            msg_id=message.msg_id,
            payloads=message.payloads,
            role=message.role,
            caller=FunctionCaller(
                id=message.call_id,
                name=message.name,
                arguments=message.content,
            )
        )

    def to_openai_param(self, container: Optional[Container], compatible: bool = False) -> List[Dict]:
        from openai.types.chat.chat_completion_assistant_message_param import (
            ChatCompletionAssistantMessageParam, FunctionCall,
        )
        from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam

        return [ChatCompletionAssistantMessageParam(
            role="assistant",
            tool_calls=[ChatCompletionMessageToolCallParam(
                id=self.caller.id,
                function=FunctionCall(
                    name=self.caller.name,
                    arguments=self.caller.arguments,
                ),
                type="function"
            )]
        )]


class VariableMessage(MessageClass, BaseModel):
    """
    变量类型消息.
    """

    __message_type__ = MessageType.VARIABLE.value

    msg_id: str = Field(default_factory=uuid, description="message id")
    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="payload type key to payload item. payload shall be a strong-typed dict"
    )
    role: str = Field(default="", description="who send the message")
    name: Optional[str] = Field(None, description="who send the message")
    attrs: Variables.Var = Field(
        description="variable pointer info"
    )

    def to_message(self) -> Message:
        message = Message.new_tail(
            type_=MessageType.VARIABLE.value,
            content="",
            role=self.role,
            name=self.name,
            attrs=self.attrs.model_dump(),
            msg_id=self.msg_id,
        )
        message.payloads = self.payloads
        return message

    @classmethod
    def from_message(cls, message: Message) -> Optional[Self]:
        if message.type != MessageType.VARIABLE.value:
            return None

        obj = cls(
            msg_id=message.msg_id,
            role=message.role,
            name=message.name,
            attrs=message.attrs,
            payloads=message.payloads,
        )
        return obj

    def to_openai_param(self, container: Optional[Container], compatible: bool = False) -> List[Dict]:
        content = f"""variable message:
vid: {self.attrs.vid} 
type: {self.attrs.type}
desc: {self.attrs.desc}
"""
        if container and container.bound(Variables) and compatible:
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


class ImageId(BaseModel):
    image_id: str = Field(description="image id")
    detail: Literal["auto", "high", "low"] = Field(default="auto", description="image quality")


class ImageAttrs(BaseModel):
    images: List[ImageId] = Field(default_factory=list, description="file id")


class ImageAssetMessage(MessageClass, BaseModel):
    msg_id: str = Field(default_factory=uuid, description="message id")
    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="payload type key to payload item. payload shall be a strong-typed dict"
    )
    role: str = Field(default="", description="who send the message")
    name: Optional[str] = Field(None, description="who send the message")
    content: Optional[str] = Field("", description="content of the image message")

    attrs: ImageAttrs = Field(description="image assert id")

    __message_type__ = MessageType.IMAGE.value

    def to_message(self) -> Message:
        message = Message.new_tail(
            role=self.role,
            name=self.name,
            content=self.content,
            type_=self.__message_type__,
            attrs=self.attrs.model_dump(),
            msg_id=self.msg_id,
        )
        message.payloads = self.payloads
        return message

    @classmethod
    def from_image_asset(
            cls,
            name: str,
            content: str,
            images: List[FileInfo],
            role: str = Role.USER.value,
    ) -> Self:
        attrs = ImageAttrs(images=[
            ImageId(image_id=image_info.fileid)
            for image_info in images
        ])
        return cls(
            name=name,
            content=content,
            role=role,
            attrs=attrs,
        )

    @classmethod
    def from_message(cls, message: Message) -> Optional[Self]:
        if message.type != cls.__message_type__:
            return None
        return cls(
            msg_id=message.msg_id,
            role=message.role,
            name=message.name,
            content=message.content,
            attrs=message.attrs,
            payloads=message.payloads,
        )

    def to_openai_param(self, container: Optional[Container], compatible: bool = False) -> List[Dict]:
        from openai.types.chat.chat_completion_content_part_text_param import ChatCompletionContentPartTextParam
        from openai.types.chat.chat_completion_content_part_image_param import (
            ChatCompletionContentPartImageParam, ImageURL,
        )
        from openai.types.chat.chat_completion_user_message_param import (
            ChatCompletionUserMessageParam,
        )
        from openai.types.chat.chat_completion_assistant_message_param import (
            ChatCompletionAssistantMessageParam,
        )
        from ghostos.contracts.assets import ImageAssets
        content = self.content
        image_id_and_desc = []
        content_parts = []
        if not compatible and self.attrs is not None and self.attrs.images and container:
            images = container.force_fetch(ImageAssets)
            for image_id_info in self.attrs.images:
                got = images.get_file_and_binary_by_id(image_id_info.image_id)
                if got is None:
                    continue
                image_info, binary = got
                if binary:
                    encoded = base64.b64encode(binary).decode('utf-8')
                    url = f"data:{image_info.filetype};base64,{encoded}"
                else:
                    url = image_info.url
                if not url:
                    continue
                content_parts.append(ChatCompletionContentPartImageParam(
                    type="image_url",
                    image_url=ImageURL(
                        url=url,
                        detail="auto",
                    ),
                ))
                image_id_and_desc.append((image_id_info.image_id, image_info.description))
        if image_id_and_desc:
            attachment = "\n(about follow images:"
            order = 0
            for image_id, desc in image_id_and_desc:
                order += 1
                attachment += f"\n[{order}] id: `{image_id}` desc: `{desc}`"
            content = content + attachment + ")"
            content = content.strip()
        if content:
            content_parts.insert(0, ChatCompletionContentPartTextParam(
                text=content,
                type="text",
            ))

        if self.role == Role.ASSISTANT.value:
            item = ChatCompletionAssistantMessageParam(
                role=Role.ASSISTANT.value,
                content=content_parts,
            )
        else:
            item = ChatCompletionUserMessageParam(
                role=Role.USER.value,
                content=content_parts,
            )
        if self.name:
            item["name"] = self.name
        return [item]


class AudioMessage(MessageClass, BaseModel):
    msg_id: str = Field(default_factory=uuid, description="message id")
    payloads: Dict[str, Dict] = Field(
        default_factory=dict,
        description="payload type key to payload item. payload shall be a strong-typed dict"
    )
    role: str = Field(default="", description="who send the message")
    name: Optional[str] = Field(None, description="who send the message")
    content: str = Field("", description="transcription of the audio message")

    __message_type__ = MessageType.AUDIO.value

    def to_message(self) -> Message:
        message = Message.new_tail(
            role=self.role,
            name=self.name,
            content=self.content,
            type_=self.__message_type__,
            msg_id=self.msg_id,
        )
        message.payloads = self.payloads
        return message

    @classmethod
    def from_message(cls, message: Message) -> Optional[Self]:
        if message.type != cls.__message_type__:
            return None
        return cls(
            msg_id=message.msg_id,
            role=message.role,
            name=message.name,
            content=message.content,
            payloads=message.payloads,
        )

    def to_openai_param(self, container: Optional[Container], compatible: bool = False) -> List[Dict]:
        raise NotImplementedError("todo")


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
            call_id: Optional[str] = None,
    ) -> None:
        self.variables = variables
        self.role = role
        self.call_id = call_id
        self.name = name

    def parse(self, messages: Iterable[Union[MessageKind, Any]]) -> Iterable[Message]:
        for item in messages:
            if isinstance(item, Message):
                yield self._with_ref(item)
            elif isinstance(item, MessageClass):
                msg = item.to_message()
                yield self._with_ref(msg)
            elif isinstance(item, str):
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
        if self.call_id is not None:
            item.call_id = self.call_id
        if not item.role and self.role:
            item.role = self.role
        if not item.name and self.name:
            item.name = self.name
        return item
