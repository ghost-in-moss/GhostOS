from typing import List
from abc import ABC, abstractmethod
from ghostiss.core.messages.message import Message, Header
from ghostiss.core.messages.attachments import Attachment
from ghostiss.core.messages.packs import Pack

__all__ = ['Messenger']


class Messenger(ABC):
    """
    向下游发包的封装.
    """

    @abstractmethod
    def send(self, *messages: Message) -> None:
        pass

    @abstractmethod
    def send_pack(self, *packs: Pack) -> None:
        pass

    @abstractmethod
    def new(self) -> "Messenger":
        """
        生成一个新的下游流.
        下游流发送的消息都会发送到这里.
        Messenger 不允许并行使用, 只有下游的 Messenger flush 了, 当前的 messenger 才能重新发送消息或者 wait.
        """
        pass

    @abstractmethod
    def with_header(self, header: Header) -> "Messenger":
        """
        消息会包含 header 的讯息. 可以覆盖.
        """
        pass

    @abstractmethod
    def with_attachments(self, attachments: List[Attachment]) -> "Messenger":
        """
        所有通过它发送的消息都会携带相关的 attachments.
        """
        pass

    @abstractmethod
    def flush(self) -> List[Message]:
        """
        多线程模式下的消息异步发送 & 同步等待实现. 理论上有三个线程:
        1. 运行 ghost 系统的主线程.
        2. ghost 同步运行的线程.
        3. 调用 LLM 的线程.

        3. 通过 iterable 传值给 2,  2 通过上游的 Send 方法发送消息.
        传输过程可以通过同步等待, 也可以通过 thread queue.

        调用 flush 方法, 返回所有发送出去的消息体.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        习惯性增加一个方法, 手动清掉对象. 避免 python 循环依赖导致垃圾回收失败.
        """
        pass
