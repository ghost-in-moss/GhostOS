import time
from typing import Iterable, Optional, List, NamedTuple, Dict, Set
from abc import ABC, abstractmethod

from ghostiss.core.messages.message import Message, Caller, DefaultTypes, Role, FunctionalToken, Payload, Attachment
from ghostiss.helpers import uuid

__all__ = [
    "Flushed", "Buffer", "DefaultBuffer",  # "GroupBuffers",
]


class Flushed(NamedTuple):
    unsent: Iterable[Message]
    """ buffer 尚未发送, 需要继续发送出去的包"""

    messages: List[Message]
    """经过 buff, 生成的包"""

    callers: Iterable[Caller]
    """消息体产生的回调方法."""


class Buffer(ABC):
    """
    在流式传输中拦截 message 的拦截器. 同时要能完成粘包, 返回粘包后的结果.
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
    def new(self) -> "Buffer":
        pass

    @abstractmethod
    def flush(self) -> Flushed:
        pass


class DefaultBuffer(Buffer):
    """
    基于 Message 标准协议的默认 buffer.
    """

    def __init__(
            self,
            *,
            name: Optional[str] = None,
            role: str = Role.ASSISTANT.value,
            payloads: Optional[Iterable[Payload]] = None,
            attachments: Optional[Iterable[Attachment]] = None,
            functional_tokens: Optional[Iterable[FunctionalToken]] = None,
    ):
        self._default_name = name
        """默认的用户名"""
        self._default_role = role
        """默认的角色"""
        self._payloads = list(payloads) if payloads else None
        """默认的 payloads"""
        self._attachments = list(attachments) if attachments else None
        """默认的 attachments"""

        self._buffering_message: Optional[Message] = None
        """正在 buff 的消息体. """

        self._buffed_messages: List[Message] = []
        """发送出去的完整消息体. """
        self._buffed_callers: List[Caller] = []
        """过程中 buff 的 caller. """
        self._origin_functional_tokens = functional_tokens

        self._functional_tokens = {}
        """加载 functional tokens. 根据特殊的 token, 生成 caller 对象. """

        self._functional_token_chars: Dict[int, Set[str]] = {}
        """ functional token 的字符组.. """

        if functional_tokens:
            for ft in functional_tokens:
                self._functional_tokens[ft.token] = ft
                i = 0
                for c in ft.token:
                    if i not in self._functional_token_chars:
                        self._functional_token_chars[i] = set()
                    idx_token_chars = self._functional_token_chars[i]
                    idx_token_chars.add(c)
                    self._functional_token_chars[i] = idx_token_chars
                    i += 1

        self._current_functional_token: str = ""
        """正在运行中的 functional token"""
        self._current_functional_token_content: str = ""
        """正在处理中的 functional token 的内容"""
        self._buffering_message_delivered_content: str = ""
        """消息体所有缓冲的 content 内容. """
        self._buffering_token: str = ""
        """疑似命中了 functional token 而被 buff 的字符串."""

    def match(self, message: Message) -> bool:
        # 默认可以匹配任何一种 message 消息体.
        return True

    def buff(self, pack: "Message") -> Iterable[Message]:
        # 获取buff 后需要发送的包.
        items = self._buff(pack)
        result = []
        for item in items:
            # 如果是尾包, 对尾包进行必要的处理.
            if not item.pack:
                result.append(self._parse_tail_pack(item))
            elif not item.is_empty():
                # 消息不为空才发送.
                result.append(item)
        return result

    def _buff(self, pack: "Message") -> Iterable[Message]:
        if not pack:
            yield from []
        if DefaultTypes.is_final(pack):
            # final 包不进行 buffer.
            yield from [pack]
        if not pack.pack:
            # 如果收到了一个尾包, 则走尾包逻辑.
            yield from self._receive_tail_pack(pack)
        if self._buffering_message is None:
            # 如果 buffering_message 为空, 则走首包逻辑.
            yield from self._receive_head_pack(pack)

        patched = self._buffering_message.patch(pack)
        # 判断新来的包能否 patch 到已经存在的包上.
        if patched:
            # patch 成功了,
            self._buffering_message = patched
            # 发送包之前, 对包的 content 进行加工.
            yield from self._parse_content_by_functional_token(pack)
        else:
            # patch 失败, 意味着 pack 来自一条新的消息.
            tail = self._clear_tail_pack()
            if tail is not None:
                yield tail
            # 接受首包.
            yield from self._receive_head_pack(pack)

    def _parse_content_by_functional_token(self, pack: "Message") -> Iterable["Message"]:
        """
        将包的 content 进行过滤. 基本逻辑:
        1. 逐个遍历 content 字符, 一个个检查.
        2. 如果字符可能命中某个 functional_token, 就开始 buff, 先不发送.
        3. buff 后的字符串如果不匹配任何 functional_token, 则一起发送.
        4. buff 后的字符如果完全匹配某个 functional_token, 则后续的字符都认为是这个 functional_token 的后续输出. 除非匹配了新的.
        """
        if not pack.content:
            yield pack
            return
        content = pack.content
        pack.content = None
        # 逐个字符进行遍历.
        buffed_idx = len(self._buffering_token) if self._buffering_message else 0
        deliver_content = ""
        for c in content:
            # 加上当前的字符, 生成的 buffering token.
            buffering_token = self._buffering_token + c
            buffering_token_length = len(buffering_token)
            # 如果 buffering token 比所有的 token 都长了.
            buffing_token_is_larger_than_any_tokens = buffering_token_length > len(self._functional_token_chars)

            # 没有希望匹配到一个 token, 则所有 buffering_token 都要输出.
            if buffing_token_is_larger_than_any_tokens or c not in self._functional_token_chars[buffed_idx]:
                # 为当前 functional token 准备好的内容要变长.
                self._current_functional_token_content += buffering_token
                functional_token = self._functional_tokens.get(self._current_functional_token, None)
                if not functional_token or functional_token.deliver:
                    # 已经 buffering 的内容都准备输出.
                    # 但如果当前的 functional token 禁止对外输出, 则不会将新内容添加到待输出内容里.
                    deliver_content += buffering_token
                # 清空 buffering content.
                self._buffering_token = ""
            #  完全匹配到了某个 functional token:
            elif buffering_token in self._functional_tokens:
                # 正在 buffer 某个 functional token 的输出. 就需要生成一次完整的 caller 了.
                if self._current_functional_token and self._current_functional_token in self._functional_tokens:
                    functional_token = self._functional_tokens[self._current_functional_token]
                    caller = Caller(
                        name=functional_token.name,
                        arguments=self._current_functional_token_content,
                        protocol=False,
                    )
                    # 把 caller 添加到当前 pack 里.
                    caller.add(pack)
                # 状态归零.
                self._current_functional_token = ""
                self._current_functional_token_content = ""
                # 变换新的 functional token.
                self._current_functional_token = buffering_token
                # 清空 buffering token 信息.
                # 并不添加 deliver content, 因为 functional token 默认不对外输出.
                self._buffering_token = ""
            # 仍然有希望通过未来的字符匹配到 token.
            else:
                self._buffering_token = buffering_token
        # 输出的消息会缓存到一起.
        self._buffering_message_delivered_content += deliver_content
        # 结算环节, 变更 pack 可以输出的 content.
        pack.content = deliver_content
        yield pack

    def _receive_tail_pack(self, pack: Message) -> Iterable[Message]:
        """
        接收到了一个尾包
        """
        if self._buffering_message:
            patched = self._buffering_message.patch(pack)
            # 尾包不属于同一条消息.
            if not patched:
                # 发送上一条消息的尾包. 只有这个方法会将消息入队.
                tail = self._clear_tail_pack()
                if tail is not None:
                    yield tail
            else:
                # 包装好首包的讯息.
                pack = self._wrap_first_pack(pack)

        _ = self._clear_tail_pack()
        # 变更 buffering_message.
        self._buffering_message = pack
        # 对尾包进行额外的处理, 并且发送.
        # 预期尾包不会发送超过一次.
        yield from self._parse_content_by_functional_token(pack)

    def _parse_tail_pack(self, tail: Message) -> Message:
        # 剥离所有的 callers.
        callers = []
        self._buffed_messages.append(tail)

        # 从标准的 payload 和 attachments 里读取 caller.
        callers.extend(tail.callers)
        if callers:
            self._buffed_callers.append(*callers)
        return tail

    def _wrap_first_pack(self, pack: Message) -> Message:
        # 补齐首包的讯息
        if not pack.msg_id:
            # 补齐首包的 uuid.
            pack.msg_id = uuid()
        if not pack.created:
            # 补齐首包的创建时间.
            pack.created = int(time.time())
        if not pack.role:
            # 使用默认的 role
            pack.role = self._default_role
        if not pack.name:
            # 使用默认的名字.
            pack.name = self._default_name

        # 添加默认的 payloads.
        if self._payloads:
            for payload in self._payloads:
                if not payload.exists(pack):
                    payload.set(pack)

        # 添加默认的 attachments.
        if self._attachments:
            for attachment in self._attachments:
                attachment.add(pack)
        return pack

    def _receive_head_pack(self, pack: "Message") -> Iterable[Message]:
        pack = self._wrap_first_pack(pack)
        # 添加新的缓冲.
        self._buffering_message = pack
        # 发送首包.
        yield from self._parse_content_by_functional_token(pack)

    def _clear_tail_pack(self) -> Optional[Message]:
        if self._buffering_message is None:
            return None

        buffering = self._buffering_message
        buffering.pack = False

        if self._buffering_token:
            self._buffering_message_delivered_content += self._buffering_token
            self._buffering_token = ""

        # 如果发送的消息和 buff 的消息不一样, 则意味着...
        if self._buffering_message_delivered_content != buffering.content:
            buffering.memory = buffering.content
            buffering.content = self._buffering_message_delivered_content

        # 状态归零.
        self._buffering_message = None
        self._buffering_message_delivered_content = ""
        self._buffering_token = ""
        self._current_functional_token = ""
        self._current_functional_token_content = ""
        return buffering

    def new(self) -> "DefaultBuffer":
        return DefaultBuffer(
            name=self._default_name,
            role=self._default_role,
            payloads=self._payloads,
            attachments=self._attachments,
            functional_tokens=self._origin_functional_tokens,
        )

    def flush(self) -> Flushed:
        unsent = self._clear_tail_pack()
        deliver: List[Message] = []
        if unsent is not None:
            unsent = self._parse_tail_pack(unsent)
            deliver.append(unsent)

        flushed = Flushed(unsent=deliver, messages=self._buffed_messages, callers=self._buffed_callers)
        self._buffering_message = None
        self._buffed_messages = []
        self._buffed_callers = []
        return flushed

# class GroupBuffers(Buffer):
#     """
#     可以根据消息类型分组的 buffers.
#     """
#
#     def __init__(
#             self,
#             buffers: Iterable[Buffer],
#             default_: Optional[Buffer] = None,
#     ):
#         self._buffers = buffers
#         self._buffering: Optional[Buffer] = None
#         if default_ is None:
#             default_ = DefaultBuffer()
#         self._default_buffer: Buffer = default_
#         self._buffed: List[Message] = []
#         self._callers: List[Caller] = []
#
#     def match(self, message: Message) -> bool:
#         return True
#
#     def _match_buffer(self, message: Message) -> Buffer:
#         for buffer in self._buffers:
#             if buffer.match(message):
#                 return buffer.new()
#         return self._default_buffer.new()
#
#     def buff(self, pack: "Message") -> Iterable[Message]:
#         if self._buffering is None:
#             return self._on_first_pack(pack)
#
#         if self._buffering.match(pack):
#             return self._buffering.buff(pack)
#
#         buffed = self._flush()
#         for item in buffed:
#             yield item
#
#         output = self._on_first_pack(pack)
#         for item in output:
#             yield item
#
#     def _flush(self) -> Iterable[Message]:
#         if self._buffering is None:
#             return []
#         flushed = self._buffering.flush()
#         self._buffering = None
#         self._buffed.append(*flushed.messages)
#         self._callers.append(*flushed.callers)
#         return flushed.unsent
#
#     def _on_first_pack(self, pack: "Message") -> Iterable[Message]:
#         buffer = self._match_buffer(pack)
#         self._buffering = buffer
#         sent = buffer.buff(pack)
#         return sent
#
#     def new(self) -> "Buffer":
#         return GroupBuffers(self._buffers)
#
#     def flush(self) -> Flushed:
#         sent = []
#         if self._buffering:
#             sent = self._flush()
#
#         return Flushed(
#             unsent=sent,
#             messages=self._buffed,
#             callers=self._callers,
#         )
