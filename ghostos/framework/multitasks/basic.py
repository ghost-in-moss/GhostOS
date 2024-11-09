from typing import Tuple
from ghostos.core.ghosts import MultiTask, Operator, Ghost, Thought, NewTask
from ghostos.core.llms import Prompt
from ghostos.core.messages import MessageKind, Role
from ghostos.core.runtime.events import EventTypes
from ghostos.framework.operators import WaitOnTasksOperator
from ghostos.helpers import yaml_pretty_dump


class MultiTaskBasicImpl(MultiTask):

    def __init__(self, ghost: Ghost):
        self._ghost = ghost

    def update_prompt(self, chat: Prompt) -> Prompt:
        children = self._ghost.session().get_task_briefs(children=True)
        if not children:
            return chat
        prompt = """
# MultiTask 

You are equipped with MultiTask library. You have created the async tasks below: 
```yaml
{tasks}
```
"""
        data = []
        for task in children:
            data.append(task.model_dump(exclude_defaults=True, exclude={"task_id"}))
        tasks = yaml_pretty_dump(data)
        content = prompt.format(tasks=tasks)
        chat.system.append(Role.SYSTEM.new(content=content))
        return chat

    def wait_on_tasks(self, *new_tasks: Tuple[str, str, Thought, str]) -> Operator:
        tasks = []
        for task in new_tasks:
            task_name, task_desc, thought, instruction = task
            tasks.append(NewTask(
                task_name=task_name,
                task_desc=task_desc,
                thought=thought,
                instruction=instruction,
            ))
        return WaitOnTasksOperator(
            new_tasks=tasks,
        )

    def run_tasks(self, *new_tasks: Tuple[str, str, Thought, str]) -> None:
        tasks = []
        for task in new_tasks:
            task_name, task_desc, thought, instruction = task
            tasks.append(NewTask(
                task_name=task_name,
                task_desc=task_desc,
                thought=thought,
                instruction=instruction,
            ))
        self._ghost.utils().create_child_tasks(depend=False, new_tasks=tasks)

    def send_task(self, task_name: str, *messages: MessageKind) -> None:
        messages = list(messages)
        if not messages:
            return
        session = self._ghost.session()
        from_task_id = session.task().task_id
        tasks = session.get_task_briefs(children=True)
        for task in tasks:
            if task.name == task_name:
                event = EventTypes.REQUEST.new(
                    task_id=task.id,
                    from_task_id=from_task_id,
                    messages=messages,
                )
                session.fire_events(event)

    def cancel_task(self, task_name: str, reason: str) -> None:
        session = self._ghost.session()
        from_task_id = session.task().task_id
        tasks = session.get_task_briefs(children=True)
        for task in tasks:
            if task.name == task_name:
                event = EventTypes.CANCEL.new(
                    task_id=task.id,
                    from_task_id=from_task_id,
                    messages=[],
                    reason=reason,
                )
                session.fire_events(event)
