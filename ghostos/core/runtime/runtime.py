from abc import ABC, abstractmethod
from typing import Protocol
from .tasks import GoTasks
from .threads import GoThreads
from .processes import GoProcesses
from ghostos_container import Container
from ghostos.core.messages.transport import Stream


class Runtime(Protocol):
    """
    shell runtime
    """
    shell_id: str
    """basic shell id."""
    process_id: str
    """the process id of this instance of shell."""
    stream: Stream
    """upstream to send messages"""
    container: Container
    """the container of the shell"""
    tasks: GoTasks
    """the tasks of the shell"""
    threads: GoThreads
    """the threads of the shell"""
    processes: GoProcesses
    """"the processes of the shell"""
