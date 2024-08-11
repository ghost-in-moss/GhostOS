from typing import Optional
from abc import ABC, abstractmethod

from ghostiss.core.session.messenger import Messenger
from ghostiss.core.session.processes import Process
from ghostiss.core.session.tasks import Task
from ghostiss.core.session.threads import MsgThread


class Session(ABC):
    """
    对 Ghost 的 Task 运行时状态统一管理的 API.
    通常每个运行中的 Task 都会创建一个独立的 Session.
    Session 在运行周期里不会立刻调用底层 IO 存储消息, 而是要等 Finish 执行后.
    这是为了减少运行时错误对状态机造成的副作用.
    """

    def id(self) -> str:
        return self.process().session_id

    @abstractmethod
    def process(self) -> "Process":
        pass

    @abstractmethod
    def task(self) -> "Task":
        pass

    @abstractmethod
    def thread(self) -> "MsgThread":
        """
        Session 会持有当前 Thread, 只有 finish 的时候才会真正地保存它.
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
        :param thread: 由于 thread 和 task 是绑定的.
        :return:
        """
        pass

    @abstractmethod
    def update_thread(self, thread: "MsgThread") -> None:
        """
        更新当前 session 的 thread.
        :param thread: 如果不属于当前 session, 则会报错
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
