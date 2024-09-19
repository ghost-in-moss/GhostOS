from typing import Optional, List, NamedTuple
from ghostos.core.ghosts.ghost import Ghost
from ghostos.core.ghosts.operators import Operator
from ghostos.core.ghosts.thoughts import Thought, ThoughtDriver
from ghostos.core.session import (
    Event, DefaultEventType,
    Task, TaskState, Tasks,
)
from ghostos.core.messages import (
    MessageKind,
    MessageKindParser,
    Role,
)
from dataclasses import dataclass


@dataclass
class NewTask:
    """
    useful to create a child task
    """
    task_name: str
    """task specific name that you can identify this task in future"""

    task_desc: str
    """task description that why you create this task"""

    thought: Thought
    """Thought instance that dispatched to run this task"""

    instruction: str
    """the instruction to the task thought"""


class Utils:
    def __init__(self, ghost: Ghost):
        self.ghost = ghost

    def get_thought_driver(self, thought: Thought) -> ThoughtDriver:
        return self.ghost.mindset().get_thought_driver(thought)

    def initialize(self) -> None:
        """
        initialize ghost
        """
        session = self.ghost.session()
        process = session.process()
        if process.initialized:
            return None
        task_id = process.main_task_id
        root_thought = self.ghost.root_thought()
        identifier = root_thought.identifier()
        meta = root_thought.to_entity_meta()
        task = Task.new(
            task_id=task_id,
            session_id=session.id(),
            process_id=process.process_id,
            name=identifier.name,
            description=identifier.description,
            meta=meta,
            parent_task_id=None,
        )
        process.initialized = True
        session.update_process(process)
        session.update_task(task, None, False)

    def fetch_thought_from_task(self, task: "Task") -> ThoughtDriver:
        thought = self.ghost.entity_factory().force_new_entity(task.meta, Thought)
        return self.ghost.mindset().get_thought_driver(thought)

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
        thought_driver = self.fetch_thought_from_task(task)
        # handle event
        op = thought_driver.on_event(self.ghost, e)
        # update the task.meta from the thought that may be changed
        task.meta = thought_driver.thought.to_entity_meta()
        session.update_task(task, None, False)
        # return the operator that could be None (use default operator outside)
        return op

    def create_child_tasks(
            self, *,
            depend: bool,
            new_tasks: List[NewTask],
    ) -> None:
        """
        创建子任务.
        :param depend: 是否要等待这些任务.
        :param new_tasks:
        :return:
        """
        if len(new_tasks) == 0:
            raise ValueError("at least one thought must be provided")
        for item in new_tasks:
            if not isinstance(item, NewTask):
                raise TypeError(f'new task {item} is not instance of NewTask')
        events = []
        session = self.ghost.session()
        current_task = session.task()
        thread = session.thread()
        parent_task_id = current_task.task_id
        children = []
        children_names = []
        for new_task in new_tasks:
            thought = new_task.thought
            meta = thought.to_entity_meta()
            driver = self.get_thought_driver(thought)
            task_id = driver.new_task_id(self.ghost)
            child = current_task.add_child(
                task_id=task_id,
                name=new_task.task_name,
                description=new_task.task_desc,
                meta=meta,
                assistant=current_task.assistant,
            )
            children.append(child)
            children_names.append(child.name)
            # 准备任务的创建事件. 这个事件的消息应该是目标 Thought 自己生成的. 所以不需要消息.
            e = DefaultEventType.CREATED.new(
                task_id=task_id,
                messages=[],
                from_task_id=parent_task_id,
                instruction=new_task.instruction,
            )
            events.append(e)
        # 更新 task 状态.
        session.create_tasks(*children)
        # 存储要发送的事件.
        session.fire_events(*events)
        thread.append(Role.new_assistant_system(
            content=f"create {len(children_names)} async tasks",
        ))
        # 更新 awaits 的信息.
        if depend:
            current_task.depend_on_tasks(
                task_ids=[child.task_id for child in children],
            )
        session.update_task(current_task, thread, False)

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
