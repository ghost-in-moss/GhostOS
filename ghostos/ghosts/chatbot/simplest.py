from typing import Union, Iterable, ClassVar

from ghostos.abcd import Agent, GhostDriver, Session, Operator
from ghostos.abcd.thoughts import LLMThought
from ghostos.container import Provider
from ghostos.core.runtime import Event
from ghostos.core.messages import Role
from ghostos.entity import ModelEntity
from ghostos.prompter import TextPrmt, Prompter
from ghostos.identifier import Identifier
from pydantic import BaseModel, Field


class Chatbot(ModelEntity, Agent):
    """
    simplest chatbot that can chat only
    """
    name: str = Field(description="name of the chatbot")
    description: str = Field(description="description of the chatbot")
    persona: str = Field(description="persona of the chatbot")
    instruction: str = Field(description="instruction of the chatbot")
    llm_api: str = Field(default="", description="llm api of the chatbot")

    ArtifactType: ClassVar = None
    ContextType: ClassVar = None
    DriverType: ClassVar = None

    def __identifier__(self) -> Identifier:
        return Identifier(
            id=None,
            name=self.name,
            description=self.description,
        )


class ChatbotDriver(GhostDriver[Chatbot]):

    def get_artifact(self, session: Session) -> None:
        return None

    def providers(self) -> Iterable[Provider]:
        return []

    def parse_event(self, session: Session, event: Event) -> Union[Event, None]:
        return event

    def get_system_prompter(self) -> Prompter:
        return TextPrmt().with_children(
            TextPrmt(title="Persona", content=self.ghost.persona),
            TextPrmt(title="Instruction", content=self.ghost.instruction),
        )

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        thought = LLMThought(llm_api=self.ghost.llm_api)

        system_prompter = self.get_system_prompter()
        system_message = Role.SYSTEM.new(content=system_prompter.get_prompt(session.container))
        prompt = session.thread.to_prompt([system_message])
        prompt, op = thought.think(session, prompt)
        if op is not None:
            return op
        return session.taskflow().wait()
