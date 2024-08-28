from ghostos.core.ghosts import MultiTask, Operator, Thought, Ghost
from ghostos.core.messages import MessageKind
from ghostos.core.session.events import DefaultEventType
from ghostos.framework.operators import WaitOnTasksOperator


class MultiTaskBasicImpl(MultiTask):

    def __init__(self, ghost: Ghost):
        self._ghost = ghost

    def wait_on_tasks(self, *thoughts: Thought, reason: str = "", instruction: str = "") -> Operator:
        return WaitOnTasksOperator(
            thoughts=list(thoughts),
            reason=reason,
            instruction=instruction,
        )

    def run_tasks(self, *thoughts: Thought) -> None:
        self._ghost.utils().create_child_tasks(depend=False, thoughts=list(thoughts))

    def send_task(self, task_name: str, *messages: MessageKind) -> None:
        messages = list(messages)
        if not messages:
            return
        session = self._ghost.session()
        from_task_id = session.task().task_id
        tasks = session.get_task_briefs(children=True)
        for task in tasks:
            if task.name == task_name:
                event = DefaultEventType.INPUT.new(
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
                event = DefaultEventType.CANCELING.new(
                    task_id=task.id,
                    from_task_id=from_task_id,
                    messages=[],
                    reason=reason,
                )
                session.fire_events(event)
