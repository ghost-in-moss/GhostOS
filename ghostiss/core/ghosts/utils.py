from typing import Optional
from ghostiss.core.ghosts.ghost import Ghost
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.session import Event


class Utils:
    def __init__(self, ghost: Ghost):
        self.ghost = ghost

    def handle_event(self, e: "Event") -> Optional["Operator"]:
        """
        ghost 执行事件的基本逻辑.
        """
        session = self.ghost.session()
        task = session.task()
        if task.task_id != e.task_id:
            # todo: use ghostiss error
            raise AttributeError(f"event {e.task_id} does not belong to Task {task.task_id}")
        if e.block and not (session.alive() and session.refresh_lock()):
            # e 要求锁定 session, 但是获取锁失败.
            session.fire_event(event=e)
            return None

        # regenerate the thought from meta
        mindset = self.ghost.thoughts()
        thought_driver = mindset.force_make_thought(task.meta)
        # handle event
        op = thought_driver.on_event(self.ghost, e)
        # update the task.meta from the thought that may be changed
        task.meta = thought_driver.to_entity_meta()
        session.update_task(task)
        # return the operator that could be None (use default operator outside)
        return op
