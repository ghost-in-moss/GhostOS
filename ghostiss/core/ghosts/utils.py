from typing import Optional, List
from ghostiss.core.ghosts.ghost import Ghost
from ghostiss.core.ghosts.operators import Operator
from ghostiss.core.ghosts.thoughts import Thought
from ghostiss.core.session import (
    Event, DefaultEventType, AwaitGroup,
    Task, TaskState, Tasks,
)

from ghostiss.core.messages import (
    MessageType,
    MessageTypeParser,
    Message,
    Role,
)


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
            session.fire_events(e)
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

    def create_child_tasks(self, awaits: bool, thoughts: List[Thought]) -> None:
        """
        创建子任务.
        :param awaits: 是否要等待这些任务.
        :param thoughts:
        :return:
        """
        if len(thoughts) == 0:
            raise ValueError("at least one thought must be provided")
        events = []
        session = self.ghost.session()
        process = session.process()
        current_task = session.task()
        parent = current_task.task_id
        tasks = []
        children_task_ids = set(current_task.children)
        for thought in thoughts:
            thought_driver = self.ghost.thoughts().instance_thought(thought)
            meta = thought_driver.to_entity_meta()
            session_id = process.session_id
            process_id = process.process_id
            identifier = thought.identifier()
            task_id = thought_driver.new_task_id(self.ghost)
            children_task_ids.add(task_id)
            # 创建任务.
            task = Task.new(
                task_id=task_id,
                session_id=session_id,
                process_id=process_id,
                name=identifier.name,
                description=identifier.description,
                meta=meta,
                parent_task_id=parent,
            )
            tasks.append(task)
            # 准备任务的创建事件. 这个事件的消息应该是目标 Thought 自己生成的. 所以不需要消息.
            e = DefaultEventType.CREATED.new(
                task_id=task_id,
                from_task_id=parent,
                messages=[],
            )
            events.append(e)
        # 更新 task 状态.
        session.update_task(*tasks)
        # 存储要发送的事件.
        session.fire_events(*events)
        children = list(children_task_ids)
        current_task.children = children
        # 更新 awaits 的信息.
        if awaits:
            group = AwaitGroup(
                tasks=children,
                description="",
                on_callaback=""
            )
            current_task.awaiting.append(group)
        session.update_task(current_task)

    def cancel_children_tasks(
            self,
            reason: str,
            includes: Optional[List[str]] = None,
            self_task: Optional[Task] = None,
    ) -> None:
        """
        取消当前任务的子任务.
        """
        session = self.ghost.session()
        self_task = session.task() if self_task is None else self_task
        # 没有正确传参.
        if includes is not None and not includes:
            return

        children_ids = self_task.children
        if not children_ids:
            return

        tasks = self.ghost.container().force_fetch(Tasks)
        children = list(tasks.get_task_briefs(children_ids))
        if not children:
            # 没有 children.
            return

        includes_set = set(includes) if includes else set([t.task_id for t in children])
        canceling = []
        canceling_events = []
        for t in children:
            if not TaskState.is_dead(t.state) and t.task_id in includes_set:
                canceling.append(t.task_id)
                event = DefaultEventType.CANCELED.new(
                    task_id=t.task_id,
                    from_task_id=self_task.task_id,
                    reason=reason,
                    messages=[]
                )
                canceling_events.append(event)

        # 批量取消未结束的子任务.
        if canceling_events:
            # 强制取消多个任务.
            session.cancel_tasks(*canceling)
            # 仍然向这些任务发送事件.
            # 发送事件需要用 session 的抽象, 在 session.finish() 时真正执行.
            session.fire_events(*canceling_events)
        return

    def send(self, *messages: MessageType) -> None:
        if len(messages) == 0:
            return
        parser = MessageTypeParser()
        outputs = parser.parse(messages)
        self.ghost.session().messenger().send(outputs)

    def send_task_event(
            self, *,
            task_id: str,
            event_type: str,
            messages: List[MessageType],
            reason: str = "",
            self_task: Optional[Task] = None,
    ) -> None:
        """
        主动向一个目标任务发送通知.
        :param task_id:
        :param event_type:
        :param messages:
        :param reason:
        :param self_task:
        :return:
        """
        if messages:
            parser = MessageTypeParser(role=Role.ASSISTANT.value)
            outputs = parser.parse(messages)
        else:
            outputs = []
        session = self.ghost.session()
        self_task = self_task if self_task is not None else session.task()

        event = DefaultEventType(event_type).new(
            task_id=task_id,
            messages=outputs,
            from_task_id=self_task.task_id,
            reason=reason,
        )
        session.fire_events(event)
        return
