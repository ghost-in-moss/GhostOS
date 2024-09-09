from __future__ import annotations

from enum import Enum
from abc import ABC, abstractmethod

from typing import List, Iterable, Dict, Optional, Union, Callable
from openai.types.chat.completion_create_params import Function, FunctionCall
from openai import NotGiven, NOT_GIVEN
from openai.types.chat.chat_completion_function_call_option_param import ChatCompletionFunctionCallOptionParam
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam

from pydantic import BaseModel, Field
from ghostos.abc import Identifiable, Identifier
from ghostos import helpers
from ghostos.core.messages import Message, DefaultMessageTypes, Caller

__all__ = [
    'LLMTool', 'FunctionalToken',
    'Chat', 'ChatPreparer',
    'prepare_chat',
]


# ---- tool and function ---- #

class LLMTool(BaseModel):
    """
    a common wrapper for JSONSchema LLM tool.
    Compatible to OpenAI Tool.
    We need this because OpenAI Tool definition is too dynamic, we need strong typehints.
    """
    id: Optional[str] = Field(default=None, description="The id of the LLM tool.")
    name: str = Field(description="function name")
    description: str = Field(default="", description="function description")
    parameters: Optional[Dict] = Field(default=None, description="function parameters")

    @classmethod
    def new(cls, name: str, desc: Optional[str] = None, parameters: Optional[Dict] = None):
        if parameters is None:
            parameters = {"type": "object", "properties": {}}
        properties = parameters.get("properties", {})
        params_properties = {}
        for key in properties:
            _property = properties[key]
            if "title" in _property:
                del _property["title"]
            params_properties[key] = _property
        parameters["properties"] = params_properties
        if "title" in parameters:
            del parameters["title"]
        return cls(name=name, description=desc, parameters=parameters)


class FunctionalTokenMode(str, Enum):
    XML = "xml"
    """ xml 模式, 使用 <name> </name> 包起来的是内容. """
    TOOL = "tool"
    """ tool mod, 使用 llm tool 进行封装. """
    TOKEN = "token"
    """ token mod. use single token to parse content. """


class FunctionalToken(Identifiable, BaseModel):
    """
    functional token means to provide function ability to LLM not by JsonSchema, but by token.
    LLM generates special tokens (such as XML marks) to indicate further tokens are the content of the function.
    LLMDriver shall define which way to prompt the functional token usage such as xml.
    """

    token: str = Field(description="token that start the function content output")
    end_token: str = Field(default="", description="end token that close the function content output")
    name: str = Field(description="name of the function")
    description: str = Field(default="", description="description of the function")
    visible: bool = Field(default=False, description="if the functional token and the parameters are visible to user")
    parameters: Optional[Dict] = Field(default=None, description="functional token parameters")

    def new_caller(self, arguments: str) -> "Caller":
        """
        generate new caller by functional token, usually used in tests.
        """
        return Caller(
            name=self.name,
            arguments=arguments,
            functional_token=True,
        )

    def identifier(self) -> Identifier:
        """
        identifier of the functional token.
        """
        return Identifier(
            name=self.name,
            description=self.description,
        )

    def as_tool(self) -> LLMTool:
        """
        all functional token are compatible to a llm tool.
        """
        return LLMTool.new(name=self.name, desc=self.description, parameters=self.parameters)


# ---- api objects ---- #

class Chat(BaseModel):
    """
    模拟对话的上下文.
    """
    id: str = Field(default_factory=helpers.uuid, description="trace id")

    system: List[Message] = Field(default_factory=list, description="system messages")
    history: List[Message] = Field(default_factory=list)
    inputs: List[Message] = Field(default_factory=list, description="input messages")
    appending: List[Message] = Field(default_factory=list, description="appending messages")

    functions: List[LLMTool] = Field(default_factory=list)
    functional_tokens: List[FunctionalToken] = Field(default_factory=list)
    function_call: Optional[str] = Field(default=None, description="function call")

    def get_messages(self) -> List[Message]:
        """
        返回所有的消息.
        """
        messages = []
        if self.system:
            messages.extend(self.system)
        if self.history:
            messages.extend(self.history)
        if self.inputs:
            messages.extend(self.inputs)
        if self.appending:
            messages.extend(self.appending)
        return messages

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
