from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Tuple, Optional, List, Dict, Set, Iterator
from ghostiss.core.messages import Messenger, Message
from ghostiss.core.operators import Operator


class Attention(ABC):

    @abstractmethod
    def func_tokens(self) -> str:
        pass

    @abstractmethod
    def new(self) -> PackageBuffer:
        pass


class PackageBuffer(ABC):

    @abstractmethod
    def buff(self, tokens: str, messenger: Messenger) -> Tuple[bool, Optional[Operator]]:
        pass

    @abstractmethod
    def buffed(self) -> List[Message]:
        pass


class AttentionsBuffer(PackageBuffer):

    def __init__(self, attentions: List[Attention]):
        self.functional_tokens: Dict[int, Set] = {}
        self.attentions: Dict[str, Attention] = {}
        self.buffered = ""
        self.max_functional_token_length = 0
        self.selected_buffer: Optional[PackageBuffer] = None
        self.messages = []
        self.op: Optional[Operator] = None
        for attention in attentions:
            self.add_attention(attention)

    def add_attention(self, attention: Attention) -> None:
        self.attentions[attention.func_tokens()] = attention
        functional_tokens = attention.func_tokens()
        self._add_functional_tokens(functional_tokens)

    def _add_functional_tokens(self, tokens: str) -> None:
        length = len(tokens)
        if length == 0:
            return
        if length > self.max_functional_token_length:
            self.max_functional_token_length = length

        i = 0
        for char in tokens:
            chars = self.functional_tokens.get(i, set())
            chars.add(char)
            self.functional_tokens[i] = chars
            i += 1

    def buff(self, tokens: str, messenger: Messenger) -> Tuple[bool, Optional[Operator]]:
        for char in self._iterate_tokens(tokens):
            char = self._pre_buff(char)
            # 被自己偷吃了.
            if char is None:
                continue
            self._buff(char, messenger)

    def _buff(self, char: str, messenger: Messenger) -> Tuple[bool, Optional[Operator]]:
        if self.selected_buffer is None:
            continue

        ok, op = self.selected_buffer.buff(char, messenger)
        if op is not None:
            messages = self.selected_buffer.buffed()
            self._append(messages)
            return True, op
        if not ok:
            messages = self.selected_buffer.buffed()
            self._append(messages)
            self.selected_buffer = None
            self._buffer()

    @staticmethod
    def _iterate_tokens(tokens: str) -> Iterator[str]:
        for char in tokens:
            yield char

    def _pre_buff(self, char: str) -> Optional[str]:
        idx = len(self.buffered)
        available = self.functional_tokens.get(idx, None)
        if available is None:
            return char

        if char not in available:
            return char

        buffer = self.buffered + char
        if buffer in self.attentions:
            self._switch_attention(self.attentions[buffer])
            self.buffered = ""
            return None

        if len(buffer) >= self.max_functional_token_length:
            self.buffered = ""
            return buffer

        self.buffered = buffer
        return None

    def _append(self, messages: List[Message]) -> None:
        self.messages.append(*messages)

    def _switch_attention(self, attention: Attention):
        pass
