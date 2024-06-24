from abc import ABC, abstractmethod
from typing import Iterable, Union, NamedTuple, TypeVar
from ghostiss.entity import EntityMeta
from ghostiss.blueprint.messages.message import Message, Future

# from typing_extensions import Required, Literal
# from enum import Enum
# from ghostiss.blueprint.messages.openai import ChatCompletionMessage

# todo: 全部不要了.

__all__ = [
    # "PackKind", "Pack",
    "Deliver",
    "Stream",
    "Decoded",
]


#
# class Pack(TypedDict, total=False):
#     kind: str
#     """pack kind"""
#
#     payload: dict
#     """pack data"""
#
#
# class PackKind(str, Enum):
#     """
#     默认的包类型.
#     """
#
#     HEADER = "header"
#     """流式输出单个消息的首包, 主要是 message header. 意味着要新创建一个消息体. """
#
#     TAIL = "tail"
#     """流式输出单个消息的尾包, 可以包含任何讯息. 都会覆盖重写原有的数据."""
#
#     FINAL = "final"
#     """流式输出的结束标记. 标记整个流输出已经结束. """
#
#     ERROR = "error"
#     """一个异常的 message"""
#
#     MESSAGE = "message"
#     """一个完整的 message. """
#
#     # --- chunks --- #
#
#     OPENAI_DELTA = "openai_delta"
#
#     TEXT_CHUNK = "text_chunk"
#
#     def new(self, data: Optional[dict] = None) -> "Pack":
#         if data is None:
#             data = {}
#         return Pack(kind=self.value, payload=data)
#
#     def match(self, pack: Pack) -> bool:
#         return self == pack["kind"]
#
#     @classmethod
#     def transport_kinds(cls) -> Set["PackKind"]:
#         """
#         拥有通讯语义的.
#         """
#         return {cls.HEADER, cls.TAIL, cls.FINAL, cls.ERROR, cls.MESSAGE}
#
#     @classmethod
#     def is_new(cls, pack: Pack) -> bool:
#         kind = pack["kind"]
#         return kind == cls.HEADER or kind == cls.MESSAGE
#
#     @classmethod
#     def is_final(cls, pack: Pack) -> bool:
#         kind = pack["kind"]
#         return kind == cls.FINAL or cls.ERROR
#
#     @classmethod
#     def new_message(cls, msg: Message) -> "Pack":
#         return cls.MESSAGE.new(msg.model_dump())
#
#     @classmethod
#     def new_header(cls, header: Header) -> "Pack":
#         return cls.HEADER.new(header.model_dump())
#
#     @classmethod
#     def new_final(cls, data: dict) -> "Pack":
#         return cls.FINAL.new(data)
#
#     @classmethod
#     def new_tail(cls, msg: Message) -> "Pack":
#         return cls.TAIL.new(msg.model_dump())
#
#     @classmethod
#     def is_chunk(cls, kind: str) -> bool:
#         return kind not in cls.transport_kinds()
#
#     @classmethod
#     def new_openai_delta(cls, msg: ChatCompletionMessage) -> "Pack":
#         return cls.OPENAI_DELTA.new(msg.model_dump())
#
#     @classmethod
#     def new_text_chunk(cls, text: str) -> "Pack":
#         data = TextPayload(text=text)
#         return cls.TEXT_CHUNK.new(data)


# ---- pack handlers ---- #

class Decoded(NamedTuple):
    messages: Iterable[Message]
    """已经向上游发送的消息"""

    callers: Iterable[Future]
    """过滤出来的 caller. """




class Stream(ABC):
    """
    向上游发送包. 如果为 false, 则意味着不允许发送.
    """

    @abstractmethod
    def deliver(self, pack: PACK) -> bool:
        pass


class Deliver(Stream, ABC):
    """
    messenger 的原型. Stream 的有状态版本.
    """

    @abstractmethod
    def deliver(self, pack: PACK) -> bool:
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
    def decoded(self) -> Decoded:
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

#
# class BasicDeliver(Deliver):
#     """
#     一个基础的实现.
#     """
#
#     def __init__(
#             self,
#             decoder: Decoder,
#             upstream: Optional[Stream] = None,
#             buffer: Optional[Buffer] = None,
#             parser: Optional[Parser] = None,
#     ):
#         self._stopped = False
#         self._decoder = decoder
#         self._upstream = upstream
#         self._buffer: Optional[Buffer] = buffer
#         self._parser: Optional[Parser] = parser
#
#     def deliver(self, pack: Pack) -> bool:
#         if self._stopped:
#             return False
#         splits = self._split_pack(pack)
#
#         for item in splits:
#             sent = self._buff_pack(item)
#             for sent_pack in sent:
#                 self._send_pack(sent_pack)
#         return not self._stopped
#
#     def _split_pack(self, pack: Pack) -> Iterable[Pack]:
#         parser = self._parser
#         if parser is None:
#             yield pack
#         else:
#             return parser.parse(pack)
#
#     def _buff_pack(self, pack: Pack) -> Iterable[Pack]:
#         buffer = self._buffer
#         if buffer is None:
#             yield pack
#         else:
#             return buffer.buff(pack)
#
#     def _send_pack(self, pack: Pack) -> bool:
#         if self._stopped:
#             return False
#         decoder = self._decoder
#         # 先存储.
#         if decoder is not None:
#             decoder.receive(pack)
#
#         # 如果上游流存在, 就发送.
#         if self._upstream is not None:
#             ok = self._upstream.deliver(pack)
#             if not ok:
#                 self._stopped = True
#                 return False
#
#     def flush(self) -> None:
#         if self._stopped:
#             return
#         if self._buffer is None:
#             return
#         buffer = self._buffer
#         buffed = buffer.flush()
#         for item in buffed:
#             self._send_pack(item)
#         self._stopped = True
#
#     def decoded(self) -> Decoded:
#         return self._decoder.buffed()
#
#     def stopped(self) -> bool:
#         return self._stopped
