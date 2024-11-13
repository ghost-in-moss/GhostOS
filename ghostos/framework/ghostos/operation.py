from __future__ import annotations

from typing import Union, List
from abc import ABC

from ghostos.core.abcd.concepts import Operation, Session, Operator
from ghostos.core.abcd.utils import fire_session_event
from ghostos.core.runtime import TaskState, EventTypes
from ghostos.core.messages import MessageKind, MessageKindParser, Message, Role


class OperationImpl(Operation):

    def __init__(self, parser: MessageKindParser):
        self.parser = parser

    def finish(self, status: str = "", *replies: MessageKind) -> Operator:
        messages = self.parser.parse(replies)
        return FinishOperator(status, list(messages))

    def fail(self, reason: str = "", *replies: MessageKind) -> Operator:
        messages = self.parser.parse(replies)
        return FailOperator(reason, list(messages))

    def wait(self, status: str = "", *replies: MessageKind) -> Operator:
        messages = self.parser.parse(replies)
        return WaitOperator(status, list(messages))

    def observe(self, *messages: MessageKind, instruction: str = "", sync: bool = False) -> Operator:
        messages = self.parser.parse(messages)
        return ObservationOperator(list(messages), instruction, sync)

    def on_error(self, *messages: MessageKind) -> Operator:
        messages = self.parser.parse(messages)
        return ErrorOperator(list(messages))


class AbcOperator(Operator, ABC):

    def __init__(
            self,
            status: str,
            messages: List[Message],
    ):
        self.status = status
        self.messages = messages

    def destroy(self):
        del self.messages


class ErrorOperator(Operator):

    def __init__(self, messages: List[Message]):
        self.messages = messages

    def run(self, session: Session) -> Union[Operator, None]:
        task = session.task
        event = EventTypes.ERROR.new(
            task_id=task.task_id,
            messages=self.messages,
            from_task_id=task.task_id,
            from_task_name=task.name,
        )
        return fire_session_event(session, event)

    def destroy(self):
        del self.messages


class ObservationOperator(Operator):

    def __init__(self, messages: List[Message], instruction: str, sync: bool):
        self.messages = messages
        self.instruction = instruction
        self.sync: bool = sync

    def run(self, session: Session) -> Union[Operator, None]:
        if len(self.messages) == 0 and not self.instruction:
            return None

        task = session.task
        event = EventTypes.ROTATE.new(
            task_id=task.task_id,
            messages=self.messages,
            from_task_id=task.task_id,
            from_task_name=task.name,
            instruction=self.instruction,
        )
        if self.sync:
            return fire_session_event(session, event)
        else:
            msg = Role.SYSTEM.new(content=f"issue observation at turn {task.turns}")
            session.thread.append(msg)
            event.reason = f"receive observation at turn {task.turns}"
            session.fire_events(event)
            return None

    def destroy(self):
        del self.messages


class FailOperator(Operator):
    def __init__(
            self,
            reason: str,
            messages: List[Message],
    ):
        self.reason = reason
        self.messages = messages

    def run(self, session: Session) -> Union[Operator, None]:
        task = session.task
        session.task.state = TaskState.FAILED.value
        session.task.status_desc = f"[FAILED] {self.reason}"
        if task.parent:
            event = EventTypes.FAILURE_CALLBACK.new(
                task_id=task.parent,
                messages=self.messages,
                from_task_id=task.task_id,
                from_task_name=task.name,
                reason=f"task {task.name} is failed: {self.reason}",
            )
            session.fire_events(event)
        elif self.messages:
            session.respond(self.messages)
        return None

    def destroy(self):
        del self.messages


class WaitOperator(AbcOperator, ABC):

    def run(self, session: Session) -> Union[Operator, None]:
        if len(self.messages) > 0:
            task = session.task
            task.state = TaskState.WAITING.value
            task.status_desc = self.status
            if task.parent:
                event = EventTypes.WAIT_CALLBACK.new(
                    task_id=task.parent,
                    messages=self.messages,
                    from_task_id=task.task_id,
                    from_task_name=task.name,
                )
                session.fire_events(event)
            else:
                session.respond(self.messages)
        return None


class FinishOperator(AbcOperator):

    def run(self, session: Session) -> Union[Operator, None]:
        task = session.task
        session.task.state = TaskState.FINISHED.value
        session.task.status_desc = self.status
        if task.parent:
            event = EventTypes.FINISH_CALLBACK.new(
                task_id=task.parent,
                messages=self.messages,
                from_task_id=task.task_id,
                from_task_name=task.name,
                reason=f"task {task.name} is finished."
            )
            session.fire_events(event)
        elif self.messages:
            session.respond(self.messages)
        return None
