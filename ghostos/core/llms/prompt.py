from __future__ import annotations

import time
from abc import ABC, abstractmethod

from typing import List, Iterable, Optional, Union, Callable, Self
from openai.types.chat.completion_create_params import Function, FunctionCall
from openai import NotGiven, NOT_GIVEN
from openai.types.chat.chat_completion_function_call_option_param import ChatCompletionFunctionCallOptionParam
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam

from pydantic import BaseModel, Field
from ghostos import helpers
from ghostos.core.messages import Message, Role, Payload
from .tools import LLMFunc, FunctionalToken

__all__ = [
    'Prompt', 'PromptPipe',
    'run_prompt_pipeline',
    'PromptStorage',
    'PromptPayload',
]


# ---- api objects ---- #

class Prompt(BaseModel):
    """
    模拟对话的上下文.
    """
    id: str = Field(default_factory=helpers.uuid, description="trace id")
    description: str = Field(default="description of this prompt")

    system: List[Message] = Field(default_factory=list, description="system messages")
    history: List[Message] = Field(default_factory=list)
    inputs: List[Message] = Field(default_factory=list, description="input messages")
    appending: List[Message] = Field(default_factory=list, description="appending messages")

    functions: List[LLMFunc] = Field(default_factory=list)
    function_call: Optional[str] = Field(default=None, description="function call")

    # deprecated
    functional_tokens: List[FunctionalToken] = Field(default_factory=list)

    # system info
    output: List[Message] = Field(default_factory=list)
    error: Optional[str] = Field(default=None, description="error message")
    created: float = Field(default_factory=lambda: round(time.time(), 4))

    def system_prompt(self) -> str:
        contents = []
        if self.system:
            contents = []
            for message in self.system:
                contents.append(message.get_content())
        return "\n\n".join(contents)

    def get_messages(self, with_system: bool = True) -> List[Message]:
        """
        返回所有的消息.
        """
        messages = []
        # combine system messages into one
        if with_system and self.system:
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

    def add(self, messages: Iterable[Message]) -> Iterable[Message]:
        for msg in messages:
            if msg.is_complete():
                self.appending.append(msg.get_copy())
            yield msg

    def fork(
            self,
            inputs: List[Message],
            system: Optional[List[Message]] = None,
            description: str = "",
            prompt_id: Optional[str] = None,
            functions: Optional[List[Function]] = None,
            function_call: Optional[str] = None,
    ) -> Prompt:
        """
        fork current prompt.
        """
        prompt_id = prompt_id or helpers.uuid()
        description = description
        copied = self.model_copy(update={
            "id": prompt_id,
            "description": description,
        }, deep=True)
        if copied.inputs:
            copied.history.extend(copied.inputs)
            copied.inputs = inputs
        if copied.appending:
            copied.history.extend(copied.appending)
            copied.appending = []
        if system:
            copied.system = system
        if functions:
            copied.functions = functions
        if function_call is not None:
            copied.function_call = function_call
        return copied


class PromptPayload(Payload):
    key = "prompt_info"

    pid: str = Field(description="created from prompt")
    desc: str = Field(default="description of the prompt")

    @classmethod
    def from_prompt(cls, prompt: Prompt) -> Self:
        return cls(pid=prompt.id, desc=prompt.description)


class PromptPipe(ABC):
    """
    用来对 chat message 做加工.
    基本思路是, 尽可能保证消息体本身的一致性, 在使用的时候才对消息结构做调整.
    """

    @abstractmethod
    def update_prompt(self, prompt: Prompt) -> Prompt:
        pass


def run_prompt_pipeline(prompt: Prompt, pipeline: Iterable[PromptPipe]) -> Prompt:
    """
    通过多个 filter 来加工 chat.
    """
    for f in pipeline:
        prompt = f.update_prompt(prompt)
    return prompt


class PromptStorage(ABC):
    """
    save and get prompt
    """

    @abstractmethod
    def save(self, prompt: Prompt) -> None:
        pass

    @abstractmethod
    def get(self, prompt_id: str) -> Optional[Prompt]:
        pass
