import time
from typing import Optional, List, Set, Iterable, ClassVar, Dict
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
from ghostos.entity import EntityMeta
from ghostos.abc import Identifier, Identifiable
from ghostos.core.messages import Payload
from contextlib import contextmanager

__all__ = [
    'Task', 'TaskPayload', 'TaskBrief',
    'TaskState',
    'Tasks',
    'WaitGroup',
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

    KILLED = "killed"

    FINISHED = "finished"
    """the task is finished"""

    @classmethod
    def is_dead(cls, state: str) -> bool:
        return state in {cls.FINISHED, cls.FAILED, cls.CANCELLED, cls.KILLED}


class WaitGroup(BaseModel):
    """
    await group of children tasks that will wake up the task.
    """
    tasks: Dict[str, bool] = Field(description="children task ids to wait")

    def is_done(self) -> bool:
        for _, ok in self.tasks.items():
            if not ok:
                return False
        return True


class AssistantInfo(Identifier, BaseModel):
    id: str = Field(description="id of the assistant")
    name: str = Field(description="name of the assistant")
    description: str = Field(description="description of the assistant")
    meta_prompt: str = Field(description="meta prompt of the assistant")


class Task(BaseModel):
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

    # --- assistant info --- #

    assistant: Optional[AssistantInfo] = Field(
        default=None,
        description="the assistant information, if given, took it as the message sender",
    )

    # --- relations --- #

    children: List[str] = Field(
        default_factory=list,
        description="""
children task ids to wait
"""
    )

    depending: List[WaitGroup] = Field(
        default_factory=list,
        description="the children task ids that wait them callback",
    )

    # --- thought --- #
    meta: EntityMeta = Field(
        description="""
The meta data to restore the handler of this task. 
"""
    )

    # --- state --- #
    state: str = Field(
        default=TaskState.NEW.value,
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
    turns: int = Field(
        default=0,
        description="the turn number of the task runs",
    )
    think_turns: int = Field(
        default=0,
        description="记录 task 已经自动运行过多少次. 如果是 0 的话, 则意味着它刚刚被创建出来. ",
    )
    depth: int = Field(
        default=0,
        description="task depth that should be parent task depth +1 if parent exists",
    )
    max_think_turns: int = Field(
        default=20,
        description="任务最大自动运行轮数, 为 0 的话表示无限. "
    )
    max_children: int = Field(
        default=20,
        description="当前任务最大的子任务数, 超过这范围的子任务开始垃圾回收. "
    )

    @classmethod
    def new(
            cls, *,
            task_id: str,
            session_id: str,
            process_id: str,
            name: str,
            description: str,
            meta: EntityMeta,
            parent_task_id: Optional[str] = None,
            assistant: Optional[Identifier] = None,
    ) -> "Task":
        return Task(
            task_id=task_id,
            session_id=session_id,
            process_id=process_id,
            thread_id=task_id,
            parent=parent_task_id,
            meta=meta,
            name=name,
            description=description,
            assistant=assistant,
        )

    def add_child(
            self, *,
            task_id: str,
            name: str,
            description: str,
            meta: EntityMeta,
            assistant: Optional[Identifier] = None,
    ) -> "Task":
        self.children.append(task_id)
        return self.new(
            task_id=task_id,
            session_id=self.session_id,
            process_id=self.process_id,
            name=name,
            description=description,
            meta=meta,
            parent_task_id=self.task_id,
            assistant=assistant,
        )

    def think_too_much(self) -> bool:
        """
        任务是否超过了自动思考的轮次.
        """
        return 0 < self.max_think_turns <= self.think_turns

    def too_much_children(self) -> bool:
        return 0 < self.max_children <= len(self.children)

    def remove_child(self, child_task_id: str) -> bool:
        results = []
        removed = False
        for exists_child_id in self.children:
            if child_task_id == exists_child_id:
                removed = True
                continue
            results.append(exists_child_id)
        self.children = results
        return removed

    def identifier(self) -> Identifier:
        return Identifier(
            id=self.id,
            name=self.name,
            description=self.description,
        )

    def is_dead(self) -> bool:
        return TaskState.is_dead(self.state)

    def is_new(self) -> bool:
        return TaskState.NEW.value == self.state

    def depending_tasks(self) -> Set[str]:
        result = set()
        for group in self.depending:
            for task in group.tasks:
                result.add(task)
        return result

    def depend_on_tasks(self, task_ids: List[str]) -> None:
        group = WaitGroup(
            tasks={task_id: False for task_id in task_ids},
        )
        self.depending.append(group)

    def on_callback_task(self, task_id: str) -> Optional[WaitGroup]:
        """
        得到一个 task id 的回调. 判断是否一组 wait group 被激活了.
        :param task_id:
        :return: 是否有 wait group 激活了.
        """
        for group in self.depending:
            if task_id in group.tasks:
                group.tasks[task_id] = True
                if group.is_done():
                    return group
        return None

    def update_turn(self) -> None:
        """
        保存一轮变更之前运行的方法.
        """
        self.updated = round(time.time(), 4)
        self.turns += 1


class TaskBrief(BaseModel, Identifiable):
    task_id: str = Field(description="the id of the task")
    name: str = Field(description="the name of the task")
    description: str = Field(description="the description of the task")
    state: str = Field(description="the state of the task")
    logs: List[str] = Field(description="the logs of the task")

    def is_overdue(self) -> bool:
        now = time.time()
        return now - self.updated > self.overdue

    def identifier(self) -> Identifier:
        return Identifier(
            id=self.id,
            name=self.name,
            description=self.description,
        )

    @classmethod
    def from_task(cls, task: Task) -> "TaskBrief":
        return TaskBrief(**task.model_dump())


class TaskPayload(Payload):
    key: ClassVar[str] = "task_info"

    task_id: str = Field(description="the id of the task")
    task_name: str = Field(description="the name of the task")
    process_id: str = Field(description="the id of the process")
    thread_id: str = Field(description="the id of the thread")

    @classmethod
    def from_task(cls, task: Task) -> "TaskPayload":
        return cls(
            task_id=task.task_id,
            task_name=task.name,
            process_id=task.process_id,
            thread_id=task.thread_id,
        )


class Tasks(ABC):
    """
    管理 task 存储的模块. 通常集成到 Session 里.
    """

    @abstractmethod
    def save_task(self, *tasks: Task) -> None:
        """
        保存一个或者多个 task.
        """
        pass

    @abstractmethod
    def get_task(self, task_id: str, lock: bool) -> Optional[Task]:
        """
        使用 task id 来获取一个 task.
        :param task_id:
        :param lock: 是否尝试对 task 上锁, 如果要求上锁但没成功, 返回 None.
        :return: if task is not Exists or locked failed
        """
        pass

    @abstractmethod
    def exists(self, task_id: str) -> bool:
        """
        if task exists
        :param task_id:
        :return:
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
    def unlock_task(self, task_id: str, lock: str) -> None:
        """
        对一个任务解锁.
        :param task_id:
        :param lock:
        :return:
        """
        pass

    @abstractmethod
    def refresh_task_lock(self, task_id: str, lock: str) -> Optional[str]:
        """
        更新一个任务的锁, 也会给它续期.
        :param task_id:
        :param lock:
        :return:
        """
        pass

    @contextmanager
    def transaction(self):
        yield
