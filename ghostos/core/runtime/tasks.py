import time
from typing import Optional, List, Set, Iterable, ClassVar, Dict, Self
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
from ghostos.common import Identifier, Identical, EntityMeta
from ghostos.core.messages import Payload
from contextlib import contextmanager

__all__ = [
    'GoTaskStruct', 'TaskPayload', 'TaskBrief',
    'TaskState',
    'GoTasks',
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
        return state in {cls.FINISHED, cls.FAILED, cls.CANCELLED, cls.KILLED}


#
# class WaitGroup(BaseModel):
#     """
#     await group of children tasks that will wake up the task.
#     """
#     tasks: Dict[str, bool] = Field(description="children task ids to wait")
#
#     def is_done(self) -> bool:
#         for _, ok in self.tasks.items():
#             if not ok:
#                 return False
#         return True


class AssistantInfo(Identifier, BaseModel):
    id: str = Field(description="id of the assistant")
    name: str = Field(description="name of the assistant")
    description: str = Field(description="description of the assistant")
    meta_prompt: str = Field(description="meta prompt of the assistant")


class GoTaskStruct(BaseModel):
    # -- scope --- #
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
    depth: int = Field(
        default=0,
        description="the depth of the task",
    )

    # --- state values --- #

    meta: EntityMeta = Field(
        description="the entity meta of the task handler",
    )

    state: str = Field(
        default=TaskState.NEW.value,
        description="""
    the state of the current task.
    """
    )

    status_desc: str = Field(
        default="",
        description="The description of the current task status.",
    )

    globals: Dict = Field(
        default_factory=dict,
        description="the global values that inherit from the parent task or shell",
    )

    properties: Dict[str, Dict] = Field(
        default_factory=dict,
        description="the state data of the task handler"
    )

    # --- brief --- #
    name: str = Field(
        description="The name of the task. not very important"
    )
    purpose: str = Field(
        description="The description of the task purpose"
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

    # --- time related --- #
    created: float = Field(
        default_factory=lambda: round(time.time(), 4),
        description="The time the task was created.",
    )
    updated: float = Field(
        default=0.0,
        description="The time the task was updated.",
    )

    # --- system --- #
    lock: Optional[str] = Field(
        default=None,
    )

    turns: int = Field(
        default=0,
        description="the turn number of the task runs",
    )

    @classmethod
    def new(
            cls, *,
            task_id: str,
            shell_id: str,
            process_id: str,
            name: str,
            description: str,
            meta: EntityMeta,
            parent_task_id: Optional[str] = None,
    ) -> "GoTaskStruct":
        return GoTaskStruct(
            task_id=task_id,
            shell_id=shell_id,
            process_id=process_id,
            thread_id=task_id,
            parent=parent_task_id,
            meta=meta,
            name=name,
            description=description,
        )

    def add_child(
            self, *,
            task_id: str,
            name: str,
            description: str,
            meta: EntityMeta,
    ) -> "GoTaskStruct":
        self.children.append(task_id)
        child = self.new(
            task_id=task_id,
            shell_id=self.shell_id,
            process_id=self.process_id,
            name=name,
            description=description,
            meta=meta,
            parent_task_id=self.task_id,
        )
        child.depth = self.depth + 1
        return child

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
            description=self.purpose,
        )

    def is_dead(self) -> bool:
        return TaskState.is_dead(self.state)

    def is_new(self) -> bool:
        return TaskState.NEW.value == self.state

    def new_turn(self) -> Self:
        """
        保存一轮变更之前运行的方法.
        todo
        """
        return self.model_copy(
            update={
                "updated": round(time.time(), 4),
                "turns": self.turns + 1,

            },
            deep=True,
        )


class TaskBrief(BaseModel, Identical):
    task_id: str = Field(description="the id of the task")
    name: str = Field(description="the name of the task")
    purpose: str = Field(description="the purpose of the task")
    state: str = Field(description="the state of the task")
    status_desc: str = Field(description="the description of the task status")

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
    def from_task(cls, task: GoTaskStruct) -> "TaskBrief":
        return TaskBrief(**task.model_dump())


class TaskPayload(Payload):
    key: ClassVar[str] = "task_info"

    task_id: str = Field(description="the id of the task")
    task_name: str = Field(description="the name of the task")
    process_id: str = Field(description="the id of the process")
    session_id: str = Field(description="the session id of the task")
    thread_id: str = Field(description="the id of the thread")

    @classmethod
    def from_task(cls, task: GoTaskStruct) -> "TaskPayload":
        return cls(
            task_id=task.task_id,
            task_name=task.name,
            session_id=task.shell_id,
            process_id=task.process_id,
            thread_id=task.thread_id,
        )


class TaskLocker(ABC):

    @abstractmethod
    def acquire(self) -> bool:
        pass

    @abstractmethod
    def refresh(self) -> bool:
        pass

    @abstractmethod
    def release(self) -> bool:
        pass


class GoTasks(ABC):
    """
    管理 task 存储的模块. 通常集成到 Session 里.
    """

    @abstractmethod
    def save_task(self, *tasks: GoTaskStruct) -> None:
        """
        保存一个或者多个 task.
        """
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[GoTaskStruct]:
        """
        使用 task id 来获取一个 task.
        :param task_id:
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
    def get_tasks(self, task_ids: List[str]) -> Dict[str, GoTaskStruct]:
        """
        从数据库里读取出多个 task. 不会获取目标 task 的锁, 所以也无法更新.
        :param task_ids:
        :return:
        """
        pass

    @abstractmethod
    def get_task_briefs(self, task_ids: List[str]) -> Dict[str, TaskBrief]:
        """
        获取多个任务的摘要信息.
        :param task_ids:
        :param states:
        :return:
        """
        pass

    @abstractmethod
    def lock_task(self, task_id: str) -> TaskLocker:
        """
        :param task_id:
        :return: None if not locked
        """
        pass

    @contextmanager
    def transaction(self):
        yield
