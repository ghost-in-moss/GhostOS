from typing import TYPE_CHECKING, Optional
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from ghostiss.core.runtime.processes import Process
    from ghostiss.core.runtime.tasks import Task
    from ghostiss.core.runtime.threads import Thread


class Session(ABC):

    @abstractmethod
    def process(self) -> "Process":
        pass

    @abstractmethod
    def task(self) -> "Task":
        pass

    @abstractmethod
    def thread(self) -> "Thread":
        """
        Session 会持有当前 Thread, 只有 finish 的时候才会真正地保存它.
        """
        pass

    @abstractmethod
    def update_task(self, task: "Task", thread: Optional["Thread"] = None) -> None:
        """
        更新当前 session 的 task.
        :param task: 如果不属于当前 session, 则会报错
        :param thread: 由于 thread 和 task 是绑定的.
        :return:
        """
        pass

    @abstractmethod
    def update_thread(self, thread: "Thread") -> None:
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
