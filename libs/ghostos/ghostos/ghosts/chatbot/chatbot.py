from typing import Union, Iterable, ClassVar, List, Optional
from ghostos.abcd import Agent, GhostDriver, Session, Operator
from ghostos.abcd.thoughts import ActionThought, Thought
from ghostos_container import Provider
from ghostos.core.runtime import Event, GoThreadInfo
from ghostos.core.messages import Role
from ghostos.core.llms import Prompt, LLMFunc
from ghostos_common.entity import ModelEntity
from ghostos_common.prompter import TextPOM, PromptObjectModel
from ghostos_common.identifier import Identifier
from pydantic import Field


class Chatbot(ModelEntity, Agent):
    """
    simplest chatbot that can chat only
    """
    # required fields
    name: str = Field(description="name of the chatbot", pattern=r"^[a-zA-Z0-9_-]+$")
    persona: str = Field(default="", description="persona of the chatbot")
    instruction: str = Field(default="", description="instruction of the chatbot")

    # not required fields
    description: str = Field(default="", description="description of the chatbot")
    llm_api: str = Field(default="", description="llm api of the chatbot")
    history_turns: int = Field(default=20, description="history turns of thread max turns")
    id: Optional[str] = Field(default=None)

    ArtifactType: ClassVar = None
    ContextType: ClassVar = None
    DriverType: ClassVar = None

    def __identifier__(self) -> Identifier:
        return Identifier(
            id=self.id,
            name=self.name,
            description=self.description,
        )


class ChatbotDriver(GhostDriver[Chatbot]):

    def get_artifact(self, session: Session) -> None:
        return None

    def get_system_instruction(self, session: Session) -> str:
        return self.get_system_prompter().get_prompt(session.container)

    def actions(self, session: Session) -> List[LLMFunc]:
        return []

    def providers(self) -> Iterable[Provider]:
        return []

    def parse_event(self, session: Session, event: Event) -> Union[Event, None]:
        return event

    def get_system_prompter(self) -> PromptObjectModel:
        return TextPOM().with_children(
            TextPOM(title="Who are you", content=f"you are `{self.ghost.name}`"),
            TextPOM(title="Your Persona", content=self.ghost.persona),
            TextPOM(title="Your Instruction", content=self.ghost.instruction),
        )

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        method = getattr(self, f"on_{event.type}", None)
        if method is not None:
            return method(session, event)
        return self.default_handle_event(session, event)

    def on_creating(self, session: Session) -> None:
        return

    def thought(self, session: Session) -> Thought:
        thought = ActionThought(llm_api=self.ghost.llm_api)
        return thought

    def prompt(self, session: Session) -> Prompt:
        system_prompter = self.get_system_prompter()
        system_message = Role.SYSTEM.new(content=system_prompter.get_prompt(session.container))
        prompt = session.thread.to_prompt([system_message])
        return prompt

    def truncate(self, session: Session) -> GoThreadInfo:
        thread = session.thread
        if 0 < self.ghost.history_turns < len(thread.history):
            thread.history[-self.ghost.history_turns].summary = ""
        elif self.ghost.history_turns == 0:
            thread.history[-1].summary = ""

        thread.history = thread.history[-self.ghost.history_turns:]
        return thread

    def default_handle_event(self, session: Session, event: Event) -> Union[Operator, None]:
        # update session thread
        session.thread.new_turn(event)
        # get thought
        thought = self.thought(session)
        # get prompt
        prompt = self.prompt(session)

        # take action
        prompt, op = thought.think(session, prompt)
        if op is not None:
            return op
        return session.mindflow().wait()
