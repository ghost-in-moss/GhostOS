from abc import ABC, abstractmethod
from typing import Iterable, NamedTuple, Optional
from ghostiss.core.messages.message import Message, Caller, Payload, Attachment, DefaultTypes, FunctionalToken
from ghostiss.core.messages.buffers import Buffer, DefaultBuffer

__all__ = [
    "Deliver",
    "Buffed",
    "Messenger",
    "DefaultMessenger",
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
    def stop(self) -> None:
        pass

    @abstractmethod
    def stopped(self) -> bool:
        """
        是否已经停止接受
        """
        pass


class Messenger(Deliver, ABC):

    def downstream(
            self, *,
            deliver: bool = True,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None,
    ) -> "Messenger":
        """
        创建一个下游的流, 只有这个流完成输出后, 上游流才能继续生产下游流.
        :param deliver:
        :param payloads:
        :param attachments:
        :param functional_tokens:
        :return:
        """
        pass


class DefaultMessenger(Messenger):
    """
    默认的 Deliver, 支持消息的各种工具.
    """

    def __init__(
            self, *,
            upstream: Optional[Deliver] = None,
            buffer: Optional[Buffer] = None,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None,
    ):
        self._upstream: Optional[upstream] = upstream
        if buffer is None:
            buffer = DefaultBuffer()
        self._buffer: Buffer = buffer
        self._functional_tokens: Optional[Iterable[FunctionalToken]] = functional_tokens
        self._stopped: bool = False
        self._payloads: Optional[Iterable[Payload]] = payloads
        """默认的 payloads"""
        self._attachments: Optional[Iterable[Attachment]] = attachments
        """消息体默认的附件. """
        self._downstream_messenger: Optional["Messenger"] = None

    def downstream(
            self, *,
            deliver: bool = True,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None,
    ) -> "Messenger":
        if self._downstream_messenger is not None:
            raise RuntimeError(f'only one downstream instance of "Messenger" is allowed')
        _function_tokens = None
        if self._functional_tokens is not None or functional_tokens is not None:
            _function_tokens = []
            if self._functional_tokens:
                _function_tokens.extend(self._functional_tokens)
            if functional_tokens:
                _function_tokens.extend(functional_tokens)
        buffer = DefaultBuffer(functional_tokens=_function_tokens)

        _payloads = None
        if self._payloads is not None or payloads is not None:
            _payloads = []
            if self._payloads:
                _payloads.extend(self._payloads)
            if payloads:
                _payloads.extend(payloads)

        _attachments = None
        if self._attachments is not None or attachments is not None:
            _attachments = []
            if self._attachments:
                _attachments.extend(self._attachments)
            if attachments:
                _attachments.extend(attachments)
        upstream = self._upstream if deliver else None
        downstream = DefaultMessenger(upstream=upstream, buffer=buffer, payloads=_payloads, attachments=_attachments)
        self._downstream_messenger = downstream
        return downstream

    def deliver(self, pack: "Message") -> bool:
        if self.stopped():
            return False
        # 下游返回 error, 会导致全链路的 messenger 因为 error 而停止.
        # 所以 error 类型的消息, 链路里只能有一个.
        if DefaultTypes.ERROR.match(pack):
            self._stop(pack)
            return True

        if DefaultTypes.is_final(pack):
            # 下游发送的 final 包, 上游会装作已经发送成功.
            if self._downstream_messenger:
                # 发送成功了, 就去掉 _downstream_messenger
                # 允许新的 downstream 生产.
                self._downstream_messenger = None
            return True
        delivers = self._buffer.buff(pack)
        # 如果上游存在, 才会真的发送. 但无论如何都会去 buff.
        if self._upstream:
            for item in delivers:
                # 如果是消息的尾包, 则
                if not item.pack:
                    item = self._wrap_message(item)
                # 如果发送不成功, 直接中断.
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
        buffed = self._buffer.flush()
        if self._upstream and not self._upstream.stopped():
            for item in buffed.sent:
                self._upstream.deliver(item)
        self._stop(None)
        return Buffed(messages=buffed.buffed, callers=buffed.callers)

    def stop(self) -> None:
        self._stop(None)

    def _stop(self, final: Optional[Message]) -> None:
        self._stopped = True
        if final is None or not DefaultTypes.is_protocol_type(final):
            final = DefaultTypes.final()
        if self._upstream and not self._upstream.stopped():
            self._upstream.deliver(final)

    def stopped(self) -> bool:
        return self._stopped or (self._upstream is not None and self._upstream.stopped())
