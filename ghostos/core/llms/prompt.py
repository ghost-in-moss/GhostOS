from __future__ import annotations

from abc import ABC, abstractmethod

from typing import List, Iterable, Optional, Union, Callable, Set
from typing_extensions import Self
from openai.types.chat.completion_create_params import Function, FunctionCall
from openai import NotGiven, NOT_GIVEN
from openai.types.chat.chat_completion_function_call_option_param import ChatCompletionFunctionCallOptionParam
from openai.types.shared_params.function_definition import FunctionDefinition
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam

from pydantic import BaseModel, Field
from ghostos_common import helpers
from ghostos.core.messages import Message, Role, Payload
from ghostos_common.helpers import timestamp, uuid
from ghostos.core.llms.configs import ModelConf
from ghostos.core.llms.tools import LLMFunc, FunctionalToken

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
    added: List[Message] = Field(default_factory=list, description="appending messages")

    functions: List[LLMFunc] = Field(default_factory=list)
    function_call: Optional[str] = Field(default=None, description="function call")

    # deprecated
    functional_tokens: List[FunctionalToken] = Field(default_factory=list)

    # system debug info
    error: Optional[str] = Field(default=None, description="error message")
    created: int = Field(default_factory=timestamp)
    model: Optional[ModelConf] = Field(default=None, description="model conf")
    run_start: float = Field(default=0.0, description="start time")
    first_token: float = Field(default=0.0, description="first token")
    run_end: float = Field(default=0.0, description="end time")
    request_params: str = Field(default="", description="real request params")

    @classmethod
    def new_from_messages(
            cls,
            messages: List[Message],
    ) -> Prompt:
        return Prompt(history=messages)

    def system_prompt(self) -> str:
        contents = []
        if self.system:
            contents = []
            for message in self.system:
                contents.append(message.get_content())
        return "\n\n".join(contents)

    def get_messages(self, with_system: bool = True, stages: Optional[List[str]] = None) -> List[Message]:
        """
        返回所有的消息.
        """
        messages = []
        if stages:
            stage_set = set(stages)
        else:
            stage_set = set()

        # combine system messages into one
        if with_system and self.system:
            system_message = Role.SYSTEM.new(content=self.system_prompt())
            messages = join_messages_by_stages(messages, stage_set, system_message)
        if self.history:
            messages = join_messages_by_stages(messages, stage_set, *self.history)
        if self.inputs:
            messages = join_messages_by_stages(messages, stage_set, *self.inputs)
        if self.added:
            messages = join_messages_by_stages(messages, stage_set, *self.added)
        return messages

    def filter_messages(self, filter_: Callable[[Message], Optional[Message]]) -> None:
        self.system = self._filter_messages(self.system, filter_)
        self.history = self._filter_messages(self.history, filter_)
        self.inputs = self._filter_messages(self.inputs, filter_)
        self.added = self._filter_messages(self.added, filter_)
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
            openai_func = Function(
                name=func.name,
                description=func.description,
                parameters=func.parameters,
            )
            functions.append(openai_func)
        if not functions:
            return NOT_GIVEN
        return functions

    def get_openai_tools(self) -> Union[List[ChatCompletionToolParam], NotGiven]:
        if not self.functions:
            return NOT_GIVEN
        tools = []
        for func in self.functions:
            openai_func = FunctionDefinition(
                name=func.name,
                description=func.description,
                parameters=func.parameters,
            )
            tool = ChatCompletionToolParam(function=openai_func, type="function")
            tools.append(tool)
        if not tools:
            return NOT_GIVEN
        return tools

    def get_openai_function_call(self) -> Union[FunctionCall, NotGiven]:
        if not self.functions:
            return NOT_GIVEN
        if self.function_call is None:
            return ChatCompletionFunctionCallOptionParam(name="auto")
        return ChatCompletionFunctionCallOptionParam(name=self.function_call)

    def add(self, messages: Iterable[Message]) -> Iterable[Message]:
        for msg in messages:
            if msg.is_complete():
                self.added.append(msg.get_copy())
            yield msg

    def filter_stages(self, stages: Optional[List[str]] = None) -> Self:
        if not stages:
            return self
        stages = set(stages)
        copied = self.model_copy(deep=True)
        if stages:
            copied.history = join_messages_by_stages([], stages, *copied.history)
            copied.inputs = join_messages_by_stages([], stages, *copied.inputs)
            copied.added = join_messages_by_stages([], stages, *copied.added)
        return copied

    def get_new_copy(self, prompt_id: Optional[str] = None) -> Prompt:
        prompt = self.model_copy(deep=True)
        if not prompt_id:
            prompt_id = uuid()
        prompt.id = prompt_id
        return prompt

    def fork(
            self,
            inputs: Optional[List[Message]],
            *,
            system: Optional[List[Message]] = None,
            description: str = "",
            prompt_id: Optional[str] = None,
            functions: Optional[List[Function]] = None,
            function_call: Optional[str] = None,
            stages: Optional[List[str]] = None,
    ) -> Prompt:
        """
        fork current prompt.
        todo: rebuild
        """
        prompt_id = prompt_id or helpers.uuid()
        description = description
        copied = self.filter_stages(stages)
        copied.id = prompt_id
        copied.description = description
        if inputs is not None:
            copied.history.extend(copied.inputs)
            copied.history.extend(copied.added)
            copied.inputs = inputs
            copied.added = []
        if system:
            copied.system = system
        if functions:
            copied.functions = functions
        if function_call is not None:
            copied.function_call = function_call
        return copied


class PromptPayload(Payload):
    key = "prompt_info"

    prompt_id: str = Field(description="created from prompt")
    desc: str = Field(default="description of the prompt")

    @classmethod
    def from_prompt(cls, prompt: Prompt) -> Self:
        return cls(prompt_id=prompt.id, desc=prompt.description)


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


def join_messages_by_stages(messages: List[Message], stages: Set[str], *join: Message) -> List[Message]:
    for msg in join:
        if msg.is_empty() or not msg.is_complete():
            continue
        if not stages or msg.stage in stages:
            messages.append(msg)
    return messages


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
