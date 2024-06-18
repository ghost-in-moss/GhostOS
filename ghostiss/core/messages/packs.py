from abc import ABC, abstractmethod
from typing import TypedDict, Optional, Iterable, Set, NamedTuple, List
from enum import Enum
from ghostiss.core.messages.message import Message, Header, Caller
from ghostiss.core.messages.openai import ChatCompletionMessage

__all__ = [
    "PackKind", "Pack",
    "Deliver", "BasicDeliver",
    "Buffer",
    "Spliter",
    "UpStream",
    "Decoder", "Buffed",
]


class Pack(TypedDict, total=False):
    kind: str
    """pack kind"""

    data: dict
    """pack data"""


class PackKind(str, Enum):
    """
    默认的包类型.
    """

    HEADER = "header"
    """流式输出单个消息的首包, 主要是 message header. 意味着要新创建一个消息体. """

    TAIL = "tail"
    """流式输出单个消息的尾包, 可以包含任何讯息. 都会覆盖重写原有的数据."""

    FINAL = "final"
    """流式输出的结束标记. 标记整个流输出已经结束. """

    ERROR = "error"
    """一个异常的 message"""

    MESSAGE = "message"
    """一个完整的 message. """

    OPENAI_DELTA = "openai_delta"

    def new(self, data: Optional[dict] = None) -> "Pack":
        if data is None:
            data = {}
        return Pack(kind=self.value, data=data)

    def match(self, pack: Pack) -> bool:
        return self == pack["kind"]

    @classmethod
    def transport_kinds(cls) -> Set["PackKind"]:
        """
        拥有通讯语义的.
        """
        return {cls.HEADER, cls.TAIL, cls.FINAL, cls.ERROR, cls.MESSAGE}

    @classmethod
    def is_new(cls, pack: Pack) -> bool:
        kind = pack["kind"]
        return kind == cls.HEADER or kind == cls.MESSAGE

    @classmethod
    def is_final(cls, pack: Pack) -> bool:
        kind = pack["kind"]
        return kind == cls.FINAL or cls.ERROR

    @classmethod
    def new_message(cls, msg: Message) -> "Pack":
        return cls.MESSAGE.new(msg.model_dump())

    @classmethod
    def new_header(cls, header: Header) -> "Pack":
        return cls.HEADER.new(header.model_dump())

    @classmethod
    def new_final(cls, data: dict) -> "Pack":
        return cls.FINAL.new(data)

    @classmethod
    def new_tail(cls, msg: Message) -> "Pack":
        return cls.TAIL.new(msg.model_dump())

    @classmethod
    def is_chunk(cls, kind: str) -> bool:
        return kind not in cls.transport_kinds()

    @classmethod
    def new_openai_delta(cls, msg: ChatCompletionMessage) -> "Pack":
        return cls.OPENAI_DELTA.new(msg.model_dump())


class Buffed(NamedTuple):
    messages: Iterable[Message]
    """已经向上游发送的消息"""

    callers: Iterable[Caller]
    """过滤出来的 caller. """


class Decoder(ABC):
    """
    粘包.
    """

    @abstractmethod
    def receive(self, pack: Pack) -> None:
        pass

    @abstractmethod
    def buffed(self) -> Buffed:
        pass


class Buffer(ABC):
    """
    缓冲输入的 pack, 不一定对外发送.
    """

    @abstractmethod
    def buff(self, pack: Pack) -> Iterable[Pack]:
        pass

    @abstractmethod
    def flush(self) -> Iterable[Pack]:
        pass


class Spliter(ABC):
    """
    拆包.
    """

    @abstractmethod
    def split(self, pack: Pack) -> Iterable[Pack]:
        """
        拆分上游的 pack
        """
        pass


class UpStream(ABC):
    """
    向上游发送包. 如果为 false, 则意味着不允许发送.
    """

    @abstractmethod
    def send(self, pack: Pack) -> bool:
        pass


class Deliver(ABC):
    """
    messenger 的原型.
    """

    @abstractmethod
    def send(self, pack: Pack) -> bool:
        """
        发送一个包.
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """
        将所有未发送的消息都发送. 然后停止运行.
        """
        pass

    @abstractmethod
    def buffer(self) -> Buffed:
        """
        已经缓冲的消息.
        """
        pass

    @abstractmethod
    def stopped(self) -> bool:
        """
        是否已经停止接受
        """
        pass


class BasicDeliver(Deliver):
    """
    一个基础的实现.
    """

    def __init__(
            self,
            decoder: Decoder,
            upstream: Optional[UpStream] = None,
            buffer: Optional[Buffer] = None,
            parser: Optional[Spliter] = None,
    ):
        self._stopped = False
        self._decoder = decoder
        self._upstream = upstream
        self._buffer: Optional[Buffer] = buffer
        self._parser: Optional[Spliter] = parser

    def send(self, pack: Pack) -> bool:
        if self._stopped:
            return False
        splits = self._split_pack(pack)

        for item in splits:
            sent = self._buff_pack(item)
            for sent_pack in sent:
                self._send_pack(sent_pack)
        return not self._stopped

    def _split_pack(self, pack: Pack) -> Iterable[Pack]:
        parser = self._parser
        if parser is None:
            yield pack
        else:
            return parser.split(pack)

    def _buff_pack(self, pack: Pack) -> Iterable[Pack]:
        buffer = self._buffer
        if buffer is None:
            yield pack
        else:
            return buffer.buff(pack)

    def _send_pack(self, pack: Pack) -> bool:
        if self._stopped:
            return False
        decoder = self._decoder
        # 先存储.
        if decoder is not None:
            decoder.receive(pack)

        # 如果上游流存在, 就发送.
        if self._upstream is not None:
            ok = self._upstream.send(pack)
            if not ok:
                self._stopped = True
                return False

    def flush(self) -> None:
        if self._stopped:
            return
        if self._buffer is None:
            return
        buffer = self._buffer
        buffed = buffer.flush()
        for item in buffed:
            self._send_pack(item)
        self._stopped = True

    def buffer(self) -> Buffed:
        return self._decoder.buffed()

    def stopped(self) -> bool:
        return self._stopped
