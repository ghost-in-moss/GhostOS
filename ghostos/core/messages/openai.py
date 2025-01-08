from typing import Iterable, Optional, Type, ClassVar, List
from abc import ABC, abstractmethod
from openai.types.chat.chat_completion_chunk import ChoiceDelta, ChatCompletionChunk
from openai.types.completion_usage import CompletionUsage
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam
from openai.types.chat.chat_completion_assistant_message_param import ChatCompletionAssistantMessageParam, FunctionCall
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_developer_message_param import ChatCompletionDeveloperMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from openai.types.chat.chat_completion_function_message_param import ChatCompletionFunctionMessageParam
from ghostos.core.messages import (
    Message, MessageType, Role, FunctionCaller, Payload, MessageClass, MessageClassesParser
)
from ghostos.core.messages.message_classes import (
    FunctionOutput, VariableMessage, ImageAssetMessage,
)
from ghostos.contracts.logger import LoggerItf, FakeLogger
from ghostos.container import Provider, Container
from ghostos.helpers import import_class_from_path

__all__ = [
    "OpenAIMessageParser", "DefaultOpenAIMessageParser", "DefaultOpenAIParserProvider",
    "CompletionUsagePayload",
]


class OpenAIMessageParser(ABC):
    """
    a parser for OpenAI messages alignment.
    """

    @abstractmethod
    def parse_message(
            self,
            message: Message,
            types: Optional[List[str]] = None,
    ) -> Iterable[ChatCompletionMessageParam]:
        """
        parse a Message to OpenAI chat completion message form.
        OpenAI's input message (ChatCompletionXXXParam) are different to ChatCompletion types,
        which is exhausting
        """
        pass

    def parse_message_list(
            self,
            messages: Iterable[Message],
            types: Optional[List[str]] = None,
    ) -> Iterable[ChatCompletionMessageParam]:
        """
        syntax suger
        """
        for message in messages:
            items = self.parse_message(message, types)
            for item in items:
                yield item

    @abstractmethod
    def from_chat_completion(self, message: ChatCompletionMessage) -> Message:
        """
        parse a ChatCompletion message to Message.
        Request -> Message -> ChatCompletionXXXXParam --LLM generation--> ChatCompletionXXX --> Message
        """
        pass

    @abstractmethod
    def from_chat_completion_chunks(self, messages: Iterable[ChatCompletionChunk]) -> Iterable[Message]:
        """
        patch the openai Chat Completion Chunks.
        the Realtime API need a new parser.
        """
        pass


class CompletionUsagePayload(CompletionUsage, Payload):
    """
    the strong-typed payload of OpenAI chat completion usage.
    """
    key: ClassVar[str] = "completion_usage"

    @classmethod
    def from_usage(cls, usage: CompletionUsage) -> "CompletionUsagePayload":
        return cls(**usage.model_dump(exclude_defaults=True))

    @classmethod
    def from_chunk(cls, message: ChatCompletionChunk) -> Optional["CompletionUsagePayload"]:
        if message.usage is not None:
            return cls(**message.usage.model_dump(exclude_defaults=True))
        return None

    def join(self, payload: "CompletionUsagePayload") -> "CompletionUsagePayload":
        self.completion_tokens += payload.completion_tokens
        self.total_tokens = self.completion_tokens + self.prompt_tokens
        return self


class DefaultOpenAIMessageParser(OpenAIMessageParser):
    """
    default implementation of OpenAIMessageParser
    """

    def __init__(
            self,
            message_classes: Optional[List[Type[MessageClass]]],
            container: Optional[Container],
    ):
        if message_classes is None:
            message_classes = [
                FunctionOutput,
                VariableMessage,
                ImageAssetMessage,
            ]
        self.class_parser = MessageClassesParser(message_classes)
        self.container: Optional[Container] = container
        self.logger: Optional[LoggerItf] = None
        if container:
            self.logger = container.get(LoggerItf)
        if not self.logger:
            self.logger = FakeLogger()

    def parse_message(
            self,
            message: Message,
            types: Optional[List[str]] = None,
    ) -> Iterable[ChatCompletionMessageParam]:
        if not message.is_complete():
            return []
        compatible = False
        if types is not None:
            types_set = set(types)
            if message.type not in types_set:
                compatible = True

        wrapped = self.class_parser.to_openai_params(message, self.container, compatible)
        if wrapped is not None:
            yield from wrapped
        else:
            yield from self._parse_message(message)

    def _parse_message(self, message: Message) -> Iterable[ChatCompletionMessageParam]:
        if message.type == MessageType.FUNCTION_CALL.value:
            if message.call_id:
                return [
                    ChatCompletionAssistantMessageParam(
                        role="assistant",
                        tool_calls=[ChatCompletionMessageToolCallParam(
                            id=message.call_id,
                            function=FunctionCall(
                                name=message.name,
                                arguments=message.content,
                            ),
                            type="function"
                        )]
                    )
                ]
            else:
                return [
                    ChatCompletionAssistantMessageParam(
                        role="assistant",
                        function_call=FunctionCall(
                            name=message.name,
                            arguments=message.content,
                        )
                    )
                ]
        elif message.type == MessageType.FUNCTION_OUTPUT:
            if message.call_id:
                return [
                    ChatCompletionToolMessageParam(
                        tool_call_id=message.call_id,
                        content=message.content,
                        role="tool",
                    )
                ]
            else:
                return [
                    ChatCompletionFunctionMessageParam(
                        content=message.get_content(),
                        name=message.name,
                        role="function",
                    )
                ]

        if message.role == Role.ASSISTANT:
            return self._parse_assistant_chat_completion(message)
        elif message.role == Role.SYSTEM:
            return [
                ChatCompletionSystemMessageParam(content=message.get_content(), role="system")
            ]
        elif message.role == Role.DEVELOPER:
            return [
                ChatCompletionDeveloperMessageParam(content=message.get_content(), role="developer")
            ]
        elif message.role == Role.USER:
            item = ChatCompletionUserMessageParam(content=message.get_content(), role="user")
            if message.name:
                item["name"] = message.name
            return [
                item
            ]
        else:
            return []

    @staticmethod
    def _parse_assistant_chat_completion(message: Message) -> Iterable[ChatCompletionAssistantMessageParam]:
        if message.is_empty():
            # todo: log warning
            return []
        content = message.get_content()
        # function call
        function_call = None
        # tools call
        tool_calls = None
        if message.callers:
            for caller in message.callers:
                if not caller.functional_token:
                    # 如果不是协议信息, 则不做额外的封装.
                    continue
                if caller.id is None:
                    function_call = FunctionCall(
                        name=caller.name,
                        arguments=caller.arguments,
                    )
                else:
                    if tool_calls is None:
                        tool_calls = []
                    tool_call = ChatCompletionMessageToolCallParam(
                        id=caller.id,
                        function=FunctionCall(
                            name=caller.name,
                            arguments=caller.arguments,
                        ),
                        type="function",
                    )
                    tool_calls.append(tool_call)
        if not content and not function_call and not tool_calls:
            return []
        item = ChatCompletionAssistantMessageParam(
            content=content,
            role="assistant",
            tool_calls=tool_calls,
        )
        if message.name:
            item["name"] = message.name

        return [item]

    def from_chat_completion(self, message: ChatCompletionMessage) -> Message:
        pack = Message.new_tail(type_=MessageType.DEFAULT, role=message.role, content=message.content)
        if message.function_call:
            caller = FunctionCaller(
                name=message.function_call.name,
                arguments=message.function_call.arguments,
                protocol=True
            )
            caller.add(pack)
        if message.tool_calls:
            for tool_call in message.tool_calls:
                caller = FunctionCaller(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=tool_call.function.arguments,
                    protocol=True,
                )
                caller.add(pack)
        return pack

    def from_chat_completion_chunks(self, messages: Iterable[ChatCompletionChunk]) -> Iterable[Message]:
        # 创建首包, 并发送.
        if messages is None:
            return []
        buffer = None
        for item in messages:
            chunk = None
            self.logger.debug("openai parser receive item: %s", item)
            if len(item.choices) == 0:
                # 接受到了 openai 协议尾包. 但在这个协议里不作为尾包发送.
                usage = CompletionUsagePayload.from_chunk(item)
                if usage and buffer:
                    usage.set_payload(buffer)
                    continue
            elif len(item.choices) > 0:
                choice = item.choices[0]
                delta = choice.delta
                chunk = self._new_chunk_from_delta(delta)
            else:
                continue
            self.logger.debug("openai parser parsed chunk: %s", chunk)

            if chunk is None:
                continue
            elif item.id:
                chunk.msg_id = item.id

            if buffer is None:
                buffer = chunk.as_head(copy=True)
                yield buffer.get_copy()
            else:
                patched = buffer.patch(chunk)
                if not patched:
                    yield buffer.as_tail()
                    buffer = chunk.as_head(copy=True)
                    yield buffer.get_copy()
                    continue
                else:
                    buffer = patched
                    yield chunk
                    continue

        if buffer:
            yield buffer.as_tail(copy=False)

    @staticmethod
    def _new_chunk_from_delta(delta: ChoiceDelta) -> Optional[Message]:

        # function call
        if delta.function_call:
            pack = Message.new_chunk(
                typ_=MessageType.FUNCTION_CALL.value,
                name=delta.function_call.name,
                content=delta.function_call.arguments,
            )
            return pack

        # tool calls
        elif delta.content:
            pack = Message.new_chunk(
                role=Role.ASSISTANT.value,
                content=delta.content,
                typ_=MessageType.DEFAULT,
            )
            return pack

        elif delta.tool_calls:
            for item in delta.tool_calls:
                pack = Message.new_chunk(
                    typ_=MessageType.FUNCTION_CALL.value,
                    call_id=item.id,
                    name=item.function.name,
                    content=item.function.arguments,
                )
                return pack
        return None


class DefaultOpenAIParserProvider(Provider[OpenAIMessageParser]):
    """
    默认的 provider.
    """

    def __init__(self, message_classes: Optional[List[str]] = None):
        classes = None
        if message_classes is not None:
            classes = []
            for import_path in message_classes:
                cls = import_class_from_path(import_path, MessageClass)
                classes.append(cls)
        self._message_classes = classes

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[OpenAIMessageParser]:
        return DefaultOpenAIMessageParser(self._message_classes, con)
