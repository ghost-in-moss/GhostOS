import time
from typing import Iterable, Optional, Type, ClassVar
from abc import ABC, abstractmethod
from openai.types.chat.chat_completion_chunk import ChoiceDelta, ChatCompletionChunk
from openai.types.completion_usage import CompletionUsage
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_assistant_message_param import ChatCompletionAssistantMessageParam, FunctionCall
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from openai.types.chat.chat_completion_function_message_param import ChatCompletionFunctionMessageParam
from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam

from ghostiss.core.messages.message import Message, DefaultMessageTypes, Role, Caller, PayloadItem
from ghostiss.container import Provider, Container, ABSTRACT
from pydantic import BaseModel, Field

__all__ = ["OpenAIMessageParser", "DefaultOpenAIMessageParser", "DefaultOpenAIParserProvider"]


class OpenAIMessageParser(ABC):
    """
    用来对齐 openai 的协议.
    """

    @abstractmethod
    def parse_message(self, message: Message) -> Iterable[ChatCompletionMessageParam]:
        """
        将 message 转换为 openai 的请求入参.
        """
        pass

    def parse_message_list(self, messages: Iterable[Message]) -> Iterable[ChatCompletionMessageParam]:
        """
        将多条消息转换成 openai 的多条入参.
        """
        for message in messages:
            items = self.parse_message(message)
            for item in items:
                yield item

    @abstractmethod
    def from_chat_completion(self, message: ChatCompletionMessage) -> Message:
        """
        将 openai chat completion 转换.
        """
        pass

    @abstractmethod
    def from_chat_completion_chunks(self, messages: Iterable[ChatCompletionChunk]) -> Iterable[Message]:
        """
        将 openai 的 delta 转换过来.
        """
        pass


class CompletionUsagePayload(CompletionUsage, PayloadItem):
    """
    将每个包的开销记录下来.
    """
    key: ClassVar[str] = "completion_usage"

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
    默认的 parser, 只做了极简的实现.
    """

    def parse_message(self, message: Message) -> Iterable[ChatCompletionMessageParam]:
        if message.type == DefaultMessageTypes.CHAT_COMPLETION:
            return self._parse_assistant_chat_completion(message)
        else:
            return self._parse_message(message)

    def _parse_message(self, message: Message) -> Iterable[ChatCompletionMessageParam]:
        if message.role == Role.ASSISTANT:
            return self._parse_assistant_chat_completion(message)
        elif message.role == Role.SYSTEM:
            return [
                ChatCompletionSystemMessageParam(content=message.get_content(), name=message.name, role="system")
            ]
        elif message.role == Role.USER:
            return [
                ChatCompletionUserMessageParam(content=message.get_content(), name=message.name, role="user")
            ]
        elif message.role == Role.FUNCTION:
            return [
                ChatCompletionFunctionMessageParam(content=message.get_content(), name=message.name, role="function")
            ]
        elif message.role == Role.TOOL:
            return [
                ChatCompletionToolMessageParam(
                    tool_call_id=message.ref_id,
                    content=message.get_content(),
                    role="tool",
                )
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

        return [ChatCompletionAssistantMessageParam(
            content=content,
            role="assistant",
            function_call=function_call,
            tool_calls=tool_calls,
        )]

    def from_chat_completion(self, message: ChatCompletionMessage) -> Message:
        pack = Message.new_tail(type_=DefaultMessageTypes.CHAT_COMPLETION, role=message.role, content=message.content)
        if message.function_call:
            caller = Caller(
                name=message.function_call.name,
                arguments=message.function_call.arguments,
                protocol=True
            )
            caller.add(pack)
        if message.tool_calls:
            for tool_call in message.tool_calls:
                caller = Caller(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=tool_call.function.arguments,
                    protocol=True,
                )
                caller.add(pack)
        return pack

    def from_chat_completion_chunks(self, messages: Iterable[ChatCompletionChunk]) -> Iterable[Message]:
        # 创建首包, 并发送.
        first = True
        for item in messages:
            if len(item.choices) == 0:
                # 接受到了 openai 协议尾包. 但在这个协议里不作为尾包发送.
                usage = CompletionUsagePayload.from_chunk(item)
                pack = Message.new_pack(role=Role.ASSISTANT.value, typ_=DefaultMessageTypes.CHAT_COMPLETION)
                usage.set(pack)
                yield pack
            else:
                choice = item.choices[0]
                delta = choice.delta
                pack = self._new_pack_from_delta(delta, first)
                yield pack
            first = False

    @staticmethod
    def _new_pack_from_delta(delta: ChoiceDelta, first: bool) -> Message:
        if first:
            pack = Message.new_head(role=Role.ASSISTANT.value, content=delta.content,
                                    typ_=DefaultMessageTypes.CHAT_COMPLETION)
        else:
            pack = Message.new_pack(role=Role.ASSISTANT.value, content=delta.content,
                                    typ_=DefaultMessageTypes.CHAT_COMPLETION)
        # function call
        if delta.function_call:
            function_call = Caller(**delta.function_call.model_dump())
            pack.callers.append(function_call)

        # tool calls
        if delta.tool_calls:
            for item in delta.tool_calls:
                tool_call = Caller(**item.tool_call.model_dump())
                pack.callers.append(tool_call)
        return pack


class DefaultOpenAIParserProvider(Provider):
    """
    默认的 provider.
    """

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[ABSTRACT]:
        return OpenAIMessageParser

    def factory(self, con: Container) -> Optional[ABSTRACT]:
        return DefaultOpenAIMessageParser()
