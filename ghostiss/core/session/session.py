from typing import Optional
from abc import ABC, abstractmethod

from ghostiss.core.session.events import Event
from ghostiss.core.session.messenger import Messenger
from ghostiss.core.session.processes import Process
from ghostiss.core.session.tasks import Task
from ghostiss.core.session.threads import MsgThread

__all__ = ['Session']


class Session(ABC):
    """
    Session 管理了一个有状态的会话. 所谓 "有状态的会话", 通常指的是:
    shell + ghost + 多轮对话/多轮思考  运行中的状态.

    Session 则提供了 Ghost 的 Task 运行时状态统一管理的 API.
    通常每个运行中的 Task 都会创建一个独立的 Session.
    Session 在运行周期里不会立刻调用底层 IO 存储消息, 而是要等 Finish 执行后.
    这是为了减少运行时错误对状态机造成的副作用.
    """

    def id(self) -> str:
        """
        session 自身的 id.
        """
        return self.process().session_id

    @abstractmethod
    def locked(self) -> bool:
        """
        session 是否已经上锁.
        """
        pass

    @abstractmethod
    def alive(self) -> bool:
        """
        Session 对自身任务进行状态检查.
        如果这个任务被取消或终止, 则返回 false.
        一些关键方法在 not alive() 时执行, 会抛出异常.
        典型的例子是上游 cancel 了当前任务.
        """
        pass

    @abstractmethod
    def refresh_lock(self) -> bool:
        """
        Session 尝试用已有的锁, 更新自身的锁. 更新失败的话, 返回 False.
        """
        pass

    @abstractmethod
    def process(self) -> "Process":
        """
        当前会话所处的进程数据.
        不允许直接修改. 只有指定的 API 会修改结果并保存.
        """
        pass

    @abstractmethod
    def task(self) -> "Task":
        """
        获取当前的任务对象.
        描述了任务所有的状态.
        返回的是一份 copy, 只有调用 update 方法才会更新.
        """
        pass

    @abstractmethod
    def thread(self) -> "MsgThread":
        """
        Session 会持有当前任务的 Thread, 只有 finish 的时候才会真正地保存它.
        """
        pass

    @abstractmethod
    def messenger(self) -> "Messenger":
        """
        Task 当前运行状态下, 向上游发送消息的 Messenger.
        每次会实例化一个 Messenger, 理论上不允许并行发送消息. 但也可能做一个技术方案去支持它.
        Messenger 未来要支持双工协议, 如果涉及多流语音还是很复杂的.
        """
        pass

    @abstractmethod
    def update_task(self, task: "Task", thread: Optional["MsgThread"] = None) -> None:
        """
        更新当前 session 的 task.
        :param task: 如果不属于当前 session, 则会报错
        :param thread: 由于 thread 和 task 是绑定的, 需要一起保存.
        """
        pass

    @abstractmethod
    def update_thread(self, thread: "MsgThread") -> None:
        """
        单独更新当前 session 的 thread.
        :param thread: 如果不属于当前 session, 则会报错
        """
        pass

    @abstractmethod
    def fire_event(self, event: "Event") -> None:
        """
        发送一个事件.
        :param event:
        :return:
        """
        pass

    @abstractmethod
    def finish(self, err: Optional[Exception]) -> None:
        """
        完成 session, 需要清理和真正保存状态.
        :return:
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        手动清理数据, 方便垃圾回收.
        """
        pass
