from typing import Optional, Iterable, List, Callable, Self, ClassVar, Union, Type, TypeVar, Generic
from abc import ABC, abstractmethod
from ghostos.identifier import Identical, Identifier, EntityMeta, to_entity_meta, get_identifier
from ghostos.core.runtime import (
    Event, Session, GoTaskStruct, Runtime,
)
from ghostos.core.messages import Message
from ghostos.core.llms import Prompt, LLMApi
from ghostos.container import Container, Contracts
from ghostos.core.abcd.ghostos import Ghost, GhostDriver, Operator
from ghostos.core.abcd.ghosts import Agent
from ghostos.core.abcd.utils import make_unique_ghost_id


def make_agent_task_id(runtime: Runtime, agent: Agent, parent_task_id: Optional[str] = None) -> str:
    """
    agent is singleton to its parent.
    """
    parent_task_id = parent_task_id if parent_task_id else ""
    id_ = get_identifier(agent)
    task_id = make_unique_ghost_id(
        runtime.shell_id,
        process_id=runtime.process_id,
        parent_task_id=parent_task_id,
        agent_name=id_.name,
    )
    return task_id


def update_session_with_event(session: Session, event: Event):
    thread = session.thread()
    thread.new_turn(event)
    session.update_thread(thread)
