from __future__ import annotations

from typing import Union, List
from typing_extensions import Self
from abc import ABC

from ghostos_container import Container
from ghostos.abcd import Mindflow, Session, Operator
from ghostos.core.runtime import TaskState, EventTypes, TaskBrief
from ghostos_moss import Injection, MossRuntime
from ghostos.core.messages import MessageKind, MessageKindParser, Message, Role
from pprint import pprint
from contextlib import redirect_stdout
from io import StringIO
from ghostos_common.prompter import PromptObjectModel
from ghostos_common.helpers import yaml_pretty_dump


class MindflowImpl(Mindflow, PromptObjectModel, Injection):

    def __init__(self, session: Session, parser: MessageKindParser):
        self.task = session.task
        self.container = session.container
        self.parser = parser
        self._destroyed = False

    def self_prompt(self, container: Container) -> str:
        brief = TaskBrief.from_task(self.task)
        return f"""
You are handling a task `{brief.name}`:

```yaml
{yaml_pretty_dump(brief.model_dump(include={"name", "description", "status_desc"}))}
```
If your task `description` is empty, means endless task, you shall not operate it;
Otherwise you shall `finish` or `cancel` it while the task is done or canceled by user.  

use Mindflow to operate the task state if you need.
"""

    def get_title(self) -> str:
        return "Mindflow"

    def on_inject(self, runtime: MossRuntime, property_name: str) -> Self:
        self.container = runtime.container()
        return self

    def on_destroy(self) -> None:
        self.destroy()

    def finish(self, status: str = "", *replies: MessageKind) -> Operator:
        messages = self.parser.parse(replies)
        return FinishOperator(status, list(messages))

    def fail(self, reason: str = "", *replies: MessageKind) -> Operator:
        messages = self.parser.parse(replies)
        return FailOperator(reason, list(messages))

    def wait(self, status: str = "", *replies: MessageKind) -> Operator:
        messages = self.parser.parse(replies)
        return WaitOperator(status, list(messages))

    def think(self, *messages: MessageKind, instruction: str = "", sync: bool = False) -> Operator:
        messages = self.parser.parse(messages)
        return RotateOperator(list(messages), instruction, sync)

    def observe(self, **kwargs) -> Operator:
        task = self.task
        observation = f"## observation on turn {task.turns}\n"
        for key, value in kwargs.items():
            observation += f"\n### `{key}`\n"
            if isinstance(value, PromptObjectModel):
                content = value.get_prompt(self.container, depth=3)
            else:
                buffer = StringIO()
                with redirect_stdout(buffer):
                    pprint(value)
                content = str(buffer.getvalue())
            observation += f"\n```\n{content}\n```"
        message = Role.SYSTEM.new(content="", memory=observation)
        return RotateOperator(
            messages=[message],
            instruction="",
            sync=False,
        )

    def error(self, *messages: MessageKind) -> Operator:
        messages = self.parser.parse(messages)
        return ErrorOperator(list(messages))

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        del self.container
        del self.parser
        del self.task


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
        session.fire_events(event)
        return None

    def destroy(self):
        del self.messages


class RotateOperator(Operator):

    def __init__(self, messages: List[Message], instruction: str, sync: bool):
        self.messages = messages
        self.instruction = instruction
        self.sync: bool = sync

    def run(self, session: Session) -> Union[Operator, None]:
        task = session.task
        event = EventTypes.ROTATE.new(
            task_id=task.task_id,
            messages=self.messages,
            from_task_id=task.task_id,
            from_task_name=task.name,
            instruction=self.instruction,
        )
        if self.sync:
            return session.handle_event(event)
        else:
            # msg = Role.SYSTEM.new(content=f"issue observation at turn {task.turns}")
            # session.thread.append(msg)
            event.reason = f"receive observation at turn {task.turns}"
            session.fire_events(event)
            session.task.state = TaskState.WAITING.value
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
        messages = []
        if self.reason:
            messages = [Role.SYSTEM.new(content=self.reason)]
        if self.messages:
            messages.extend(self.messages)
        if messages:
            session.respond_buffer(messages)
        return None

    def destroy(self):
        del self.messages


class WaitOperator(AbcOperator, ABC):

    def run(self, session: Session) -> Union[Operator, None]:
        task = session.task
        task.state = TaskState.WAITING.value
        if len(self.messages) > 0:
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
                session.respond_buffer(self.messages)
        return None


class FinishOperator(AbcOperator):

    def run(self, session: Session) -> Union[Operator, None]:
        task = session.task
        session.task.state = TaskState.FINISHED.value
        session.task.status_desc = self.status
        messages = list(self.messages)
        artifact = session.get_artifact()
        if artifact is not None:
            # send artifact
            artifact_message = session.to_messages([artifact])
            messages.extend(artifact_message)

        if task.parent:
            event = EventTypes.FINISH_CALLBACK.new(
                task_id=task.parent,
                messages=messages,
                from_task_id=task.task_id,
                from_task_name=task.name,
                reason=f"task {task.name} is finished."
            )
            session.fire_events(event)
        elif self.messages:
            session.respond_buffer(self.messages)
        return None
