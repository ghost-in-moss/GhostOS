from abc import ABC, abstractmethod
from typing import (
    Protocol, TypeVar, Optional, Union, Literal, List, Type, Dict, TypedDict, Required, Any
)
from ghostos.core.moss import Moss
from pydantic import BaseModel


class Func(Protocol):
    """
    AI Function definition in data-driven pattern.
    """

    Args: Type[BaseModel]
    Returns: Optional[Type[BaseModel]]


F = TypeVar('F', bound=Func)


class Task(Protocol[F]):
    """
    is the state instance of a Func execution
    """
    args: F.Args
    """ the calling arguments, which is changeable during execution"""

    returns: Union[F.Returns, None]
    """ the return values, which is altering during execution"""

    status: Literal["new", "waiting", "running", "done", "pending", "cancelled", "aborted"]
    """ the status of the execution """

    description: str
    """ describe the execution status"""


class State(BaseModel, ABC):
    """
    the runtime private state properties model of the Func
    """
    pass


S = TypeVar("S", bound=State)


class VarPtr(TypedDict):
    """
    refer a global accessible variable to the pointer.
    compatible to many type like int, str, boolean, float, or other identifiable types.
    """

    vid: Required[str]
    """ unique id of the variable"""

    type: Required[str]
    """ origin type of the variable, like int, str, or import path in `[module]:[attr]` pattern"""

    desc: Optional[str]
    """ description of the variable"""


M = TypeVar("M", bound=Moss)


class OP(ABC):
    """
    runtime operator of a Func.
    can only be pre-defined by outer Operating System.
    """

    @abstractmethod
    def run(self):
        pass


class Context(Protocol[F, S, M]):
    """
    the runtime context for an AI Entity-driven Func.
    """

    state: S
    """ mutate self state properties """

    task: Task[F]
    """ self task instance """

    moss: M
    """
    the operating system for the AI Entity who driven this Func.
    provide instance of libraries and tools.
    """

    subtasks: Dict[str, Task]
    """
    the other Func state instances, that have been created by this Context.
    """

    @abstractmethod
    def send(self, *messages: Union[str, VarPtr, Any]) -> None:
        """
        send messages to the caller.
        :param messages: str, var pointer or any value that can be converted to VarPtr.
        :exception TypeError: if message can not convert to VarPtr
        """
        pass

    @abstractmethod
    def set_var(self, value: Any, vid: Optional[str] = None) -> VarPtr:
        """

        :param value:
        :param vid:
        :return:
        """
        pass

    @abstractmethod
    def get_var(self, vid: str, type_: Optional[Type[Any]] = None) -> Union[Any, None]:
        """
        get a global variable by vid.
        :param vid: id from VarPtr
        :param type_: the expected type of the variable.
        :return: None if the variable is not found, otherwise unpack the variable to it origin type
        """
        pass

    # the functions below are the primitive operators of this functions.

    @abstractmethod
    def done(self, returns: Union[F.Returns, None] = None, *messages: str) -> OP:
        """
        end the task with confirmed return values.
        :param returns: if not None, update the return value of self task
        :param messages: if given, inform the caller with the messages.
        """
        pass

    @abstractmethod
    def abort(self, reason: str) -> OP:
        """
        abort the task with given reason.
        """
        pass

    @abstractmethod
    def await_answer(self, question: str, suggestions: Optional[List[str]] = None) -> OP:
        """
        ask a question to the caller, and wait for the answer.
        :param question: ask for confirmation, choice, selection, clarification, etc.
        :param suggestions: if you have any
        """
        pass

    @abstractmethod
    def ack(self) -> OP:
        """
        acknowledge the messages and do nothing.
        """
        pass

    @abstractmethod
    def observe(self, **kwargs) -> OP:
        """
        start an observation on the outputs before it is called.
        :param kwargs: if given, repr each arg for observation.
        """
        pass

    # the methods below can interact with other funcs.

    @abstractmethod
    def create_subtask(self, name: str, args: Func.Args) -> None:
        """
        call another Func with subtask name.
        :param name: key to find the subtask in self subtasks
        :param args: arguments instance of the calling Func
        """
        pass

    @abstractmethod
    def send_to_subtask(self, name: str, *messages: Union[str, VarPtr, Any]) -> None:
        """
        send information to the subtask.
        :param name: specify a subtask by name
        :param messages: if not str or VarPtr, then must be some value that can be converted to VarPtr.
        """
        pass

    @abstractmethod
    def cancel_subtask(self, name: str, reason: str) -> None:
        """
        cancel specified subtask by name with reason.
        """
        pass
