from typing import Optional, Iterable, List, Callable, Self, Union, Protocol, Dict, Any
from abc import ABC, abstractmethod

from ghostos.core.session.events import Event, EventBus
from ghostos.core.session.messenger import Messenger
from ghostos.core.session.processes import GoProcesses, GoProcess
from ghostos.core.session.tasks import GoTasks, GoTaskStruct, TaskBrief
from ghostos.core.session.threads import GoThreads, GoThreadInfo
from ghostos.core.messages import MessageKind, Role, Buffer, Payload, Message
from ghostos.core.llms import FunctionalToken
from ghostos.container import Container
from pydantic import BaseModel

__all__ = ['Session', 'SessionProps', 'SessionStateValue']

SessionProps = Dict[str, Union[Dict, BaseModel]]


class Scope(BaseModel):
    shell_id: str
    process_id: str
    task_id: str
    thread_id: str
    parent_task_id: Optional[str] = None


class Session(ABC):
    """
    Session 管理了一个有状态的会话. 所谓 "有状态的会话", 通常指的是:
    shell + ghost + 多轮对话/多轮思考  运行中的状态.

    Session 则提供了 Ghost 的 Task 运行时状态统一管理的 API.
    通常每个运行中的 Task 都会创建一个独立的 Session.
    Session 在运行周期里不会立刻调用底层 IO 存储消息, 而是要等一个周期正常结束.
    这是为了减少运行时错误对状态机造成的副作用.
    """

    scope: Scope
    """
    the running scope of the session
    """

    globals: Dict[str, Any]
    """
    global values of the session. 
    inherit from parent task or shell props. 
    some key are override by parent task or current task.
    """

    properties: SessionProps
    """ 
    Most important value of the session.
    keep the runtime properties of the task. 
    key is unique to the task handler, value shall be dict or BaseModel.
    value shall be serializable, otherwise the world may crash!!
    
    session 最重要的数据结构, 用来承载所有的运行时数据. 
    key 是数据运行时唯一的 key, 值只能是 dict. 
    所有的值都应该是 Serializable 的, 否则会有世界毁灭之类的灾难爆发!!
    """

    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def alive(self) -> bool:
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
    def refresh(self) -> Self:
        """
        refresh the session, update overdue time and task lock.
        """
        pass

    # @abstractmethod
    # def refresh_lock(self) -> bool:
    #     """
    #     Session 尝试用已有的锁, 更新自身的锁. 更新失败的话, 返回 False.
    #     """
    #     pass

    @abstractmethod
    def task(self) -> "GoTaskStruct":
        """
        获取当前的任务对象.
        描述了任务所有的状态.
        返回的是一份 copy, 只有调用 update 方法才会更新.
        """
        pass

    @abstractmethod
    def thread(self) -> "GoThreadInfo":
        """
        Session 会持有当前任务的 Thread, 只有 finish 的时候才会真正地保存它.
        """
        pass

    @abstractmethod
    def messenger(
            self, *,
            sending: bool = True,
            saving: bool = True,
            thread: Optional[GoThreadInfo] = None,
            name: Optional[str] = None,
            buffer: Optional[Buffer] = None,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None
    ) -> "Messenger":
        """
        Task 当前运行状态下, 向上游发送消息的 Messenger.
        每次会实例化一个 Messenger, 理论上不允许并行发送消息. 但也可能做一个技术方案去支持它.
        Messenger 未来要支持双工协议, 如果涉及多流语音还是很复杂的.
        """
        pass

    @abstractmethod
    def send_messages(self, *messages: MessageKind, remember: bool = True) -> List[Message]:
        """
        发送消息.
        :param messages:
        :param remember: remember the messages within the thread
        :return:
        """
        pass

    @abstractmethod
    def update_task(self, task: "GoTaskStruct") -> None:
        """
        更新当前 session 的 task.
        :param task: 如果不属于当前 session, 则会报错
        """
        pass

    @abstractmethod
    def update_process(self, process: "GoProcess") -> None:
        """
        改动 process 并保存. 通常只在初始化里才需要.
        """
        pass

    @abstractmethod
    def update_thread(self, thread: "GoThreadInfo", update_history: bool) -> None:
        """
        单独更新当前 session 的 thread.
        :param thread: 如果不属于当前 session, 则会报错
        :param update_history: 是否要将 thread 的历史更新掉.
        """
        pass

    @abstractmethod
    def create_tasks(self, *tasks: "GoTaskStruct") -> None:
        """
        创建多个 task. 只有 session.done() 的时候才会执行.
        """
        pass

    # --- 多任务管理的 api. 在 session.finish 时真正执行. --- #

    @abstractmethod
    def fire_events(self, *events: "Event") -> None:
        """
        发送多个事件. 这个环节需要给 event 标记 callback.
        在 session.done() 时才会真正执行.
        """
        pass

    @abstractmethod
    def get_task_briefs(self, *task_ids, children: bool = False) -> List[TaskBrief]:
        """
        获取多个任务的简介.
        :param task_ids: 可以指定要获取的 task id
        :param children: 如果为 true, 会返回当前任务的所有子任务数据.
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


class SessionStateValue(Protocol):
    """
    show a way to easy the session state controlling
    """

    @classmethod
    @abstractmethod
    def load(cls, session: Session) -> Union[Self, None]:
        pass

    @abstractmethod
    def bind(self, session: Session) -> None:
        pass

    @abstractmethod
    def get_or_bind(self, session: Session) -> Self:
        val = self.load(session)
        if val is None:
            self.bind(session)
            val = self
        return val
