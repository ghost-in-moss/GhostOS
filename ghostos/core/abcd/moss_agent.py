from __future__ import annotations
from typing import Tuple, Optional, Protocol, Any, Self, Iterable, List, Dict, Union, Callable, Any
from types import ModuleType

from ghostos.common import Identifier, Identical, get_identifier
from ghostos.core.llms import Prompt, PromptPipe, LLMApi, LLMs
from ghostos.core.messages import Message, Caller, Role
from ghostos.core.session import Session, GoThreadInfo, Event
from ghostos.core.abcd.ghostos import Ghost, GhostDriver, Operator, G
from ghostos.core.session.session import SessionProps
from ghostos.core.moss import MossRuntime, MossCompiler, Moss
from ghostos.helpers import generate_import_path, import_from_path, join_import_module_and_spec, uuid, unwrap
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import inspect


class MossAgent(BaseModel, Ghost):
    """
    An Agent defined by a single python file
    """

    Goal = None

    module_name: str = Field(
        description="the python module name of the MossAgent located."
    )

    name: str = Field(
        default="",
        description="The name of the agent, if empty, the source will be it's name if agent instance is missing",
    )
    description: str = Field(
        default="",
        description="The description of the agent. can also defined by __description__ in the source file",
    )
    id: Optional[str] = Field(
        default=None,
        description="if not none, the agent is singleton to the shell",
    )

    @abstractmethod
    def __identifier__(self) -> Identifier:
        # check if the module exists
        agent_id = self.id
        name = self.module_name
        if self.name:
            name = self.name
        description = self.description
        return Identifier(
            id=agent_id,
            name=name,
            description=description,
        )


def __goal__(moss: Moss) -> Any:
    return None


def __thought__(moss: Moss, props: dict) -> str:
    pass


class MossAgentDriver(GhostDriver[MossAgent]):
    """
    default moss agent driver.
    """

    def __init__(self, ghost: MossAgent):
        super().__init__(ghost)
        self._module = import_from_path(ghost.module_name)

    def get_goal(self, session: Session) -> Optional[G.Goal]:
        if __goal__.__name__ in self._module.__dict__:
            method = getattr(self._module, __goal__.__name__)
            return method(self.ghost, session)
        return __goal__(self.ghost, session)

    def instructions(self, session: Session) -> List[Message]:
        if self.ghost.__instruction__:
            instruction = self.ghost.__instruction__(self.ghost, session)
        else:
            instruction = self.ghost.instruction
        return [Role.SYSTEM.new(content=instruction)]

    def truncate(self, session: Session, thread: GoThreadInfo) -> GoThreadInfo:
        if self.ghost.__truncate__:
            return self.ghost.__truncate__(self.ghost, session, thread)
        return thread

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        thread = session.thread()
        thread = self.truncate(session, thread)

        # update event
        ok = True
        if self.ghost.__update_event__:
            ok = self.ghost.__update_event__(self.ghost, session, thread, event)
        else:
            thread.new_turn(event)
        session.update_thread(thread, False)
        if not ok:
            return None

        # prompt
        system = self.instructions(session)
        prompt = thread.to_prompt(system)

        thoughts = self.thoughts(session)
        for t in thoughts:
            prompt, op = t.think(session, prompt)
            if op is not None:
                return op
        return self.action(session, prompt)

    def thoughts(self, session: Session) -> Iterable[Thought]:
        if self.ghost.__thoughts__:
            return self.ghost.__thoughts__(self.ghost, session)
        return []

    def actions(self, session: Session) -> Dict[str, Action]:
        if self.ghost.__actions__:
            return self.ghost.__actions__(self.ghost, session)
        pass

    def llm_api(self, session: Session) -> LLMApi:
        if self.ghost.__llm_api__:
            return self.ghost.__llm_api__(self.ghost, session)
        return session.container().force_fetch(LLMs).get_api("")

    def action(self, session: Session, prompt: Prompt) -> Optional[Operator]:
        actions = self.actions(session)
        for action in actions.values():
            prompt = action.process(prompt)

        llm_api = self.llm_api(session)
        messenger = session.messenger()
        llm_api.deliver_chat_completion(
            prompt,
            messenger,
        )
        messages, callers = messenger.flush()
        for caller in callers:
            if caller.name in actions:
                action = actions[caller.name]
                op = action.callback(session, caller)
                if op is not None:
                    return op
        return None


MossAgent.__ghost_driver__ = MossAgentDriver


class Action(PromptPipe, ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def callback(self, session: Session, caller: Caller) -> Optional[Operator]:
        pass


class Thought(ABC):

    @abstractmethod
    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        pass
