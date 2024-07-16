import time
from typing import Iterable, Optional, List, NamedTuple, Type
from abc import ABC, abstractmethod

from ghostiss.core.messages.message import Message, Caller, DefaultTypes
from ghostiss.core.messages.payloads import Payload, CallerPayload, FunctionCall
from ghostiss.core.messages.payloads import read_payload_callers, add_payload
from ghostiss.core.messages.attachments import Attachment, CallerAttachment, ToolCall
from ghostiss.core.messages.attachments import read_attachment_callers, add_attachment
from ghostiss.core.messages.message import FunctionalToken, FunctionCall
from ghostiss.helpers import uuid

__all__ = [
    "Flushed", "MessageBuffer", "DefaultMessageBuffer", "GroupMessageBuffers",
]


class Flushed(NamedTuple):
    sent: Iterable[Message]
    """发送出去的包"""

    buffed: Iterable[Message]
    """经过 buff, 生成的包"""

    callers: Iterable[Caller]
    """消息体产生的回调方法."""


class MessageBuffer(ABC):
    """
    在流式传输中拦截 message 的拦截器.
    """

    @abstractmethod
    def match(self, message: Message) -> bool:
        """
        匹配一个消息体.
        """
        pass

    @abstractmethod
    def buff(self, pack: "Message") -> Iterable[Message]:
        """
        buff 一个消息体, 然后决定是否对外发送.
        """
        pass

    @abstractmethod
    def new(self) -> "MessageBuffer":
        pass

    @abstractmethod
    def flush(self) -> Flushed:
        pass


class DefaultMessageBuffer(MessageBuffer):
    """
    基于 Message 标准协议的 buffer.
    """

    def __init__(
            self,
            *,
            attachments: Optional[List[Attachment]] = None,
            payloads: Optional[List[Payload]] = None,
            caller_attachments: Optional[List[Type[CallerAttachment]]] = None,
            caller_payloads: Optional[List[CallerPayload]] = None,
            functional_tokens: Optional[List[FunctionalToken]] = None,
    ):
        self._buffering: Optional[Message] = None
        """正在 buff 的消息体. """

        self._buffed: List[Message] = []
        """发送出去的完整消息体. """
        self._buffed_callers: List[Caller] = []
        """过程中 buff 的 caller. """

        self._attachments: Optional[List[Attachment]] = attachments
        """追加在每条消息后的 attachment"""

        self._payloads: Optional[List[Payload]] = payloads
        """追加在每条消息上的 payload"""

        if caller_attachments is not None:
            caller_attachments = [ToolCall]
        self._caller_attachments = caller_attachments
        """用来判断的 caller attachment"""

        if caller_payloads is not None:
            caller_payloads = [FunctionCall]
        self._caller_payloads = caller_payloads
        """用来判断的 caller payloads"""

        self._functional_tokens = {}
        """加载 functional tokens """

        for ft in functional_tokens:
            self._functional_tokens[ft.token] = ft

    def match(self, message: Message) -> bool:
        return True

    def buff(self, pack: "Message") -> Iterable[Message]:
        if self._buffering is None:
            self._buffering = pack
            sent = self._receive_first(pack)
            return sent

        ok = self._buffering.buff(pack)
        if ok:
            return [pack]
        else:
            # 发送尾包.
            tail = self._clear_tail()
            if tail is not None:
                yield tail
            # 接受首包.
            sent = self._receive_first(pack)
            for item in sent:
                yield item

    def _receive_first(self, pack: "Message") -> Iterable[Message]:
        if not pack.msg_id:
            pack.msg_id = uuid()
        if not pack.created:
            pack.created = int(time.time())

        if pack.pack:
            self._buffering = pack
        else:
            # 如果不是 pack 类型的包, 则直接发送. 同时添加 buffed.
            self._buffed.append(pack)
        yield pack

    def _clear_tail(self) -> Optional[Message]:
        if self._buffering is None:
            return None

        buffering = self._buffering
        self._buffering = None
        buffering.pack = False

        buffed = buffering.get_copy()
        buffed = self._wrap_message(buffed)

        # 剥离所有的 callers.
        callers = []
        # 通过 functional tokens 来获取 caller
        read = self._read_functional_tokens(buffed)
        for item in read:
            callers.append(item)

        # 从标准的 payload 和 attachments 里读取 caller.
        read = self._read_callers(buffed)
        for item in read:
            callers.append(item)

        self._buffed.append(buffed)
        if callers:
            self._buffed_callers.append(*callers)
        return buffed

    def _wrap_message(self, message: Message) -> Message:
        message = message.get_copy()
        # 添加 payloads
        if self._payloads:
            for payload in self._payloads:
                add_payload(payload, message)
        #  添加 attachments.
        if self._attachments:
            for attachment in self._attachments:
                add_attachment(attachment, message)
        return message

    def new(self) -> "DefaultMessageBuffer":
        return DefaultMessageBuffer()

    def _read_callers(self, message: Message) -> Iterable[Caller]:
        iterator = read_attachment_callers(self._caller_attachments, message)
        for item in iterator:
            yield item
        iterator = read_payload_callers(self._caller_payloads, message)
        for item in iterator:
            yield item

    def _read_functional_tokens(self, tail: Message) -> Iterable[Caller]:
        if tail.content is None or tail.pack:
            # 只有尾包才要处理.
            return []

        if tail.get_type() != DefaultTypes.CHAT_COMPLETION:
            # 当前只支持 chat completion 使用 functional tokens.
            return []

        # todo: 偷懒, 先用尾包, 未来再改流式.
        memory = tail.content
        callers = []
        ft: Optional[FunctionalToken] = None
        content_lines = []
        arguments_lines: List[str] = []
        lines = tail.content.splitlines()

        for line in lines:
            if line in self._functional_tokens:
                if ft is not None:
                    # 添加到输出.
                    if ft.deliver:
                        content_lines.append(*arguments_lines)
                    # 生成 arguments 字符串.
                    arguments = "\n".join(arguments_lines)
                    # 添加 caller.
                    callers.append(Caller(name=ft.function.name, arguments=arguments))
                    # 清空状态.
                    arguments_lines = []
                # 重置状态.
                ft = self._functional_tokens[line]
            elif ft is None:
                content_lines.append(line)
            elif ft.function:
                arguments_lines.append(line)

        if ft is not None:
            if ft.deliver:
                content_lines.append(*arguments_lines)
            # 生成 arguments 字符串.
            arguments = "\n".join(arguments_lines)
            # 添加 caller.
            callers.append(Caller(name=ft.function.name, arguments=arguments))

        if not callers:
            return []

        tail.content = "\n".join(content_lines)
        tail.memory = memory
        return callers

    def flush(self) -> Flushed:
        sent = self._clear_tail()
        deliver: List[Message] = []
        if sent is not None:
            deliver.append(sent)

        return Flushed(sent=deliver, buffed=self._buffed, callers=self._buffed_callers)


class GroupMessageBuffers(MessageBuffer):
    """
    可以根据消息类型分组的 buffers.
    """

    def __init__(
            self,
            buffers: Iterable[MessageBuffer],
            default_: Optional[MessageBuffer] = None,
    ):
        self._buffers = buffers
        self._buffering: Optional[MessageBuffer] = None
        if default_ is None:
            default_ = DefaultMessageBuffer()
        self._default_buffer: MessageBuffer = default_
        self._buffed: List[Message] = []
        self._callers: List[Caller] = []

    def match(self, message: Message) -> bool:
        return True

    def _match_buffer(self, message: Message) -> MessageBuffer:
        for buffer in self._buffers:
            if buffer.match(message):
                return buffer.new()
        return self._default_buffer.new()

    def buff(self, pack: "Message") -> Iterable[Message]:
        if self._buffering is None:
            return self._on_first_pack(pack)

        if self._buffering.match(pack):
            return self._buffering.buff(pack)

        buffed = self._flush()
        for item in buffed:
            yield item

        output = self._on_first_pack(pack)
        for item in output:
            yield item

    def _flush(self) -> Iterable[Message]:
        if self._buffering is None:
            return []
        flushed = self._buffering.flush()
        self._buffering = None
        self._buffed.append(*flushed.buffed)
        self._callers.append(*flushed.callers)
        return flushed.sent

    def _on_first_pack(self, pack: "Message") -> Iterable[Message]:
        buffer = self._match_buffer(pack)
        self._buffering = buffer
        sent = buffer.buff(pack)
        return sent

    def new(self) -> "MessageBuffer":
        return GroupMessageBuffers(self._buffers)

    def flush(self) -> Flushed:
        sent = []
        if self._buffering:
            sent = self._flush()

        return Flushed(
            sent=sent,
            buffed=self._buffed,
            callers=self._callers,
        )
