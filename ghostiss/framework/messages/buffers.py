import time
from typing import Iterable, Optional, List, Dict, Set

from ghostiss.core.messages import Message, Caller, DefaultTypes, Role, Payload, Attachment, Buffer, Flushed
from ghostiss.core.llms import FunctionalToken
from ghostiss.helpers import uuid

__all__ = ['DefaultBuffer']


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

        self._functional_tokens: Dict[str, FunctionalToken] = {}
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

    def buff(self, pack: "Message") -> List[Message]:
        # 获取buff 后需要发送的包.
        items = self._buff(pack)
        result = []
        for item in items:
            # 如果是尾包, 对尾包进行必要的处理.
            is_tail = item.is_tail()
            if is_tail:
                self._buff_tail_pack(item)
            result.append(item)
        return result

    def _buff(self, pack: "Message") -> Iterable[Message]:
        if not pack:
            return []
        # 不深拷贝的话, 加工逻辑就会交叉污染?
        # pack = origin.model_copy(deep=True)
        if DefaultTypes.is_protocol_type(pack):
            # final 包不进行 buffer.
            yield pack
            return
        if pack.is_tail():
            # 如果收到了一个尾包, 则走尾包逻辑.
            yield from self._receive_tail_pack(pack)
            return
        if self._buffering_message is None:
            # 如果 buffering_message 为空, 则走首包逻辑.
            yield from self._receive_head_pack(pack)
            return

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
        deliver_content = ""
        for c in content:
            buffed_idx = len(self._buffering_token) if self._buffering_message else 0
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
                    caller = self._generate_current_caller()
                    if caller:
                        # 把 caller 添加到当前 pack 里.
                        caller.add(pack)
                        caller.add(self._buffering_message)
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
        # 当成首包来加工一下.
        pack = self._wrap_first_pack(pack)
        if self._buffering_message:
            # 先判断是不是同一个包.
            patched = self._buffering_message.patch(pack)
            # 尾包不属于同一条消息.
            if patched:
                # 不做二次加工.
                self._reset_buffering()
                yield patched
                return
            else:
                # 发送上一条消息的尾包. 只有这个方法会将消息入队.
                last_tail = self._clear_tail_pack()
                if last_tail is not None:
                    yield last_tail
        # 然后发送当前包.
        yield pack

    def _buff_tail_pack(self, tail: Message) -> None:
        # 剥离所有的 callers.
        self._buffed_messages.append(tail)

        # 从标准的 payload 和 attachments 里读取 caller.
        if tail.callers:
            for caller in tail.callers:
                self._buffed_callers.append(caller)

    def _wrap_first_pack(self, pack: Message) -> Message:
        # 首包强拷贝, 用来做一个 buffer.
        pack = pack.model_copy(deep=True)
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
            self._reset_buffering()
            return None

        buffering = self._buffering_message
        buffering.pack = False

        if self._buffering_token:
            self._buffering_message_delivered_content += self._buffering_token
            self._current_functional_token_content += self._buffering_token
            self._buffering_token = ""

        # 添加未发送的 caller.
        if self._current_functional_token:
            caller = self._generate_current_caller()
            if caller:
                caller.add(self._buffering_message)

        # 如果发送的消息和 buff 的消息不一样, 则意味着...
        if self._buffering_message_delivered_content != buffering.content:
            buffering.memory = buffering.content
            buffering.content = self._buffering_message_delivered_content

        self._reset_buffering()
        return buffering

    def _reset_buffering(self) -> None:
        # 状态归零.
        self._buffering_message = None
        self._buffering_message_delivered_content = ""
        self._buffering_token = ""
        self._current_functional_token = ""
        self._current_functional_token_content = ""

    def _generate_current_caller(self) -> Optional[Caller]:
        if not self._current_functional_token:
            return None
        functional_token = self._functional_tokens[self._current_functional_token]
        return functional_token.new_caller(self._current_functional_token_content)

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
            self._buff_tail_pack(unsent)
            deliver.append(unsent)

        flushed = Flushed(unsent=deliver, messages=self._buffed_messages, callers=self._buffed_callers)
        self._buffering_message = None
        self._buffed_messages = []
        self._buffed_callers = []
        return flushed
