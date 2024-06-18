from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Union
from ghostiss.context import Context
from ghostiss.core.llms import LlmMsg
from ghostiss.core.messages import Package, Message, Attachment
from ghostiss.core.operators import Operator


class LlmChunkParser(ABC):
    """
    将 LLM Msg Chunk 转化成 Package
    """

    @abstractmethod
    def new(self) -> "LlmChunkParser":
        pass

    @abstractmethod
    def buff(self, chunk: LlmMsg) -> Tuple[List[Package], Optional[Operator]]:
        pass


class MessageBuffer(ABC):
    """
    记录所有输出的 package
    在 messenger 的出口端.
    """

    @abstractmethod
    def buff(self, package: Package) -> None:
        pass

    @abstractmethod
    def buffered(self) -> List[Message]:
        pass


class PackagePipe(ABC):
    """
    包的管道式处理, 每一层都可能会对 package 进行加工.
    加工结果可能是直接发送, 或者拆分 or buff, 或者不发送.
    返回 operator 时会中断.
    """

    @abstractmethod
    def filter(self, package: Package) -> Tuple[List[Package], List[Operator]]:
        pass


class Attention(ABC):
    """
    对 tokens 的流式输出进行理解.
    可以输出额外的数据, 或操作. 输出操作则中断流程.
    通常 attention 会放到一个处理 FunctionalTokens 的 PackagePipe 里.
    这个 pipe 接收流式的输出, 当匹配到 function tokens 时, 会 buffer 后续的 tokens.
    直到 buffer 结束, 就会回调这个 Attention.
    """

    @abstractmethod
    def functional_tokens(self) -> str:
        pass

    @abstractmethod
    def attend(self, tokens: str) -> Tuple[List[Message], Optional[Operator]]:
        pass


class Messenger(ABC):

    @abstractmethod
    def new(self) -> "Messenger":
        """
        清空状态, 生成一个无污染的 messenger 实例.
        """
        pass

    @abstractmethod
    def with_parser(self, parser: LlmChunkParser) -> "Messenger":
        pass

    @abstractmethod
    def with_buffer(self, buffer: MessageBuffer) -> "Messenger":
        pass

    @abstractmethod
    def with_attentions(self, attentions: List[Attention]) -> "Messenger":
        pass

    @abstractmethod
    def with_pipes(self, *pipes: PackagePipe) -> "Messenger":
        pass

    @abstractmethod
    def with_attachments(self, attachments: List[Attachment]) -> "Messenger":
        """
        所有通过它发送的消息都会携带相关的 attachments.
        """
        pass

    @abstractmethod
    def send(self, *messages: Union[Package, Message]) -> None:
        pass

    @abstractmethod
    def receive(self, chunk: LlmMsg) -> None:
        """
        接收到一个 chunk 后, 通过 LlmChunkParser 处理完, 然后调用 send 方法发送.
        """
        pass

    @abstractmethod
    def wait(self, ctx: Context) -> Tuple[List[Message], List[Operator]]:
        """
        同步等待 messenger 结果.
        在 python 没有较好的异步机制.
        :returns
           messages: messenger 运行过程中生产出来的消息, 与端上保持一致.
           operators: 运行过程中产生的各种算子. 会在 kernel 里通过栈运行.
        """
        pass
