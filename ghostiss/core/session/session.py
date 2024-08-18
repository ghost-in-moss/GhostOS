from typing import Optional, Iterable, List, Callable
from abc import ABC, abstractmethod

from ghostiss.core.session.events import Event
from ghostiss.core.session.messenger import Messenger
from ghostiss.core.session.processes import Process
from ghostiss.core.session.tasks import Task
from ghostiss.core.session.threads import MsgThread
from ghostiss.core.messages import MessageKind, Role
from ghostiss.entity import EntityMeta

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

    def with_ghost(
            self, *,
            name: str,
            role: str = Role.ASSISTANT.value,
    ) -> "Session":
        """
        添加 Ghost 相关的信息.
        :param name: ghost (agent) name
        :param role: message role.
        :return: self
        """
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
    def refresh_lock(self) -> bool:
        """
        :return:
        """
        pass

    # @abstractmethod
    # def refresh_lock(self) -> bool:
    #     """
    #     Session 尝试用已有的锁, 更新自身的锁. 更新失败的话, 返回 False.
    #     """
    #     pass

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
    def send_messages(self, *messages: MessageKind, role: str = Role.ASSISTANT.value) -> None:
        """
        发送消息.
        :param messages:
        :param role:
        :return:
        """
        pass

    @abstractmethod
    def update_task(self, task: "Task", thread: Optional["MsgThread"] = None) -> None:
        """
        更新当前 session 的 task.
        :param task: 如果不属于当前 session, 则会报错
        :param thread: 由于 thread 和 task 是绑定的, 需要一起保存. update thread 的时候, thread 的 appending 等信息会更新.
        """
        pass

    @abstractmethod
    def update_process(self, process: "Process") -> None:
        pass

    @abstractmethod
    def update_thread(self, thread: "MsgThread") -> None:
        """
        单独更新当前 session 的 thread.
        :param thread: 如果不属于当前 session, 则会报错
        """
        pass

    # --- 多任务管理的 api. 在 session.finish 时真正执行. --- #

    @abstractmethod
    def fire_events(self, *events: "Event") -> None:
        """
        发送多个事件.
        """
        pass

    @abstractmethod
    def future(self, name: str, call: Callable[[], Iterable[MessageKind]], reason: str) -> None:
        """
        异步运行一个函数, 将返回的消息作为 think 事件发送.
        :param name: task name
        :param call:
        :param reason:
        :return:
        """
        pass

    @abstractmethod
    def cancel_tasks(self, *task_ids: str) -> None:
        """
        取消多个任务.
        :param task_ids:
        :return:
        """
        pass

    @abstractmethod
    def finish(self) -> None:
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
    def fail(self, err: Optional[Exception]) -> None:
        """
        任务执行异常的处理. 需要判断任务是致命的, 还是可以恢复.
        :param err:
        :return:
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        手动清理数据, 方便垃圾回收.
        """
        pass
