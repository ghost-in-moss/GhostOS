from typing import Optional, Iterable, List, TypeVar

from ghostos.container import Container
from ghostos.core.abcd.concepts import Conversation, Scope, Ghost, Session
from ghostos.core.abcd.utils import get_ghost_driver
from ghostos.core.messages import Message
from ghostos.core.runtime import (
    Event, EventTypes,
    GoTaskStruct, TaskLocker, GoTasks,
)
from ghostos.prompter import Prompter
from ghostos.identifier import get_identifier
from ghostos.entity import to_entity_meta

G = TypeVar("G", bound=Ghost)


class ConversationImpl(Conversation[G]):

    def __init__(
            self,
            shell_id: str,
            process_id: str,
            container: Container,
            task: GoTaskStruct,
            task_locker: TaskLocker,
    ):
        self._container = container
        self._scope = Scope(
            shell_id=shell_id,
            process_id=process_id,
            task_id=task.task_id,
            parent_task_id=task.parent_task_id,
        )
        self._task = task
        self._locker = task_locker
        # ghost_id = get_identifier(self._ghost)
        # task_id = ghost_driver.make_task_id(self._scope)
        # tasks = container.force_fetch(GoTasks)
        # task = tasks.get_task(task_id)
        # context_meta = to_entity_meta(context) if context is not None else None
        # if task is None:
        #     task = GoTaskStruct.new(
        #         task_id=task_id,
        #         shell_id=shell_id,
        #         process_id=process_id,
        #         depth=0,
        #         name=ghost_id.name,
        #         description=ghost_id.description,
        #         meta=to_entity_meta(ghost),
        #         context=context_meta,
        #         parent_task_id=None,
        #     )
        # else:
        #     task.meta = to_entity_meta(ghost)
        #     if context_meta:
        #         task.meta = context_meta

    def container(self) -> Container:
        return self._container

    def respond(
            self,
            inputs: Iterable[Message],
            context: Optional[G.Context] = None,
            history: Optional[List[Message]] = None,
    ) -> Iterable[Message]:
        context_meta = to_entity_meta(context) if context is not None else None
        event = EventTypes.INPUT.new(
            task_id=self._task.task_id,
            messages=list(inputs),
            context=context_meta,
        )
        return self.respond_event(event)

    def respond_event(self, event: Event) -> Iterable[Message]:
        pass

    def pop_event(self) -> Optional[Event]:
        pass

    def fail(self, error: Exception) -> bool:
        pass

    def close(self):
        pass

    def closed(self) -> bool:
        pass
