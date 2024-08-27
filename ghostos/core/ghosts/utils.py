from typing import Optional, List
from ghostos.core.ghosts.ghost import Ghost
from ghostos.core.ghosts.operators import Operator
from ghostos.core.ghosts.thoughts import Thought
from ghostos.core.session import (
    Event, DefaultEventType, WaitGroup,
    Task, TaskState, Tasks,
)

from ghostos.core.messages import (
    MessageKind,
    MessageKindParser,
    Message,
    Role,
)


class Utils:
    def __init__(self, ghost: Ghost):
        self.ghost = ghost

    def initialize(self) -> Optional["Event"]:
        session = self.ghost.session()
        process = session.process()
        if process.initialized:
            return None
        task_id = process.main_task_id
        root_thought = self.ghost.root_thought()
        identifier = root_thought.identifier()
        task = Task.new(
            task_id=task_id,
            session_id=session.id(),
            process_id=process.id,
            name=identifier.name,
            description=identifier.description,
            meta=root_thought.to_entity().to_entity_meta(),
            parent_task_id=None,
        )
        process.initialized = True
        session.update_process(process)
        session.update_task(task, None, False)
        return DefaultEventType.CREATED.new(
            task_id=task_id,
            messages=[],
        )

    def handle_event(self, e: "Event") -> Optional["Operator"]:
        """
        ghost 执行事件的基本逻辑.
        """
        session = self.ghost.session()
        task = session.task()
        if task.task_id != e.task_id:
            # todo: use ghostos error
            raise AttributeError(f"event {e.task_id} does not belong to Task {task.task_id}")

        # regenerate the thought from meta
        thoughts = self.ghost.thoughts()
        thought_entity = thoughts.force_make_thought(task.meta)
        # handle event
        op = thought_entity.on_event(self.ghost, e)
        # update the task.meta from the thought that may be changed
        task.meta = thought_entity.to_entity_meta()
        session.update_task(task, None, False)
        # return the operator that could be None (use default operator outside)
        return op

    def create_child_tasks(
            self, *,
            depend: bool,
            thoughts: List[Thought],
            reason: str = "",
            instruction: str = "",
    ) -> None:
        """
        创建子任务.
        :param depend: 是否要等待这些任务.
        :param thoughts:
        :param reason:
        :param instruction:
        :return:
        """
        if len(thoughts) == 0:
            raise ValueError("at least one thought must be provided")
        events = []
        session = self.ghost.session()
        current_task = session.task()
        parent_task_id = current_task.task_id
        children = []
        for thought in thoughts:
            entity = thought.to_entity()
            meta = entity.to_entity_meta()
            identifier = thought.identifier()
            task_id = entity.new_task_id(self.ghost)
            child = current_task.add_child(
                task_id=task_id,
                name=identifier.name,
                description=identifier.description,
                meta=meta,
            )
            children.append(child)
            # 准备任务的创建事件. 这个事件的消息应该是目标 Thought 自己生成的. 所以不需要消息.
            e = DefaultEventType.CREATED.new(
                task_id=task_id,
                from_task_id=parent_task_id,
                messages=[],
            )
            events.append(e)
        # 更新 task 状态.
        session.create_tasks(*children)
        # 存储要发送的事件.
        session.fire_events(*events)
        # 更新 awaits 的信息.
        if depend:
            current_task.depend_on_tasks(
                task_ids=[child.task_id for child in children],
                reason=reason,
                instruction=instruction,
            )
        session.update_task(current_task, None, False)

    def cancel_children_tasks(
            self, *,
            reason: str = "",
            instruction: str = "",
            includes: Optional[List[str]] = None,
            self_task: Optional[Task] = None,
    ) -> None:
        """
        取消当前任务的子任务.
        includes 为 None 时表示取消所有子任务.
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
        canceling_events = []
        for t in children:
            if not TaskState.is_dead(t.state) and t.task_id in includes_set:
                event = DefaultEventType.CANCELING.new(
                    task_id=t.task_id,
                    from_task_id=self_task.task_id,
                    reason=reason,
                    instruction=instruction,
                    messages=[]
                )
                canceling_events.append(event)

        # 批量取消未结束的子任务.
        if canceling_events:
            # 仍然向这些任务发送事件.
            # 发送事件需要用 session 的抽象, 在 session.finish() 时真正执行.
            session.fire_events(*canceling_events)
        return

    def send(self, *messages: MessageKind) -> None:
        if len(messages) == 0:
            return
        parser = MessageKindParser()
        outputs = parser.parse(messages)
        self.ghost.session().messenger().send(outputs)

    def send_task_event(
            self, *,
            task_id: str,
            event_type: str,
            messages: List[MessageKind],
            reason: str = "",
            instruction: str = "",
            self_task: Optional[Task] = None,
    ) -> None:
        """
        主动向一个目标任务发送通知.
        :param task_id:
        :param event_type:
        :param messages:
        :param reason:
        :param instruction:
        :param self_task:
        :return:
        """
        if messages:
            parser = MessageKindParser(role=Role.ASSISTANT.value)
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
            instruction=instruction,
        )
        session.fire_events(event)
        return
