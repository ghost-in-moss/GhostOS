# Tasks

One of the core features of `GhostOS` is its fully asynchronous Multi-Agent architecture.

Each running Agent (Ghost) is considered a `minimal stateful unit`, capable of scheduling the execution status of a
task:

```python

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
```

Agent 可以直接使用 [MOSS](/en/concepts/moss_protocol.md) 提供的类库来操作自身的状态:

```python

class Taskflow(Prompter, ABC):
    """
    default operations
    """
    MessageKind = Union[str, Message, Any]
    """message kind shall be string or serializable object"""

    # --- 基本操作 --- #
    @abstractmethod
    def finish(self, status: str = "", *replies: MessageKind) -> Operator:
        """
        finish self task
        :param status: describe status of the task
        :param replies: replies to parent task or user
        """
        pass

    @abstractmethod
    def fail(self, reason: str = "", *replies: MessageKind) -> Operator:
        """
        self task failed.
        :param reason: describe status of the task
        :param replies: replies to parent task or user
        """
        pass

    @abstractmethod
    def wait(self, status: str = "", *replies: MessageKind) -> Operator:
        """
        wait for the parent task or user to provide more information or further instruction.
        :param status: describe current status
        :param replies: question, inform or
        """
        pass

    @abstractmethod
    def think(self, *messages: MessageKind, instruction: str = "", sync: bool = False) -> Operator:
        """
        start next round thinking on messages
        :param messages: observe target
        :param instruction: instruction when receive the observation.
        :param sync: if True, observe immediately, otherwise check other event first
        :return:
        """
        pass

    @abstractmethod
    def observe(self, **kwargs) -> Operator:
        """
        observe values
        :param kwargs:
        :return:
        """

    @abstractmethod
    def error(self, *messages: MessageKind) -> Operator:
        pass


class Subtasks(Prompter, ABC):
    """
    library that can handle async subtasks by other ghost instance.
    """
    MessageKind = Union[str, Message, Any]
    """message kind shall be string or serializable object"""

    @abstractmethod
    def cancel(self, name: str, reason: str = "") -> None:
        """
        cancel an exists subtask
        :param name: name of the task
        :param reason: the reason to cancel it
        :return:
        """
        pass

    @abstractmethod
    def send(
            self,
            name: str,
            *messages: MessageKind,
            ctx: Optional[Ghost.ContextType] = None,
    ) -> None:
        """
        send message to an existing subtask
        :param name: name of the subtask
        :param messages: the messages to the subtask
        :param ctx: if given, update the ghost context of the task
        :return:
        """
        pass

    @abstractmethod
    def create(
            self,
            ghost: Ghost,
            instruction: str = "",
            ctx: Optional[Ghost.ContextType] = None,
            task_name: Optional[str] = None,
            task_description: Optional[str] = None,
    ) -> None:
        """
        create subtask from a ghost instance
        :param ghost: the ghost instance that handle the task
        :param instruction: instruction to the ghost
        :param ctx: the context that the ghost instance needed
        :param task_name: if not given, use the ghost's name as the task name
        :param task_description: if not given, use the ghost's description as the task description
        """
        pass
```

This allows multiple Agents to communicate and interact with each other on a `Task` basis.

For more details on the implementation,
see [ghostos.core.runtime.tasks](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/core/runtime/tasks.py).