from typing import Iterable

from ghostos.core.ghosts import Ghost, Action
from ghostos.core.ghosts.thoughts import ModelThought
from ghostos.thoughts.basic import LLMThoughtDriver
from pydantic import Field

from ghostos.core.llms import LLMApi
from ghostos.core.runtime import Event

__all__ = ["ChatThought", "ChatThoughtDriver"]


class ChatThought(ModelThought):
    """
    Simple Chat Thought
    """
    llm_api: str = Field(default="", description="llm api name")
    instruction: str = Field(default="", description="instruction for the llm")


class ChatThoughtDriver(LLMThoughtDriver[ChatThought]):

    def get_llmapi(self, g: Ghost) -> LLMApi:
        llm_api_name = self.thought.llm_api
        return g.llms().get_api(llm_api_name)

    def actions(self, g: Ghost, e: Event) -> Iterable[Action]:
        return []

    def instruction(self, g: Ghost, e: Event) -> str:
        return self.thought.show_instruction
