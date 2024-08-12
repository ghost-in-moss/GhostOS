from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field
from ghostiss.entity import EntityMeta

__all__ = [
    'Process',
    'Processes',
]


class Process(BaseModel):
    process_id: str = Field(
        description="""
Unique process id for the agent session. Session shall only have one process a time.
Stop the process will stop all the tasks that belongs to it.
""",
    )

    session_id: str = Field(

    )
    ghost_id: str = Field(
        description="""
The id of the ghost in which the process belongs.
""",
    )
    main_task_id: str = Field(
        description="""
The main task is the root task of the process task tree.
""",
    )
    ghost_meta: EntityMeta = Field(
        description="""
The meta data that waken the sleeping ghost in disputed services.
"""
    )


class Processes(ABC):
    """
    管理进程存储的模块. 通常集成到 Session 里.
    """

    @abstractmethod
    def get_process(self, process_id: str) -> Process:
        pass

    @abstractmethod
    def get_ghost_process(self, ghost_id: str) -> Optional[Process]:
        pass

    @abstractmethod
    def save_process(self, process: Process) -> None:
        pass
