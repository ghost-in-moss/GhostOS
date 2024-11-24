from typing import Optional, TypeVar, Dict, Any, Iterable
from .agent import MossAgent
from ghostos.core.moss import Moss
from ghostos.abcd import Session, Action, Thought, LLMThought
from ghostos.prompter import Prompter
from ghostos.core.runtime import GoThreadInfo
from ghostos.container import Provider, Container

A = TypeVar("A")


# --- lifecycle methods for meta agent --- #


def __moss_agent_artifact__(agent: MossAgent, moss: Moss):
    """
    get the agent goal, default is None
    """
    return None


def __moss_agent_actions__(agent: MossAgent, moss: Moss) -> Iterable[Action]:
    yield from []


def __moss_agent_persona__(agent: MossAgent, moss: Moss) -> str:
    return agent.persona


def __moss_agent_instruction__(agent: MossAgent, moss: Moss) -> str:
    return agent.instructions


def __moss_agent_thought__(agent: MossAgent, moss: Moss, *actions: Action) -> Thought:
    return LLMThought(
        llm_api=agent.llm_api,
        actions=actions,
        message_stage="",
    )
