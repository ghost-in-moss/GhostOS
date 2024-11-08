from __future__ import annotations
from typing import (
    Type, Generic, Protocol, ClassVar, TypeVar,
    Tuple, Optional, Iterable, List, Self, Union, Dict,
)

from abc import ABC, abstractmethod
from ghostos.common import Identifiable, Entity, EntityType, EntityMeta, to_entity_meta, from_entity_meta
from ghostos.core.runtime import (
    TaskState,
)
from ghostos.core.runtime.events import Event
from ghostos.core.runtime.tasks import GoTaskStruct, TaskBrief
from ghostos.core.runtime.threads import GoThreadInfo
from ghostos.core.messages import MessageKind, Message, Stream, Caller, Payload
from ghostos.container import Container
from ghostos.helpers import generate_import_path
from pydantic import BaseModel
import json

"""
# Core Concepts of GhostOS framework.

The word `Ghost` is picked from `Ghost In the Shell` movie.
The Ghost can perform as both conversational object or an async function.
Ghost is the abstract of atomic state machine unit in the GhostOS.

for example, llm-based `Agent` is a state machine, an implementation of Ghost in GhostOS.

Why Agent is a state machine?
1. Agent receives an event at a time, not parallel, or face brain split.
2. Agent keep it state in the system prompt and messages, by nature language.
3. Agent take actions that matching expectation.
So Agent is an AI-State-Machine, defined from prompt, not code; executed by Model, not Interpreter.

About the Ghost Abstract:
1. it is a class.
2. the ghost class can construct ghost instance.
3. any ghost instance can run as a conversational task
4. a conversational task runs in turns, receiving event and replying messages.
5. the conversational task is stateful, accept one event at a time.
6. the conversational task reach the end when it is canceled, done or failed
7. all the ghost has a Goal model to describe its current achievement.
8. The Ghost Class shall be simple and clear to the AI models, when they are creating ghosts themselves.

and the Most valuable features about ghost are:
1. ghosts shall be fractal, can be called by other ghosts.
2. ghost shall be defined by code, which can be generated by meta-agents.
"""

__all__ = ("Ghost", "Session", "GhostDriver", "Props", "GhostOS", "Operator", "StateValue")


class Ghost(Identifiable, EntityType, ABC):
    """
    the class defines the model of a kind of ghosts.
    four parts included:
    1. configuration of the Ghost, which is Ghost.__init__. we can predefine many ghost instance for special scenes.
    2. context is always passed by the Caller of a ghost instance. each ghost class has it defined context model.
    3. goal is the static output (other than conversation messages) of a ghost instance.
    4. driver is
    """

    Props: ClassVar[Union[Type[Props], None]]
    """ props is the model of properties that passed from caller, and alternative during runtime"""

    Artifact: ClassVar[Union[Type, None]]
    """ the model of the ghost's artifact, is completing during runtime"""

    Driver: Type[GhostDriver] = None
    """ separate ghost's methods to the driver class, make sure the ghost is simple and clear to other ghost"""


G = TypeVar("G", bound=Ghost)


class GhostDriver(Generic[G], ABC):
    """
    Ghost class is supposed to be a data class without complex methods definitions.
    so it seems much clear when prompt to the LLM or user-level developer.
    when LLM is creating a ghost class or instance, we expect it only see the code we want it to see,
    without knowing the details codes of it, for safety / fewer tokens / more focus or other reasons.

    so the methods of the ghost class defined in this class.
    only core developers should know details about it.
    """

    def __init__(self, ghost: G) -> None:
        self.ghost = ghost

    @abstractmethod
    def get_goal(self, session: Session) -> Optional[G.Artifact]:
        """
        generate the ghost goal from session_state
        may be the Goal Model is a SessionStateValue that bind to it.

        The AI behind a ghost is not supposed to operate the session object,
        but work on the goal through functions or Moss Injections.
        """
        pass

    @abstractmethod
    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        """
        all the state machine is only handling session event with the predefined operators.
        """
        pass


class Operator(Protocol):
    """
    Operator to operating the GhostOS through the Session encapsulation.

    The Operator is just like the primitives of any coding language.
    for example, GhostOS have some operators work like python's `return`, `yield`, `await` .

    I'm not capable to develop a real OS or a new coding language for AI,
    GhostOS is built above python with the additional complexities.

    Operators should be predefined, offer to user-level developer, or AI-models.
    """

    @abstractmethod
    def run(self, session: Session) -> Union[Operator, None]:
        """
        :return: None means stop the loop, otherwise keep going.

        operator returns an operator is a way to encapsulate repetitive codes.
        """
        pass

    @abstractmethod
    def destroy(self):
        """
        Python gc is not trust-worthy
        Especially A keep B, B keep C, C keep A, father and child keep each other.
        I prefer to del the object attributes in the end of the object lifecycle.
        """
        pass


class Props(Payload, Entity, ABC):
    """
    is strong-typed model for runtime alternative properties of a ghost.
    """
    key = "ghost_props"
    """props is also a Payload class, which can be bound to event or messages"""

    __children__: List[Props]
    """ children is fractal sub context nodes"""

    def with_children(self, *children: Props) -> Props:
        self.__children__.extend(children)
        return self

    @abstractmethod
    def self_prompt(self, container: Container, depth: int = 0) -> str:
        """
        generate prompt by self, without children
        :param container:
        :param depth:
        :return:
        """
        pass

    def get_prompt(self, container: Container, depth: int = 0) -> str:
        self_prompt = self.self_prompt(container, depth=depth)
        prompts = [self_prompt]
        for child in self.__children__:
            prompts.append(child.get_prompt(container, depth=depth + 1))
        return "\n\n".join([prompt.rstrip() for prompt in prompts])

    def __to_entity_meta__(self) -> EntityMeta:
        type_ = generate_import_path(self.__class__)
        ctx_data = self.model_dump(exclude_defaults=True)
        children_data = []
        for child in self.__children__:
            children_data.append(to_entity_meta(child))
        data = {"ctx": ctx_data, "children": children_data}
        content = json.dumps(data)
        return EntityMeta(type=type_, content=content.encode())

    @classmethod
    def __from_entity_meta__(cls, meta: EntityMeta) -> Self:
        data = json.loads(meta["content"])
        ctx_data = data["ctx"]
        children_data = data["children"]
        result = cls(**ctx_data)
        children = []
        for child in children_data:
            children.append(from_entity_meta(child))
        return result.with_children(*children)


class GhostOS(Protocol):

    @abstractmethod
    def container(self) -> Container:
        """
        root container for GhostOS
        """
        pass

    @abstractmethod
    def send_event(self, event: Event) -> None:
        """
        send an event into the loop.
        the event always has a task_id, so the task shall be created first.
        """
        pass

    @abstractmethod
    def converse(
            self,
            ghost: G,
            context: G.Props,
    ) -> Conversation[G]:
        """
        create a top-level conversation with a ghost.
        top-level means task depth is 0.
        So it never locked until the conversation is created.
        """
        pass

    @abstractmethod
    def call(
            self,
            ghost: G,
            props: G.Props,
            instructions: Optional[Iterable[Message]] = None,
            *,
            timeout: float = 0.0,
    ) -> Tuple[Union[G.Artifact, None], TaskState]:
        """
        run a ghost task until it stopped,
        """
        pass

    @abstractmethod
    def background_run_event(
            self,
            *,
            timeout: float = 0.0,
    ) -> Union[Event, None]:
        """
        run the event loop for the ghosts in the Shell.
        1. pop task notification.
        2. try to converse the task
        3. if failed, pop another task notification.
        4. if success, pop task event and handle it until no event found.
        5. send a task notification after handling, make sure someone check the task events are empty.
        only the tasks that depth > 0 have notifications.
        background run itself is blocking method, run it in a separate thread for parallel execution.
        :param timeout:
        :return: the handled event
        """
        pass


class Conversation(Protocol[G]):
    """
    interface for operate on synchronized (task is locked) ghost
    """

    @abstractmethod
    def session(self) -> Session:
        """
        Session of the Conversation
        """
        pass

    @abstractmethod
    def is_done(self) -> bool:
        """
        weather the conversation is done or not
        """
        pass

    @abstractmethod
    def respond(
            self,
            inputs: Iterable[Message],
            props: Optional[G.Props] = None,
            *,
            history: Optional[Iterable[Message]] = None,
    ) -> Iterable[Message]:
        """
        create response immediately by inputs. the inputs will change to event.
        """
        pass

    @abstractmethod
    def respond_event(self, event: Event) -> Iterable[Message]:
        """
        create response to the event immediately
        :param event:
        :return:
        """
        pass

    @abstractmethod
    def pop_event(self) -> Optional[Event]:
        """
        pop event of the current task
        """
        pass

    @abstractmethod
    def fail(self, error: Exception) -> bool:
        """
        exception occur
        :return: catch the exception or not
        """
        pass

    @abstractmethod
    def close(self):
        """
        close the conversation
        """
        pass

    @abstractmethod
    def closed(self) -> bool:
        """
        closed
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.close():
            return
        if exc_val is not None:
            return self.fail(exc_val)
        else:
            self.close()
            return None


class Messenger(Stream, ABC):
    """
    Messenger is a bridge of message streams
    Messenger finish when the flush method is called.
    Each messenger can nest sub messengers, when sub messenger is finished,
    the parent messenger is not finished until the flush is called.

    why this is an abstract base class?
    there may be more abilities during streaming are needed,
    this project can only provide a basic one.
    """

    @abstractmethod
    def flush(self) -> Tuple[List[Message], List[Caller]]:
        """
        flush the buffed messages, finish the streaming of this messenger.
        the message buffer shall join all the chunks to message item.
        after the messenger is flushed, it can not send any new message.
        """
        pass


class StateValue(ABC):
    """
    session state value
    """

    @abstractmethod
    def get(self, session: Session) -> Optional[Self]:
        pass

    @abstractmethod
    def bind(self, session: Session) -> None:
        pass

    def get_or_bind(self, session: Session) -> Self:
        value = self.get(session)
        if value is None:
            value = self
            self.bind(session)
        return value


class Session(Protocol[G]):
    """
    Session 管理了一个有状态的会话. 所谓 "有状态的会话", 通常指的是:
    shell + ghost + 多轮对话/多轮思考  运行中的状态.

    Session 则提供了 Ghost 的 Task 运行时状态统一管理的 API.
    通常每个运行中的 Task 都会创建一个独立的 Session.
    Session 在运行周期里不会立刻调用底层 IO 存储消息, 而是要等一个周期正常结束.
    这是为了减少运行时错误对状态机造成的副作用.
    """

    class Scope(BaseModel):
        """
        scope of the session.
        """
        task_id: str
        parent_task_id: Optional[str] = None

    scope: Scope
    """the running scope of the session"""

    state: Dict[str, Union[Dict, BaseModel]]
    """session state that keep session state values"""

    container: Container
    """Session level container"""

    task: GoTaskStruct
    """current task"""

    thread: GoThreadInfo
    """thread info of the task"""

    @abstractmethod
    def is_alive(self) -> bool:
        """
        Session 对自身任务进行状态检查.
        如果这个任务被取消或终止, 则返回 false.
        基本判断逻辑:
        1. 消息上游流没有终止.
        2. task 持有了锁.
        3. 设置的超时时间没有过.
        """
        pass

    @abstractmethod
    def ghost(self) -> G:
        """
        current ghost instance
        :return:
        """
        pass

    @abstractmethod
    def get_props(self) -> G.Props:
        """
        current context for the ghost
        """
        pass

    @abstractmethod
    def get_artifact(self) -> G.Artifact:
        """
        :return: the current state of the ghost goal
        """
        pass

    @abstractmethod
    def goal(self) -> G.Artifact:
        pass

    @abstractmethod
    def refresh(self) -> Self:
        """
        refresh the session, update overdue time and task lock.
        """
        pass

    @abstractmethod
    def messenger(
            self, *,
            remember: bool = True,
    ) -> "Messenger":
        """
        Task 当前运行状态下, 向上游发送消息的 Messenger.
        每次会实例化一个 Messenger, 理论上不允许并行发送消息. 但也可能做一个技术方案去支持它.
        Messenger 未来要支持双工协议, 如果涉及多流语音还是很复杂的.
        """
        pass

    @abstractmethod
    def respond(
            self,
            messages: Iterable[MessageKind],
            remember: bool = True,
    ) -> Tuple[List[Message], List[Caller]]:
        """
        发送消息, 但不影响运行状态.
        """
        pass

    # --- 基本操作 --- #
    @abstractmethod
    def self_finish(self, status: str = "", *replies: MessageKind) -> Operator:
        """
        finish self task
        :param status: describe status of the task
        :param replies: replies to parent task or user
        """
        pass

    @abstractmethod
    def self_fail(self, status: str, *replies: MessageKind) -> Operator:
        """
        self task failed.
        :param status: describe status of the task
        :param replies: replies to parent task or user
        """
        pass

    @abstractmethod
    def self_wait(self, status: str, *replies: MessageKind) -> Operator:
        """
        wait for the parent task or user to provide more information or further instruction.
        :param status: describe current status
        :param replies: question, inform or
        """
        pass

    # --- subtask 相关 --- #

    @abstractmethod
    def cancel_subtask(self, ghost: G, reason: str = "") -> None:
        """
        取消子任务.
        :param ghost:
        :param reason:
        :return:
        """
        pass

    def send_subtask(self, ghost: G, *messages: MessageKind, ctx: Optional[G.Props] = None) -> None:
        """
        发送消息给子任务. 如果子任务不存在, 会创建.
        子任务会通过 event 与父任务通讯.
        :param ghost:
        :param messages:
        :param ctx:
        :return:
        """
        pass

    def create_subtask(self, ghost: G, ctx: G.Props, instruction: str) -> None:
        """
        创建子任务并运行.
        :param ghost:
        :param ctx:
        :param instruction:
        :return:
        """
        pass

    def call(self, ghost: G, ctx: G.Props) -> G.Artifact:
        """
        创建一个子任务, 阻塞并等待它完成.
        :param ghost:
        :param ctx:
        :return: the Goal of the task. if the final state is not finish, throw an exception.
        """
        pass

    # --- 更底层的 API. --- #

    @abstractmethod
    def create_tasks(self, *tasks: "GoTaskStruct") -> None:
        """
        创建多个 task. 只有 session.done() 的时候才会执行.
        """
        pass

    @abstractmethod
    def fire_events(self, *events: "Event") -> None:
        """
        发送多个事件. 这个环节需要给 event 标记 callback.
        在 session.done() 时才会真正执行.
        """
        pass

    @abstractmethod
    def get_task_briefs(self, *task_ids) -> List[TaskBrief]:
        """
        获取多个任务的简介.
        :param task_ids: 可以指定要获取的 task id
        """
        pass

    @abstractmethod
    def save(self) -> None:
        """
        完成 session, 需要清理和真正保存状态.
        需要做的事情包括:
        1. 推送 events, events 要考虑 task 允许的栈深问题. 这个可以后续再做.
        2. 保存 task. task 要对自己的子 task 做垃圾回收. 并且保留一定的子 task 数, 包含 dead task.
        3. 保存 thread
        4. 保存 processes.
        5. 考虑到可能发生异常, 要做 transaction.
        6. 退出相关的逻辑只能在 finish 里实现.
        :return:
        """
        pass

    @abstractmethod
    def fail(self, err: Optional[Exception]) -> bool:
        """
        任务执行异常的处理. 需要判断任务是致命的, 还是可以恢复.
        :param err:
        :return:
        """
        pass

    @abstractmethod
    def done(self) -> None:
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        手动清理数据, 方便垃圾回收.
        """
        pass

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        intercept = None
        if exc_val is not None:
            intercept = self.fail(exc_val)
        else:
            self.done()
        self.destroy()
        return intercept
