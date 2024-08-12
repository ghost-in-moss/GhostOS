import time
from typing import Optional, List, Set
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
from ghostiss.entity import EntityMeta
from ghostiss.abc import Identifier, Identifiable

__all__ = [
    'Task', 'TaskState', 'Tasks',
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

    QUEUED = "queued"
    """the task is queued to run"""

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


class Task(BaseModel, Identifiable):
    locker: Optional[str] = Field(
        description="task locker ",
    )
    round: int = Field(
        default=0,
        description="记录 Process 已经运行过多少次. 如果是第一次的话, 则意味着它刚刚被创建出来. ",
    )

    # -- scope --- #
    process_id: str = Field(
        description="""
the id of the process that the task belongs to.
""",
    )

    thread_id: str = Field(
        description="""
the id of the thread that contains the context of the task.
""",
    )
    task_id: str = Field(
        description="""
the id of the task. 
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
    # --- time related --- #
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


class Tasks(ABC):
    """
    管理 task 存储的模块. 通常集成到 Session 里.
    """

    @abstractmethod
    def create_task(self, task: Task) -> Task:
        pass

    @abstractmethod
    def get_task(self, task_id: str, lock: bool) -> Optional[Task]:
        pass

    @abstractmethod
    def has_task(self, task_id: str) -> bool:
        pass

    @abstractmethod
    def lock_task(self, task_id: str) -> Task:
        pass

    @abstractmethod
    def update_task(self, task: Task) -> Task:
        pass
