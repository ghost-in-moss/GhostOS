from typing import Optional, TypeVar, Generic, Type
from abc import ABC, abstractmethod
from ghostos.common import Identifiable, Identifier
from ghostos.core.ghosts import Ghost
from ghostos.core.ghosts.thoughts import Thought, ModelThought
from ghostos.helpers import generate_import_path, md5, import_from_path
from pydantic import BaseModel, Field

__all__ = [
    'Assistant',
    'AssistantDriver',
    'get_assistant_driver',
    'get_assistant_driver_type',
    'BasicAssistant',
    'BasicAssistantDriver',
]


class Assistant(Identifiable, ABC):
    """
    Assistant is a special thinking unit in Ghost.
    Each assistant has a unique identifier, is a singleton instance in the Process.
    You can talk to a agent through MultiAssistant library.
    """

    __assistant_driver__: Optional[Type["AssistantDriver"]] = None


A = TypeVar("A", bound=Assistant)


class AssistantDriver(Generic[A], ABC):

    def __init__(self, assistant: A):
        self.assistant = assistant

    @abstractmethod
    def meta_prompt(self, g: Ghost) -> str:
        pass

    @abstractmethod
    def root_thought(self, g: Ghost) -> Thought:
        pass

    def task_id(self, g: Ghost) -> str:
        """
        generate unique task id for assistant instance in the process
        """
        process_id = g.session().process().process_id
        name = self.assistant.identifier().name
        assistant_type = generate_import_path(type(self.assistant))
        thought_type = generate_import_path(type(self.root_thought(g)))
        # hash a singleton id of the assistant task.
        return md5(f"{process_id}-{assistant_type}-{thought_type}-{name}")


def get_assistant_driver_type(assistant: A) -> Type[AssistantDriver]:
    """
    get assistant driver instance
    :param assistant:
    :return:
    """
    if assistant.__assistant_driver__ is not None:
        return assistant.__assistant_driver__
    assistant_import_path = generate_import_path(type(assistant))
    driver_path = assistant_import_path + "Driver"
    driver = import_from_path(driver_path)
    return driver


def get_assistant_driver(assistant: A) -> AssistantDriver[A]:
    driver_type = get_assistant_driver_type(assistant)
    return driver_type(assistant)


class BasicAssistant(Assistant, BaseModel):
    """
    the basic assistant that use model thought as root thought
    """

    name: str = Field(description="the name of the assistant")
    description: str = Field(description="the description of the assistant about it usage")
    prompt: str = Field(description="the meta prompt of the assistant")
    thought: ModelThought = Field(description="the thought of the assistant")

    def identifier(self) -> Identifier:
        import_path = generate_import_path(type(self))
        return Identifier(
            id=f"{import_path}-{self.name}",
            name=self.name,
            description=self.description,
        )


class BasicAssistantDriver(AssistantDriver[BasicAssistant]):

    def meta_prompt(self, g: Ghost) -> str:
        return self.assistant.prompt

    def root_thought(self, g: Ghost) -> Thought:
        return self.assistant.thought
