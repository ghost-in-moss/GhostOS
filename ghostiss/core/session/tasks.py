import time
from typing import Optional, List, Set, Iterable, ClassVar
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
from ghostiss.entity import EntityMeta
from ghostiss.abc import Identifier, Identifiable
from ghostiss.core.messages import Payload

__all__ = [
    'Task', 'TaskPayload', 'TaskBrief',
    'TaskState',
    'Tasks',
    'AwaitGroup',
]


class TaskState(str, Enum):
    """ runtime state of the task. """

    NEW = "new"
    """the task is yet created"""

    RUNNING = "running"
    """the task is running"""

    WAITING = "waiting"
    """the task needs more inputs"""

    # QUEUED = "queued"
    # """the task is queued to run"""

    CANCELLED = "cancelled"
    """the task is canceled"""

    FAILED = "failed"
    """the task is failed due to an exception"""

    FINISHED = "finished"
    """the task is finished"""

    @classmethod
    def is_dead(cls, state: str) -> bool:
        return state in {cls.FINISHED, cls.FAILED, cls.CANCELLED}


class AwaitGroup(BaseModel):
    """
    await group of children tasks that will wake up the task.
    """
    description: str = Field(description="why to create the group")
    on_callback: str = Field(description="prompt when waiting tasks are done")
    tasks: List[str] = Field(description="children task ids to wait")


class TaskBrief(BaseModel, Identifiable):
    task_id: str = Field(description="the id of the task")
    name: str = Field(description="the name of the task")
    description: str = Field(description="the description of the task")
    task_state: TaskState = Field(description="the state of the task")
    logs: List[str] = Field(description="the logs of the task")
    created: float = Field(
        default_factory=lambda: round(time.time(), 4),
        description="The time the task was created.",
    )
    updated: float = Field(
        default_factory=lambda: round(time.time(), 4),
        description="The time the task was updated.",
    )
    overdue: float = Field(
        default=0.0,
        description="The time the task was overdue.",
    )
    timeout: float = Field(
        default=0.0,
        description="timeout for each round of the task execution",
    )

    def identifier(self) -> Identifier:
        return Identifier(
            id=self.id,
            name=self.name,
            description=self.description,
        )


class TaskPayload(Payload):
    key: ClassVar[str] = "task_info"
    task_id: str = Field(description="the id of the task")
    task_name: str = Field(description="the name of the task")
    process_id: str = Field(description="the id of the process")
    thread_id: str = Field(description="the id of the thread")


class Task(TaskBrief):
    # -- scope --- #
    session_id: str = Field(
        description="session id that task belongs.",
    )
    process_id: str = Field(
        description="""
the id of the process that the task belongs to.
""",
    )
    task_id: str = Field(
        description="""
    the id of the task. 
    """,
    )
    thread_id: str = Field(
        description="""
the id of the thread that contains the context of the task.
""",
    )

    parent: Optional[str] = Field(
        default=None,
        description="""
Parent task id of the task.
""",
    )

    # --- brief --- #
    name: str = Field(
        description="The name of the task. "
    )
    description: str = Field(
        description="The description of the task"
    )
    priority: float = Field(
        default=0.0,
        description="The priority of the task",
    )

    # --- relations --- #

    children: List[str] = Field(
        default_factory=list,
        description="""
children task ids to wait
"""
    )

    awaiting: List[AwaitGroup] = Field(
        default_factory=list,
    )

    # --- thought --- #
    meta: EntityMeta = Field(
        description="""
The meta data to restore the handler of this task. 
"""
    )

    # --- state --- #
    state: TaskState = Field(
        default=TaskState.NEW,
        description="""
the state of the current task.
"""
    )
    # --- state ---#
    logs: List[str] = Field(
        default_factory=list,
        description="log of the status change of the task",
    )
    # --- time related --- #
    created: float = Field(
        default_factory=lambda: round(time.time(), 4),
        description="The time the task was created.",
    )
    updated: float = Field(
        default=0.0,
        description="The time the task was updated.",
    )
    overdue: float = Field(
        default=0.0,
        description="The time the task was overdue.",
    )
    timeout: float = Field(
        default=0.0,
        description="timeout for each round of the task execution",
    )

    # --- system --- #
    lock: Optional[str] = Field(
        default=None,
    )
    think_turns: int = Field(
        default=0,
        description="记录 task 已经自动运行过多少次. 如果是 -1 的话, 则意味着它刚刚被创建出来. ",
    )
    max_think_turns: int = Field(
        default=20,
        description="任务最大自动运行轮数, 为 0 的话表示无限. "
    )
    pending: bool = Field(
        default=False,
        description="if the task is pending. use Tasks lib to restore it",
    )
    depth: int = Field(
        default=0,
        description="task depth that should be parent task depth +1 if parent exists",
    )

    @classmethod
    def new(
            cls, *,
            task_id: str,
            session_id: str,
            process_id: str,
            name: str, description: str,
            meta: EntityMeta,
            parent_task_id: Optional[str] = None,
    ) -> "Task":
        return Task(
            id=task_id,
            session_id=session_id,
            process_id=process_id,
            thread_id=task_id,
            parent=parent_task_id,
            meta=meta,
            name=name,
            description=description,
        )

    def should_pending(self) -> bool:
        """
        任务是否超过了自动思考的轮次.
        """
        return self.pending or (0 < self.max_think_turns <= self.think_turns)

    def identifier(self) -> Identifier:
        return Identifier(
            id=self.id,
            name=self.name,
            description=self.description,
        )

    def brief(self) -> TaskBrief:
        return TaskBrief(**self.model_dump())

    def awaiting_tasks(self) -> Set[str]:
        result = set()
        for group in self.awaiting:
            for task in group.tasks:
                result.add(task)
        return result

    def update_awaits(self, task_id: str) -> bool:
        awaiting = []
        fulfill = False
        for group in self.awaiting:
            if task_id in group.tasks:
                group.tasks.remove(task_id)
            if len(group.awaiting) > 0:
                awaiting.append(group)
            else:
                fulfill = True
        self.awaiting = awaiting
        return fulfill

    def as_payload(self) -> TaskPayload:
        """
        根据当前 Task 获取添加到消息体里的 payload.
        """
        return TaskPayload(
            task_id=self.task_id,
            process_id=self.process_id,
            thread_id=self.thread_id,
            name=self.name,
        )


class Tasks(ABC):
    """
    管理 task 存储的模块. 通常集成到 Session 里.
    """

    @abstractmethod
    def save_task(self, task: Task) -> None:
        """
        保存一个 task.
        """
        pass

    @abstractmethod
    def get_task(self, task_id: str, lock: bool) -> Optional[Task]:
        """
        使用 task id 来获取一个 task.
        :param task_id:
        :param lock: 是否尝试对 task 上锁, 如果要求上锁但没成功, 返回 None.
        """
        pass

    @abstractmethod
    def get_tasks(self, task_ids: List[str], states: Optional[List[TaskState]] = None) -> Iterable[Task]:
        """
        从数据库里读取出多个 task. 不会获取目标 task 的锁, 所以也无法更新.
        :param task_ids:
        :param states:
        :return:
        """
        pass

    @abstractmethod
    def get_task_briefs(self, task_ids: List[str], states: Optional[List[TaskState]] = None) -> Iterable[TaskBrief]:
        """
        获取多个任务的摘要信息.
        :param task_ids:
        :param states:
        :return:
        """
        pass

    @abstractmethod
    def cancel_tasks(self, task_ids: List[str]) -> None:
        """
        变更一组任务的状态, 强制取消. 目标任务应该周期性检查状态.
        :param task_ids:
        :return:
        """
        pass

    @abstractmethod
    def unlock_task(self, task_id: str, lock: str) -> None:
        pass

    @abstractmethod
    def update_task(self, task: Task) -> Task:
        pass
