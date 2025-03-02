from typing import TypeVar, Iterable
from .agent import MossAgent
from ghostos_moss import Moss
from ghostos.abcd import Action, Thought, ActionThought

A = TypeVar("A")


# --- lifecycle methods for meta agent --- #


def __moss_agent_artifact__(agent: MossAgent, moss: Moss):
    """
    get the agent artifact, default is None

    Artifact is what an Agent is producing. Like return value of a function.
    But I want the production of an agent is altering during the runtime,
    So I can see what going on, and intercept an automatic agent if necessary.
    """
    return None


def __moss_agent_actions__(agent: MossAgent, moss: Moss) -> Iterable[Action]:
    """
    define the actions that agent equipped.
    but I prefer let the agent do everything with code,
    So the Only needed Action is MossAction.
    """
    yield from []


def __moss_agent_persona__(agent: MossAgent, moss: Moss) -> str:
    """
    return the persona of the agent, which is showed in agent's system instruction.
    consider this, if moss.persona is a defined str attr of Moss, the Agent can modify it by MossAction.
    so the moss agent can easily modify itself persona.
    """
    return agent.persona


def __moss_agent_instruction__(agent: MossAgent, moss: Moss) -> str:
    """
    return the instruction string of the agent.
    """
    return agent.instruction


def __moss_agent_thought__(agent: MossAgent, moss: Moss, *actions: Action) -> Thought:
    """
    GhostOS separate single turn `Thought` and Multi-turns `Agent`.
    So the Agent (or Ghost) can conversation in multiple turns with the GoThreadInfo which saved history.
    But in a single turn, the GoThreadInfo will convert to LLM Prompt instance, and run by Thought.

    We can combine multiple Thought to a pipeline, graph or parallel tree to implements Single-turn Chain of Thought.

    take moderation for example:
    1. first thought:  quick thought to judge the user input is legal to respond.
    2. second thought:  think about what to reply
    3. end thought: reflect the reply, if illegal, re-think it.

    we can easily build this pipeline by code.
    """
    return ActionThought(
        llm_api=agent.llm_api,
        actions=actions,
        message_stage="",
    )
