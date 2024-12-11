from typing import Optional, TypeVar, Dict, Any, Iterable
from .agent import MossAgent
from ghostos.core.moss import Moss, MossRuntime
from ghostos.abcd.concepts import Session, Operator
from ghostos.core.runtime import GoThreadInfo, Event
from ghostos.container import Provider

A = TypeVar("A")


# <moss-hide>
# lifecycle methods for developer.
# agent need not know details about these methods, but also ok.
# hide these methods because too much ghostos designing patterns are needed.

def __moss_agent_providers__(agent: A) -> Iterable[Provider]:
    """
    return session level providers that special required to the Agent.
    :param agent: the moss agent instance.
    :return: providers that register to the session container.
    """
    return []


def __moss_agent_creating__(agent: A, session: Session) -> None:
    pass


def __moss_agent_truncate__(agent: MossAgent, session: Session) -> GoThreadInfo:
    """
    default truncate logic of the agent
    :param agent:
    :param session:
    :return:
    """
    from ghostos.abcd.thoughts import SummaryThought
    from ghostos.core.llms import Prompt

    thread = session.thread
    turns = thread.get_history_turns(True)
    # do the truncate
    if len(turns) > agent.truncate_at_turns:
        # the history turns to remove
        truncated = agent.truncate_at_turns - agent.truncate_to_turns
        if truncated <= 0:
            return thread
        turns = turns[:truncated]
        # last turn of the truncated turns
        if len(turns) < 1:
            return thread
        target = turns[-1]
        messages = []
        for turn in turns:
            messages.extend(turn.messages(False))
        prompt = Prompt(history=messages)
        _, summary = SummaryThought(llm_api=agent.llm_api).think(session, prompt)
        if summary:
            target.summary = summary
    return session.thread


def __moss_agent_parse_event__(agent: MossAgent, session: Session, event: Event) -> Optional[Event]:
    return event


def __moss_agent_injections__(agent: A, session: Session[A]) -> Dict[str, Any]:
    """
    manually define some of the injections to the Moss Class.
    if a property of Moss is not injected here, the session container will inject it by typehint.
    :param agent:
    :param session:
    """
    return {
    }


def __moss_agent_on_event_type__(
        agent: MossAgent,
        session: Session[A],
        runtime: MossRuntime,
        event: Event,
) -> Optional[Operator]:
    """
    define customized event handler
    :param agent:
    :param session:
    :param runtime:
    :param event:
    :return:
    """
    pass

# </moss-hide>
