from typing import Optional, Iterable, NamedTuple, List, Tuple
from abc import ABC, abstractmethod
from ghostiss.core.messages.message import Message, Payload, Attachment, Caller
from ghostiss.core.messages.buffers import Buffer
from ghostiss.core.messages.stream import Stream
from ghostiss.core.runtime.threads import MsgThread
from ghostiss.core.runtime.llms import FunctionalToken


class Buffed(NamedTuple):
    messages: List["Message"]
    """已经向上游发送的消息"""

    callers: List["Caller"]
    """过滤出来的 caller. """


class Messenger(Stream, ABC):
    """
    Messenger 是流式传输消息的桥梁.
    通过 messenger 发送完消息后, 需要执行 done 方法.
    它可以通过 downstream 方法生成下级 messenger
    """

    @abstractmethod
    def new(
            self, *,
            sending: bool = True,
            thread: Optional[MsgThread] = None,
            name: Optional[str] = None,
            buffer: Optional[Buffer] = None,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None
    ) -> "Messenger":
        """
        生成一个新的 Messenger 供发送消息使用. 发送完应该调用 flush 方法.
        :param sending: 消息是否向上游发送. 为 false 的话不会真正对上游发送.
        :param thread: 如果传入了 thread, 在 flush 时会自动将消息保存到 thread 内.
        :param name: 所有的消息体默认都添加 name.
        :param buffer: 自定义 buffer, 也可以用于过滤消息.
        :param payloads: 消息默认添加的 payloads.
        :param attachments: 消息默认添加的 attachments.
        :param functional_tokens: 是否添加 functional tokens.
        :return: 返回一个新的 messenger.
        """
        pass

    @abstractmethod
    def flush(self) -> Tuple[List[Message], List[Caller]]:
        """
        将过程中发送的消息进行粘包, 并返回粘包后的结果.
        运行完 done, 会中断后续的输出.
        """
        pass
