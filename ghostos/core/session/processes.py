from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field
from ghostos.entity import EntityMeta
from contextlib import contextmanager
from ghostos.helpers import uuid

__all__ = [
    'GoProcess',
    'GoProcesses',
]


class GoProcess(BaseModel):
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
            ghost_meta: EntityMeta,
            process_id: Optional[str] = None,
            main_task_id: Optional[str] = None,
    ) -> "GoProcess":
        process_id = process_id if process_id else uuid()
        main_task_id = process_id if main_task_id is None else main_task_id
        return GoProcess(
            session_id=session_id,
            process_id=process_id,
            main_task_id=main_task_id,
            ghost_meta=ghost_meta,
        )


class GoProcesses(ABC):
    """
    repository to save or load process
    """

    @abstractmethod
    def get_process(self, process_id: str) -> Optional[GoProcess]:
        """
        get process by id
        :param process_id: process id
        """
        pass

    @abstractmethod
    def get_session_process(self, session_id: str) -> Optional[GoProcess]:
        """
        get session process by session id
        """
        pass

    @abstractmethod
    def save_process(self, process: GoProcess) -> None:
        """
        save process
        :param process:
        :return:
        """
        pass

    @contextmanager
    def transaction(self):
        """
        transaction to process io
        do nothing as default.
        """
        yield
