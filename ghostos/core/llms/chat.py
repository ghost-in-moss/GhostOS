from __future__ import annotations

from abc import ABC, abstractmethod

from typing import List, Iterable, Optional, Union, Callable
from openai.types.chat.completion_create_params import Function, FunctionCall
from openai import NotGiven, NOT_GIVEN
from openai.types.chat.chat_completion_function_call_option_param import ChatCompletionFunctionCallOptionParam
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam

from pydantic import BaseModel, Field
from ghostos import helpers
from ghostos.core.messages import Message, Role
from .tools import LLMTool, FunctionalToken

__all__ = [
    'LLMTool', 'FunctionalToken',
    'Chat', 'ChatPreparer',
    'prepare_chat',
]



# ---- api objects ---- #

class Chat(BaseModel):
    """
    模拟对话的上下文.
    """
    id: str = Field(default_factory=helpers.uuid, description="trace id")
    streaming: bool = Field(default=False, description="streaming mode")

    system: List[Message] = Field(default_factory=list, description="system messages")
    history: List[Message] = Field(default_factory=list)
    inputs: List[Message] = Field(default_factory=list, description="input messages")
    appending: List[Message] = Field(default_factory=list, description="appending messages")

    functions: List[LLMTool] = Field(default_factory=list)
    functional_tokens: List[FunctionalToken] = Field(default_factory=list)
    function_call: Optional[str] = Field(default=None, description="function call")

    def system_prompt(self) -> str:
        contents = []
        if self.system:
            contents = []
            for message in self.system:
                contents.append(message.get_content())
        return "\n\n".join(contents)

    def get_messages(self) -> List[Message]:
        """
        返回所有的消息.
        """
        messages = []
        # combine system messages into one
        if self.system:
            system_message = Role.SYSTEM.new(content=self.system_prompt())
            messages.append(system_message)
        if self.history:
            messages.extend(self.history)
        if self.inputs:
            messages.extend(self.inputs)
        if self.appending:
            messages.extend(self.appending)
        results = []
        for message in messages:
            if message.is_empty():
                continue
            results.append(message)
        return results

    def filter_messages(self, filter_: Callable[[Message], Optional[Message]]) -> None:
        self.system = self._filter_messages(self.system, filter_)
        self.history = self._filter_messages(self.history, filter_)
        self.inputs = self._filter_messages(self.inputs, filter_)
        self.appending = self._filter_messages(self.appending, filter_)
        return

    @staticmethod
    def _filter_messages(
            messages: Iterable[Message], filter_: Callable[[Message], Optional[Message]]
    ) -> List[Message]:
        result = []
        for item in messages:
            item = filter_(item)
            if item is not None:
                result.append(item)
        return result

    def get_openai_functions(self) -> Union[List[Function], NotGiven]:
        if not self.functions:
            return NOT_GIVEN
        functions = []
        for func in self.functions:
            if func.id is not None:
                continue
            openai_func = Function(**func.model_dump())
            functions.append(openai_func)
        return functions

    def get_openai_tools(self) -> Union[List[ChatCompletionToolParam], NotGiven]:
        if not self.functions:
            return NOT_GIVEN
        tools = []
        for func in self.functions:
            if func.id is None:
                continue
            openai_func = Function(**func.model_dump())
            tool = ChatCompletionToolParam(function=openai_func)
            tools.append(tool)
        return tools

    def get_openai_function_call(self) -> Union[FunctionCall, NotGiven]:
        if not self.functions:
            return NOT_GIVEN
        if self.function_call is None:
            return "auto"
        return ChatCompletionFunctionCallOptionParam(name=self.function_call)


class ChatPreparer(ABC):
    """
    用来对 chat message 做加工.
    基本思路是, 尽可能保证消息体本身的一致性, 在使用的时候才对消息结构做调整.
    """

    @abstractmethod
    def prepare_chat(self, chat: Chat) -> Chat:
        pass


def prepare_chat(chat: Chat, updater: Iterable[ChatPreparer]) -> Chat:
    """
    通过多个 filter 来加工 chat.
    """
    for f in updater:
        chat = f.prepare_chat(chat)
    return chat
