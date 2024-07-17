from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from ghostiss.entity import EntityMeta
from ghostiss.helpers import uuid


class Process(BaseModel):
    process_id: str = Field(
        description="""
Unique process id for the agent session. Session shall only have one process a time.
Stop the process will stop all the tasks that belongs to it.
""",
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
    shell_meta: EntityMeta = Field(
        description="""
The meta data that provide the transformative shell interface.
"""
    )


class Processes(ABC):
    pass
