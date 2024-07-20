from abc import ABC, abstractmethod
from typing import Iterable, NamedTuple, Optional
from ghostiss.core.messages.message import Message, Caller, Payload, Attachment, DefaultTypes
from ghostiss.core.messages.buffers import Buffer


__all__ = [
    "Deliver",
    "Buffed",
    "DefaultDownstreamDeliver",
]


class Buffed(NamedTuple):
    messages: Iterable["Message"]
    """已经向上游发送的消息"""

    callers: Iterable["Caller"]
    """过滤出来的 caller. """


class Deliver(ABC):
    """
    messenger 的原型. Stream 的有状态版本.
    """

    @abstractmethod
    def deliver(self, pack: "Message") -> bool:
        """
        发送一个包.
        """
        pass

    @abstractmethod
    def send(self, messages: Iterable[Message]) -> bool:
        """
        发送消息.
        """
        pass

    @abstractmethod
    def flush(self) -> "Buffed":
        """
        将所有未发送的消息都发送. 然后停止运行.
        """
        pass

    @abstractmethod
    def stopped(self) -> bool:
        """
        是否已经停止接受
        """
        pass


class DefaultDownstreamDeliver(Deliver):
    """
    默认的 Deliver, 支持消息的各种工具.
    """

    def __init__(
            self, *,
            upstream: Optional[Deliver] = None,
            buffer: Optional[Buffer] = None,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
    ):
        self._upstream = upstream
        self._buffer = buffer
        self._stopped = False
        self._payloads = payloads
        """默认的 payloads"""
        self._attachments = attachments
        """消息体默认的附件. """

    def deliver(self, pack: "Message") -> bool:
        if self.stopped():
            return False
        if DefaultTypes.is_final(pack):
            # 下游发送的 final 包, 上游会装作已经发送成功.
            return True
        delivers = self._buffer.buff(pack)
        if self._upstream:
            for item in delivers:
                if not item.pack:
                    item = self._wrap_message(item)

                success = self._upstream.deliver(item)
                if not success:
                    return False
        return True

    def _wrap_message(self, message: Message) -> Message:
        if DefaultTypes.is_protocol_type(message):
            # 如果是协议类型的消息, 则不做添加.
            return message
        if message.pack:
            # pack 直接发送.
            return message
        if self._payloads:
            for p in self._payloads:
                p.set(message)
        if self._attachments:
            for a in self._attachments:
                a.add(message)
        return message

    def send(self, messages: Iterable[Message]) -> bool:
        for item in messages:
            success = self.deliver(item)
            if not success:
                return False
        return True

    def flush(self) -> "Buffed":
        self._stopped = True
        buffed = self._buffer.flush()
        if self._upstream and not self._upstream.stopped():
            for item in buffed.sent:
                self._upstream.deliver(item)
            # 发送一个尾包表示当前流已经结束.
            self._upstream.send(DefaultTypes.final())

        return Buffed(messages=buffed.buffed, callers=buffed.callers)

    def stopped(self) -> bool:
        return self._stopped or (self._upstream is not None and self._upstream.stopped())
