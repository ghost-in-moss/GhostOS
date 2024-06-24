from typing import List, Iterable, Optional, Set

from ghostiss.blueprint.messages.deliver import Buffer, Pack, PackKind, TextPayload

__all__ = [
    "PipelineBuffer",
    "FunctionalTokenBuffer",
]


class PipelineBuffer(Buffer):
    """
    管道式的 buffer.
    """

    def __init__(self, buffers: List[Buffer]):
        # 按顺序从前向后发送.
        self._buffers = buffers
        self._buffering = []
        for buffer in self._buffers:
            self._buffering.append(buffer)
        self._sent: List[Pack] = []
        self._flushed: bool = False

    def new(self) -> Buffer:
        buffers = []
        for buffer in self._buffers:
            buffers.append(buffer.new())
        return PipelineBuffer(buffers)

    def append(self, buffer: Buffer) -> "PipelineBuffer":
        buffers = self._buffers.copy()
        buffers.append(buffer)
        return PipelineBuffer(buffers)

    def buff(self, pack: Pack) -> Iterable[Pack]:
        # todo: 先不写递归.
        if self._flushed:
            return []
        _sent: List[Pack] = [pack]
        for buffer in self._buffering:
            new_sent = []
            for item in _sent:
                result = buffer.buff(item)
                for s in result:
                    new_sent.append(s)
            _sent = new_sent
        for item in _sent:
            yield item

    def _buff(self, pack: Pack, buffer: Buffer, forwards: List[Buffer]) -> Iterable[Pack]:
        next_buffer = forwards.pop(0)
        iterable = buffer.buff(pack)
        for item in iterable:
            if next_buffer is not None:
                futures = self._buff(item, next_buffer, forwards)
                for f in futures:
                    yield f
            else:
                yield item

    def flush(self) -> Iterable[Pack]:
        buffer = self._reduce()
        while buffer is not None:
            sent = buffer.flush()
            for item in sent:
                yield item
            buffer = self._reduce()

    def _reduce(self) -> Optional[Buffer]:
        if len(self._buffering) == 0:
            return None
        buffer = self._buffering.pop(0)
        return buffer


class FunctionalTokenBuffer(Buffer):

    def __init__(self, tokens: List[str], prefix: str = "\n"):
        self._tokens = tokens
        # 假设已经存在.
        self._buffering: str = prefix
        self._tokens_trie: List[Set[str]] = []
        for token in tokens:
            self._add_token(prefix + token)

    def _add_token(self, token: str):
        for idx, char in enumerate(token):
            # 从来不加入到 0.
            if idx >= len(self._tokens_trie):
                self._tokens_trie.append(set())
            s = self._tokens_trie[idx]
            s.add(char)

    def new(self) -> "Buffer":
        return FunctionalTokenBuffer(self._tokens)

    def buff(self, pack: Pack) -> Iterable[Pack]:
        if not PackKind.TEXT_CHUNK.match(pack):
            flush = self.flush()
            for item in flush:
                yield item
            yield pack
        else:
            payload = TextPayload(**pack["payload"])
            return self._buff(payload["text"])

    def _buff(self, text: str) -> Iterable[Pack]:
        idx = len(self._buffering)
        # todo
        pass

    def flush(self) -> Iterable[Pack]:
        if self._buffering:
            sent = PackKind.new_text_chunk(self._buffering)
            self._buffering = ""
            yield sent
