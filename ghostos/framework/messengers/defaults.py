from typing import Optional, Iterable, TYPE_CHECKING, Type, Dict, List
from ghostos.container import Container, Provider
from ghostos.core.runtime.messenger import Messenger, Buffed
from ghostos.core.messages import (
    Message, Payload, Attachment, Role, MessageType,
    Buffer, Stream,
)
from ghostos.core.runtime.threads import GoThreadInfo
from ghostos.core.llms import FunctionalToken
from ghostos.framework.messages.buffers import DefaultBuffer
from ghostos.helpers import uuid
from threading import Lock

if TYPE_CHECKING:
    from ghostos.contracts.logger import LoggerItf

__all__ = [
    'DefaultMessenger', 'TestMessengerProvider'
]


class DefaultMessenger(Messenger, Stream):
    """
    默认的 Deliver, 支持消息的各种工具.
    """

    def __init__(
            self, *,
            depth: int = 0,
            upstream: Optional[Stream] = None,
            thread: Optional["GoThreadInfo"] = None,
            name: Optional[str] = None,
            role: Optional[str] = None,
            buffer: Optional[Buffer] = None,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None,
            saving: bool = True,
            logger: Optional["LoggerItf"] = None,
    ):
        """
        初始化一个 Messenger.
        :param upstream: 如果为 None 的话, 不会对上游发送消息.
        :param thread: 如果不为 None, 会把发送的尾包记录到 thread 里.
        :param name: 消息体的名字.
        :param role: 消息体的角色, 默认设定为 Assistant
        :param buffer: 是否传入自定义的 buffer.
        :param payloads: 每条消息都必须添加的 payload.
        :param attachments: 每条消息都必须添加的 attachments.
        :param functional_tokens: 是否有需要处理的 functional tokens
        :param logger:
        """
        self._depth = depth
        self._thread: Optional[GoThreadInfo] = thread
        # self._streaming_id: str = uuid()
        self._name = name
        self._logger = logger
        self._role = role if role else Role.ASSISTANT.value
        self._upstream: Optional[upstream] = upstream
        self._stopped: bool = False
        self._saving: bool = saving
        self._payloads: Optional[Iterable[Payload]] = payloads
        """默认的 payloads"""
        self._attachments: Optional[Iterable[Attachment]] = attachments
        """消息体默认的附件. """
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
        self._accept_chunks = upstream.accept_chunks() if upstream else False
        # self._sending_stream_id: Optional[str] = None
        # self._sending_stream_buffer: Dict[str, List[Message]] = {}
        self._destroyed: bool = False
        self._locker = Lock()

    # def new(
    #         self, *,
    #         sending: bool = True,
    #         thread: Optional[MsgThread] = None,
    #         name: Optional[str] = None,
    #         buffer: Optional[Buffer] = None,
    #         payloads: Optional[Iterable[Payload]] = None,
    #         attachments: Optional[Iterable[Attachment]] = None,
    #         functional_tokens: Optional[Iterable[FunctionalToken]] = None,
    # ) -> "Messenger":
    #     # payloads 完成初始化.
    #     # copy
    #     messenger = DefaultMessenger(
    #         depth=self._depth + 1,
    #         upstream=self._upstream,
    #         thread=thread,
    #         name=self._name,
    #         role=self._role,
    #         # buffer is None to sub manager
    #         buffer=buffer,
    #         payloads=payloads,
    #         attachments=attachments,
    #         functional_tokens=functional_tokens,
    #     )
    #     return messenger

    def accept_chunks(self) -> bool:
        return self._accept_chunks

    def deliver(self, pack: "Message") -> bool:
        if self.stopped():
            return False

        elif MessageType.is_final(pack):
            # 下游发送的 final 包, 上游会装作已经发送成功.
            return True

        with self._locker:
            # 下游返回 error, 会导致全链路的 messenger 因为 error 而停止.
            # 所以 error 类型的消息, 链路里只能有一个.
            if MessageType.ERROR.match(pack):
                # receive error pack will stop the current streaming.
                self._stop(pack)
                return True
            # return self._map_or_deliver_by_streaming_id(pack)
            return self._buff_then_deliver(pack)

    # def _map_or_deliver_by_streaming_id(self, pack: "Message") -> bool:
    #     """
    #     use streaming id to buff or reduce messages.
    #     """
    #     if self._depth > 0:
    #         return self._buff_then_deliver(pack)
    #     if self._sending_stream_id is None:
    #         self._sending_stream_id = pack.streaming_id
    #
    #     if pack.streaming_id not in self._sending_stream_buffer:
    #         self._sending_stream_buffer[pack.streaming_id] = []
    #     buffer = self._sending_stream_buffer[pack.streaming_id]
    #     buffer.append(pack)
    #     if self._sending_stream_id != pack.streaming_id:
    #         return True
    #     else:
    #         # reduce deliver
    #         return self._reduce_streaming_items()

    # def _reduce_streaming_items(self) -> bool:
    #     if self._sending_stream_id is not None:
    #         items = self._sending_stream_buffer[self._sending_stream_id]
    #         self._sending_stream_buffer[self._sending_stream_id] = []
    #         last = None
    #         for item in items:
    #             success = self._buff_then_deliver(item)
    #             if not success:
    #                 return False
    #             last = item
    #         if last and (last.is_complete() or DefaultMessageTypes.is_protocol_type(last)):
    #             print("\n+++`" + last.content + "`+++\n")
    #             del self._sending_stream_buffer[self._sending_stream_id]
    #             self._sending_stream_id = None
    #             # keep going
    #             return self._reduce_streaming_items()
    #         else:
    #             # still buffering
    #             return True
    #     elif len(self._sending_stream_buffer) == 0:
    #         # all items are sent
    #         self._sending_stream_id = None
    #         self._sending_stream_buffer = {}
    #         return True
    #     else:
    #         for key in self._sending_stream_buffer:
    #             self._sending_stream_id = key
    #             break
    #         return self._reduce_streaming_items()

    def _buff_then_deliver(self, pack: "Message") -> bool:
        delivery = self._buffer.buff(pack)
        return self._deliver_to_upstream(delivery)

    def _deliver_to_upstream(self, delivery: Iterable[Message]) -> bool:
        if self._stopped:
            return False
        for item in delivery:
            if not MessageType.is_protocol_message(item) and item.chunk and not self._accept_chunks:
                continue
            # 如果发送不成功, 直接中断.
            # if self._depth == 0:
            #     item.streaming_id = None
            # if (
            #         self._saving
            #         and self._thread is not None  # thread exists.
            #         and not DefaultMessageTypes.is_protocol_type(item)  # not a protocol type message.
            #         and not item.chunk
            # ):  # is tail package.
            #     # append tail message to thread.
            #     self._thread.append(item)

            if self._upstream is not None:
                success = self._upstream.deliver(item)
                if not success:
                    # in case check upstream is stopped over and over again.
                    self._stopped = self._upstream.stopped()
                    return False
        return True

    def flush(self) -> Buffed:
        if self._stopped or self._destroyed:
            return Buffed(messages=[], callers=[])
        buffed = self._buffer.flush()
        if buffed.unsent:
            self._deliver_to_upstream(buffed.unsent)
        if self._thread:
            self._thread.append(*buffed.messages)
        self._stop(None)
        return Buffed(messages=buffed.messages, callers=buffed.callers)

    def _stop(self, final: Optional[Message]) -> None:
        """
        停止并且发送指定的 final 包. 如果没有指定, 则发送 DefaultTypes.final()
        """
        self._stopped = True
        if self._destroyed:
            return
        if final is None or not MessageType.is_protocol_message(final):
            final = MessageType.final()
        self._deliver_to_upstream([final])
        self.destroy()

    def stopped(self) -> bool:
        if self._stopped:
            return True
        if self._upstream is None:
            return False
        if self._upstream.stopped():
            self._stopped = True
        return self._stopped

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._stopped:
            return
        self.flush()
        if exc_val:
            self._stop(MessageType.ERROR.new(content=str(exc_val)))
        self.destroy()

    def destroy(self) -> None:
        """
        I kind of don't trust python gc, let me help some
        :return:
        """
        if self._destroyed:
            return
        self._destroyed = True
        del self._upstream
        self._buffer = None
        del self._payloads
        del self._attachments
        self._thread = None
        del self._functional_tokens


class TestMessengerProvider(Provider[Messenger]):
    """
    for test only
    """

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Messenger]:
        return Messenger

    def factory(self, con: Container) -> Messenger:
        return DefaultMessenger()
