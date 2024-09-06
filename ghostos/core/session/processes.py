from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field
from ghostos.entity import EntityMeta
from contextlib import contextmanager
from ghostos.helpers import uuid

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
        description="session id in which the process belongs",
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
    initialized: bool = Field(
        default=False,
        description="if the process is initialized or not.",
    )
    quited: bool = Field(
        default=False,
        description="if the process is quited or not.",
    )

    @classmethod
    def new(
            cls, *,
            session_id: str,
            is_async: bool,
            ghost_meta: EntityMeta,
            process_id: Optional[str] = None,
    ) -> "Process":
        process_id = process_id if process_id else uuid()
        main_task_id = process_id
        return Process(
            session_id=session_id,
            process_id=process_id,
            main_task_id=main_task_id,
            ghost_meta=ghost_meta,
            asynchronous=is_async,
        )


class Processes(ABC):
    """
    管理进程存储的模块. 通常集成到 Session 里.
    """

    @abstractmethod
    def get_process(self, process_id: str) -> Optional[Process]:
        """
        get process by id
        :param process_id: process id
        """
        pass

    @abstractmethod
    def get_session_process(self, session_id: str) -> Optional[Process]:
        """
        get session process by session id
        """
        pass

    @abstractmethod
    def save_process(self, process: Process) -> None:
        """
        save process
        :param process:
        :return:
        """
        pass

    @contextmanager
    def transaction(self):
        yield
