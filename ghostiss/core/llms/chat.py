from __future__ import annotations

from enum import Enum
from abc import ABC, abstractmethod

from typing import List, Iterable, Dict, Optional, Union, Callable
from openai.types.chat.completion_create_params import Function, FunctionCall
from openai import NotGiven, NOT_GIVEN
from openai.types.chat.chat_completion_function_call_option_param import ChatCompletionFunctionCallOptionParam
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam

from pydantic import BaseModel, Field
from ghostiss.abc import Identifiable, Identifier
from ghostiss import helpers
from ghostiss.core.messages import Message, DefaultMessageTypes, Caller

__all__ = [
    'LLMTool', 'FunctionalToken',
    'Chat', 'ChatPreparer',
    'update_chat',
]


# ---- tool and function ---- #

class LLMTool(BaseModel):
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
    定义特殊的 token, 用来在流式输出中生成 caller.
    """

    token: str = Field(description="流式输出中标志 caller 的特殊 token. 比如 :moss>\n ")
    name: str = Field(description="caller 的名字. ")
    description: str = Field(description="functional token 的描述")
    deliver: bool = Field(default=False, description="functional token 后续的信息是否要发送. 可以设置不发送. ")
    parameters: Optional[Dict] = Field(default=None, description="functional token parameters")

    def new_caller(self, arguments: str) -> "Caller":
        return Caller(
            name=self.name,
            arguments=arguments,
            functional_token=True,
        )

    def identifier(self) -> Identifier:
        return Identifier(
            name=self.name,
            description=self.description,
        )

    def as_tool(self) -> LLMTool:
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
            contents = []
            for message in self.system:
                content = message.get_content()
                contents.append(content)
            content = "\n\n".join(contents)
            system = DefaultMessageTypes.DEFAULT.new_system(content=content)
            messages.append(system)
        if self.history:
            for item in self.history:
                messages.append(item)
        if self.inputs:
            for item in self.inputs:
                messages.append(item)
        if self.appending:
            for item in self.appending:
                messages.append(item)
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


def update_chat(chat: Chat, updater: Iterable[ChatPreparer]) -> Chat:
    """
    通过多个 filter 来加工 chat.
    """
    for f in updater:
        chat = f.prepare_chat(chat)
    return chat
