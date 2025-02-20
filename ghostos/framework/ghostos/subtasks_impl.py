from typing import Optional, Dict, List

from ghostos_container import Container
from ghostos.abcd import Subtasks, Session, Ghost
from ghostos.abcd import get_ghost_driver
from ghostos.core.runtime import GoTaskStruct, GoTasks, EventTypes, TaskBrief, TaskState
from ghostos_common.identifier import get_identifier
from ghostos_common.helpers import yaml_pretty_dump
from ghostos_common.entity import to_entity_meta


class SubtasksImpl(Subtasks):

    def __init__(self, session: Session, max_subtasks: int = 20):
        self.session = session
        self.max_shown_subtasks = max_subtasks

    def get_subtasks(self) -> Dict[str, TaskBrief]:
        children = self.session.task.children
        if len(children) == 0:
            return {}
        tasks = self.session.get_task_briefs(*children)
        return {t.name: t for t in tasks.values()}

    def cancel(self, name: str, reason: str = "") -> None:
        subtasks = self.get_subtasks()
        if name not in subtasks:
            raise NameError(f"Subtask {name} does not exist")
        subtask_brief = subtasks[name]
        task_id = subtask_brief.task_id
        self_task = self.session.task
        event = EventTypes.CANCEL.new(
            task_id=task_id,
            reason=reason,
            messages=[],
            from_task_id=self_task.task_id,
            from_task_name=self_task.name,
        )
        self.session.fire_events(event)

    def send(
            self,
            name: str,
            *messages: Subtasks.MessageKind,
            ctx: Optional[Ghost.ContextType] = None,
    ) -> None:
        subtasks = self.get_subtasks()
        if name not in subtasks:
            raise NameError(f"Subtask {name} does not exist")
        subtask_brief = subtasks[name]
        task_id = subtask_brief.task_id
        event_messages = self.session.to_messages(messages)
        self_task = self.session.task
        event = EventTypes.INPUT.new(
            task_id=task_id,
            messages=event_messages,
            from_task_id=self_task.task_id,
            from_task_name=self_task.name,
        )
        self.session.fire_events(event)

    def create(
            self,
            ghost: Ghost,
            instruction: str = "",
            ctx: Optional[Ghost.ContextType] = None,
            task_name: Optional[str] = None,
            task_description: Optional[str] = None,
    ) -> None:
        driver = get_ghost_driver(ghost)
        task_id = driver.make_task_id(self.session.scope)
        tasks = self.session.container.force_fetch(GoTasks)
        task = tasks.get_task(task_id)
        self_task = self.session.task
        if not task:
            identifier = get_identifier(ghost)
            task_name = task_name or identifier.name
            task_description = task_description or identifier.description
            context_meta = to_entity_meta(ctx) if ctx is not None else None
            task = GoTaskStruct.new(
                task_id=task_id,
                shell_id=self_task.shell_id,
                process_id=self_task.process_id,
                depth=self_task.depth + 1,
                name=task_name,
                description=task_description,
                meta=to_entity_meta(ghost),
                context=context_meta,
                parent_task_id=self_task.task_id,
            )
            self.session.create_tasks(task)
        event = EventTypes.CREATED.new(
            task_id=task_id,
            messages=[],
            reason=f"receive task from parent task {self_task.name}",
            from_task_id=self_task.task_id,
            from_task_name=self_task.name,
            instruction=instruction,
        )
        self.session.fire_events(event)

    def self_prompt(self, container: Container) -> str:
        subtasks = self.get_subtasks()
        total = len(subtasks)
        if total == 0:
            return "There are no subtasks yet. You can create any by Subtasks lib if you need"

        tasks = subtasks.values()
        sorted_tasks = sort_tasks(list(tasks))
        prior_tasks = sorted_tasks[:5]
        tasks = sorted_tasks[5:]
        wait_tasks = []
        dead_tasks = []
        other_tasks = []
        for subtask in tasks:
            if subtask.state == TaskState.WAITING.value:
                wait_tasks.append(subtask)
            elif TaskState.is_dead(subtask.state):
                dead_tasks.append(subtask)
            else:
                other_tasks.append(subtask)
        wait_tasks = sort_tasks(wait_tasks)
        dead_tasks = sort_tasks(dead_tasks)
        other_tasks = sort_tasks(other_tasks)

        blocks = []
        count = 0
        for order_tasks in [prior_tasks, wait_tasks, other_tasks, dead_tasks]:
            for task in order_tasks:
                if count > self.max_shown_subtasks:
                    break
                blocks.append(task.model_dump(exclude={"task_id"}, exclude_defaults=True))
                count += 1

        shown_tasks = len(blocks)
        tasks_content = yaml_pretty_dump(shown_tasks)
        return f"""
There are {total} subtasks, first {shown_tasks} tasks brief are:

```yaml
{tasks_content.strip()}
```
"""

    def get_title(self) -> str:
        return "Subtasks"


def sort_tasks(tasks: List[TaskBrief]) -> List[TaskBrief]:
    return sorted(tasks, key=lambda t: t.updated, reverse=True)
