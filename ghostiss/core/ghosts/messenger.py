from typing import Optional, Iterable, NamedTuple, List, Tuple, TYPE_CHECKING, Type
from abc import ABC, abstractmethod
from ghostiss.container import Container, Provider
from ghostiss.core.messages.message import Message, Payload, Attachment, Role, Caller, DefaultTypes, FunctionalToken
from ghostiss.core.messages.buffers import Buffer, DefaultBuffer
from ghostiss.core.messages.stream import Stream
from ghostiss.core.runtime.threads import Thread

if TYPE_CHECKING:
    from ghostiss.contracts.logger import LoggerItf


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
            thread: Optional[Thread] = None,
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


class DefaultMessenger(Messenger, Stream):
    """
    默认的 Deliver, 支持消息的各种工具.
    """

    def __init__(
            self, *,
            thread: "Thread",
            upstream: Optional[Stream] = None,
            saving: bool = True,
            name: Optional[str] = None,
            role: Optional[str] = None,
            buffer: Optional[Buffer] = None,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None,
            logger: Optional["LoggerItf"] = None,
    ):
        self._thread = thread
        self._saving = saving
        self._name = name
        self._logger = logger
        self._role = role if role else Role.ASSISTANT.value
        self._upstream: Optional[upstream] = upstream
        self._stopped: bool = False
        self._payloads: Optional[Iterable[Payload]] = payloads
        """默认的 payloads"""
        self._attachments: Optional[Iterable[Attachment]] = attachments
        """消息体默认的附件. """
        self._downstream_messenger: Optional["Messenger"] = None
        self._functional_tokens = functional_tokens
        if buffer is None:
            buffer = DefaultBuffer(
                name=self._name,
                role=self._role,
                payloads=self._payloads,
                attachments=self._attachments,
                functional_tokens=self._functional_tokens,
            )
        self._buffer: Buffer = buffer

    def new(
            self, *,
            sending: bool = True,
            thread: Optional[Thread] = None,
            name: Optional[str] = None,
            buffer: Optional[Buffer] = None,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None,
    ) -> "Messenger":
        # payloads 完成初始化.
        _payloads = None
        if self._payloads is not None or payloads is not None:
            payloads_map = {}
            if self._payloads:
                for payload in self._payloads:
                    payloads_map[payload.key] = payload
            if payloads:
                for payload in payloads:
                    payloads_map[payload.key] = payload
            _payloads = payloads_map.values()

        # attachments 初始化.
        _attachments = None
        if self._attachments is not None or attachments is not None:
            _attachments = []
            if self._attachments:
                _attachments.extend(self._attachments)
            if attachments:
                _attachments.extend(attachments)

        # 如果能传输数据, 则传递上游的 upstream.
        upstream = self._upstream if sending else None
        thread = thread if thread else self._thread
        functional_tokens = functional_tokens if functional_tokens else self._functional_tokens
        messenger = DefaultMessenger(
            upstream=upstream,
            thread=thread,
            name=self._name,
            role=self._role,
            buffer=buffer,
            payloads=_payloads,
            attachments=_attachments,
            functional_tokens=functional_tokens,
        )
        return messenger

    def deliver(self, pack: "Message") -> bool:
        if self.stopped():
            return False
        if not pack:
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
        delivery = self._buffer.buff(pack)
        return self._deliver(delivery)

    def _deliver(self, delivery: Iterable[Message]) -> bool:
        for item in delivery:
            if self._saving and not DefaultTypes.is_protocol_type(item) and not item.pack and self._thread:
                self._thread.update([item])
            if self._upstream:
                # 如果发送不成功, 直接中断.
                success = self._upstream.deliver(item)
                if not success:
                    return False
        return True

    def send(self, messages: Iterable[Message]) -> bool:
        for item in messages:
            success = self.deliver(item)
            if not success:
                return False
        return True

    def flush(self) -> "Buffed":
        if self._stopped:
            return Buffed(messages=[], callers=[])

        buffed = self._buffer.flush()
        if buffed.unsent:
            self._deliver(buffed.unsent)
        return Buffed(messages=buffed.messages, callers=buffed.callers)

    def _stop(self, final: Optional[Message]) -> None:
        """
        停止并且发送指定的 final 包. 如果没有指定, 则发送 DefaultTypes.final()
        """
        self._stopped = True
        if final is None or not DefaultTypes.is_protocol_type(final):
            final = DefaultTypes.final()
        if self._upstream and not self._upstream.stopped():
            self._upstream.deliver(final)

    def stopped(self) -> bool:
        return self._stopped or (self._upstream is not None and self._upstream.stopped())


class TestMessengerProvider(Provider[Messenger]):
    """
    for test only
    """

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Messenger]:
        return Messenger

    def factory(self, con: Container) -> Messenger:
        return DefaultMessenger(thread=Thread())
