import time
from typing import Iterable, Optional, List, Dict, Set

from ghostos.core.messages import Message, FunctionCaller, MessageType, Role, Payload, Buffer, Flushed
from ghostos.core.llms import FunctionalToken
from ghostos.helpers import uuid

__all__ = ['DefaultBuffer']


# deprecated
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
            functional_tokens: Optional[Iterable[FunctionalToken]] = None,
    ):
        self._default_name = name
        """默认的用户名"""
        self._default_role = role
        """默认的角色"""
        self._payloads = list(payloads) if payloads else None
        """默认的 payloads"""

        self._buffering_message: Optional[Message] = None
        """正在 buff 的消息体. """

        self._buffed_messages: List[Message] = []
        """过程中 buff 的 caller. """
        self._origin_functional_tokens = functional_tokens

        self._functional_token_starts: Dict[str, FunctionalToken] = {}
        """加载 functional tokens. 根据特殊的 token, 生成 caller 对象. """

        self._functional_token_ends: Dict[str, FunctionalToken] = {}

        self._functional_token_chars: Dict[int, Set[str]] = {}
        """ functional token 的字符组.. """

        self._destroyed = False

        if functional_tokens:
            for ft in functional_tokens:
                start = ft.token
                if not start:
                    continue
                end = ft.end_token
                self._functional_token_starts[start] = ft
                i = 0
                for c in start:
                    i = self._add_functional_token_char(c, i)
                if not end:
                    continue
                self._functional_token_ends[end] = ft
                i = 0
                for c in end:
                    i = self._add_functional_token_char(c, i)

        self._current_functional_token: str = ""
        """正在运行中的 functional token"""
        self._current_functional_token_content: str = ""
        """正在处理中的 functional token 的内容"""
        self._buffering_message_delivered_content: str = ""
        """消息体所有缓冲的已发送 content 内容. """
        self._buffering_token: str = ""
        """疑似命中了 functional token 而被 buff 的字符串."""

    def _add_functional_token_char(self, c: str, i: int) -> int:
        if i not in self._functional_token_chars:
            self._functional_token_chars[i] = set()
        idx_token_chars = self._functional_token_chars[i]
        idx_token_chars.add(c)
        self._functional_token_chars[i] = idx_token_chars
        i += 1
        return i

    def match(self, message: Message) -> bool:
        # 默认可以匹配任何一种 message 消息体.
        return True

    def add(self, pack: "Message") -> List[Message]:
        # 获取buff 后需要发送的包.
        items = self._buff(pack)
        result = []
        for item in items:
            # 如果是尾包, 对尾包进行必要的处理.
            is_tail = item.is_complete()
            if is_tail:
                self._buff_tail_pack(item)
            result.append(item)
        return result

    def _buff(self, pack: "Message") -> Iterable[Message]:
        if not pack:
            return []
        # 不深拷贝的话, 加工逻辑就会交叉污染?
        # pack = origin.model_copy(deep=True)
        if MessageType.is_protocol_message(pack):
            # final 包不进行 buffer.
            yield pack
            return
        if pack.is_complete():
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
            yield self._parse_content_by_functional_token(pack)
        else:
            # patch 失败, 意味着 pack 来自一条新的消息.
            tail = self._clear_tail_pack()
            if tail is not None:
                yield tail
            # 接受首包.
            yield from self._receive_head_pack(pack)

    def _parse_content_by_functional_token(self, pack: "Message") -> "Message":
        """
        将包的 content 进行过滤. 基本逻辑:
        1. 逐个遍历 content 字符, 一个个检查.
        2. 如果字符可能命中某个 functional_token, 就开始 buff, 先不发送.
        3. buff 后的字符串如果不匹配任何 functional_token, 则一起发送.
        4. buff 后的字符如果完全匹配某个 functional_token, 则后续的字符都认为是这个 functional_token 的后续输出. 除非匹配了新的.
        # todo: this function is too ugly
        """
        if not pack.content or not self._functional_token_starts:
            return pack
        content = pack.content
        # 逐个字符进行遍历.
        deliver_content = ""
        for c in content:
            buffed_idx = len(self._buffering_token) if self._buffering_token else 0
            # 加上当前的字符, 生成的 buffering token.
            buffering_token = self._buffering_token + c
            buffering_token_length = len(buffering_token)
            # 如果 buffering token 比所有的 token 都长了.
            buffing_token_is_larger_than_any_tokens = buffering_token_length > len(self._functional_token_chars)

            # 没有希望匹配到一个 token, 则所有 buffering_token 都要输出.
            is_functional_token_char = c in self._functional_token_chars[buffed_idx]
            if buffing_token_is_larger_than_any_tokens or not is_functional_token_char:
                # 为当前 functional token 准备好的内容要变长.
                self._current_functional_token_content += buffering_token
                functional_token = self._functional_token_starts.get(self._current_functional_token, None)
                if not functional_token or functional_token.visible:
                    # 已经 buffering 的内容都准备输出.
                    # 但如果当前的 functional token 禁止对外输出, 则不会将新内容添加到待输出内容里.
                    deliver_content += buffering_token
                # 清空 buffering content.
                self._buffering_token = ""
            #  完全匹配到了某个 functional token:
            elif buffering_token in self._functional_token_starts:
                ft = self._functional_token_starts[buffering_token]
                # 正在 buffer 某个 functional token 的输出. 就需要生成一次完整的 caller 了.
                if (
                        self._current_functional_token
                        # functional token only has start
                        and self._current_functional_token in self._functional_token_starts
                        and self._current_functional_token not in self._functional_token_ends
                ):
                    caller = self._generate_current_caller()
                    if caller:
                        # 把 caller 添加到当前 pack 里.
                        caller.add(pack)
                        if pack is not self._buffering_message:
                            caller.add(self._buffering_message)
                # 状态归零.
                self._current_functional_token = buffering_token
                self._current_functional_token_content = ""
                # 变换新的 functional token.
                if ft.visible:
                    deliver_content += buffering_token
                # 清空 buffering token 信息.
                self._buffering_token = ""
            # 仍然有希望通过未来的字符匹配到 token.
            elif buffering_token in self._functional_token_ends:
                ft = self._functional_token_ends[buffering_token]
                if (
                        self._current_functional_token
                        # functional token only has start
                        and self._current_functional_token in self._functional_token_starts
                ):
                    caller = self._generate_current_caller()
                    if caller:
                        # 把 caller 添加到当前 pack 里.
                        caller.add(pack)
                        if pack is not self._buffering_message:
                            caller.add(self._buffering_message)
                # reset states
                self._current_functional_token = ""
                self._current_functional_token_content = ""
                # reset current functional token
                self._current_functional_token = ""
                if ft.visible:
                    deliver_content += buffering_token
                self._buffering_token = ""
            else:
                self._buffering_token = buffering_token
        # 输出的消息会缓存到一起.
        self._buffering_message_delivered_content += deliver_content
        # 结算环节, 变更 pack 可以输出的 content.
        if pack.is_complete() and pack.content != self._buffering_message_delivered_content:
            pack.memory = pack.content
        pack.content = deliver_content
        return pack

    def _receive_tail_pack(self, pack: Message) -> Iterable[Message]:
        """
        接收到了一个尾包
        """
        # 当成首包来加工一下.
        pack = self._wrap_first_pack(pack)
        # 清理掉上一条 buffering_message.
        if self._buffering_message:
            # 先判断是不是同一个包.
            patched = self._buffering_message.patch(pack)
            # 尾包属于同一条消息.
            if patched:
                # 不做二次加工.
                self._reset_buffering()
                yield patched
                # return from here
                return
            else:
                # 发送上一条消息的尾包. 只有这个方法会将消息入队.
                last_tail = self._clear_tail_pack()
                if last_tail is not None:
                    yield last_tail
        self._buffering_message = pack
        # 然后发送当前包.
        yield self._parse_content_by_functional_token(pack)
        self._buffering_message = None

    def _buff_tail_pack(self, tail: Message) -> None:
        # 剥离所有的 callers.
        self._buffed_messages.append(tail)

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
                if not payload.payload_exists(pack):
                    payload.set_payload(pack)

        return pack

    def _receive_head_pack(self, pack: "Message") -> Iterable[Message]:
        pack = self._wrap_first_pack(pack)
        # 添加新的缓冲.
        self._buffering_message = pack
        # 发送首包.
        yield self._parse_content_by_functional_token(pack)

    def _clear_tail_pack(self) -> Optional[Message]:
        if self._buffering_message is None:
            self._reset_buffering()
            return None

        buffering = self._buffering_message
        buffering = buffering.as_tail()

        if self._functional_token_starts:
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

    def _generate_current_caller(self) -> Optional[FunctionCaller]:
        if not self._current_functional_token:
            return None
        functional_token = self._functional_token_starts[self._current_functional_token]
        caller = functional_token.new_caller(self._current_functional_token_content)
        self._current_functional_token = ""
        return caller

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

        callers = []
        messages = self._buffed_messages
        for item in messages:
            callers.extend(item.callers)
        flushed = Flushed(
            unsent=deliver,
            messages=messages,
            callers=callers,
        )
        self._reset_buffering()
        self._buffed_messages = []
        return flushed

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        del self._buffering_message
        del self._buffering_message_delivered_content
        del self._buffering_token
        del self._functional_token_starts
        del self._origin_functional_tokens
        del self._functional_token_ends
